"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface StrixStatus {
  installed: boolean;
  path: string | null;
}

/**
 * StrixControlCard
 *
 * Sleek widget for the dashboard overview that wires the autonomous Strix
 * pentest engine into the local scan session.
 *
 *  State A (Strix installed): a 🚀 Run button that streams live agent progress.
 *  State B (Strix not installed): an install notice + 📦 Install & Enable button.
 */
export function StrixControlCard() {
  const [status, setStatus] = useState<StrixStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [target, setTarget] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/strix/status", { cache: "no-store" });
      if (res.ok) setStatus((await res.json()) as StrixStatus);
    } catch {
      setStatus({ installed: false, path: null });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const streamRun = useCallback(
    async (install: boolean) => {
      setBusy(true);
      setLog([]);
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const res = await fetch("/api/strix/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ target: target || undefined, install }),
          cache: "no-store",
          signal: ctrl.signal,
        });
        if (!res.body) throw new Error("no response stream");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() || "";
          for (const frame of frames) {
            const line = frame.replace(/^data:\s?/, "").trim();
            if (!line) continue;
            if (line === "__DONE__") {
              setLog((l) => [...l, "✅ Stream complete."]);
              continue;
            }
            setLog((l) => [...l, line]);
          }
        }
      } catch (e) {
        setLog((l) => [...l, "❌ " + (e as Error).message]);
      } finally {
        setBusy(false);
        if (install) refreshStatus();
      }
    },
    [target, refreshStatus]
  );

  const card: React.CSSProperties = {
    marginTop: 28,
    background: "linear-gradient(135deg, #0f1620 0%, #131c2b 100%)",
    border: "1px solid #1f2933",
    borderRadius: 16,
    padding: "20px 24px",
  };

  return (
    <section style={card}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 18 }}>
            🤖 Autonomous AI Pentest{" "}
            <span style={{ color: "#58a6ff" }}>Strix</span>
          </h2>
          <div style={{ fontSize: 13, color: "#8b98a5", marginTop: 4 }}>
            {loading
              ? "Checking Strix engine availability…"
              : status?.installed
                ? `Engine ready · ${status.path}`
                : "Strix AI engine not detected on this host."}
          </div>
        </div>

        {status?.installed ? (
          <button
            onClick={() => streamRun(false)}
            disabled={busy}
            style={{
              background: "linear-gradient(135deg,#1f6feb,#3b82f6)",
              color: "white",
              border: "none",
              borderRadius: 8,
              padding: "10px 16px",
              fontWeight: 700,
              cursor: busy ? "wait" : "pointer",
            }}
          >
            {busy ? "Running…" : "🚀 Run Autonomous AI Pentest (Strix)"}
          </button>
        ) : (
          !loading && (
            <button
              onClick={() => streamRun(true)}
              disabled={busy}
              style={{
                background: "#238636",
                color: "white",
                border: "none",
                borderRadius: 8,
                padding: "10px 16px",
                fontWeight: 700,
                cursor: busy ? "wait" : "pointer",
              }}
            >
              {busy ? "Installing…" : "📦 Install & Enable Strix AI Engine"}
            </button>
          )
        )}
      </div>

      {status?.installed && (
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 12, color: "#8b98a5" }}>
            Target (defaults to current scan target)
          </label>
          <input
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="repo path or URL"
            style={{
              width: "100%",
              marginTop: 4,
              background: "#0b0f14",
              border: "1px solid #1f2933",
              borderRadius: 8,
              color: "#e6edf3",
              padding: "8px 10px",
              fontSize: 13,
            }}
          />
        </div>
      )}

      {log.length > 0 && (
        <pre
          style={{
            marginTop: 14,
            background: "#0b0f14",
            border: "1px solid #1f2933",
            borderRadius: 10,
            padding: "12px 14px",
            maxHeight: 240,
            overflowY: "auto",
            fontSize: 12,
            lineHeight: 1.5,
            color: "#aeb9c4",
            whiteSpace: "pre-wrap",
          }}
        >
          {log.join("\n")}
        </pre>
      )}
    </section>
  );
}
