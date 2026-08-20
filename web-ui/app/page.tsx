"use client";

import { useCallback, useEffect, useState } from "react";
import type { ScanReport } from "@/lib/types";
import { GradeBadge } from "@/components/GradeBadge";
import { StatCard } from "@/components/StatCard";
import { RemediationCard } from "@/components/RemediationCard";
import { StrixControlCard } from "@/components/StrixControlCard";

export default function Dashboard() {
  const [report, setReport] = useState<ScanReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastScan, setLastScan] = useState<string>("");

  const runScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/report", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = (await res.json()) as ScanReport;
      setReport(data);
      setLastScan(new Date().toLocaleTimeString());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    runScan();
  }, [runScan]);

  const counts = report?.counts ?? {};
  const critical = counts.Critical ?? 0;
  const high = counts.High ?? 0;
  const medium = counts.Medium ?? 0;
  const findings = report?.findings ?? [];

  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "32px 20px 64px" }}>
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, letterSpacing: -0.3 }}>
            DM <span style={{ color: "#58a6ff" }}>SecureGate</span>
          </h1>
          <div style={{ color: "#8b98a5", fontSize: 13, marginTop: 4 }}>
            Static security baseline scanner — CWE-798 · CWE-306 · CWE-942
          </div>
        </div>
        <button
          onClick={runScan}
          disabled={loading}
          style={{
            background: "#1f6feb",
            color: "white",
            border: "none",
            borderRadius: 8,
            padding: "10px 18px",
            fontWeight: 700,
            cursor: loading ? "wait" : "pointer",
          }}
        >
          {loading ? "Scanning…" : "Re-run scan"}
        </button>
      </header>

      {error && (
        <div style={{ color: "#f85149", marginTop: 16 }}>Error: {error}</div>
      )}

      <StrixControlCard />

      {report && (
        <>
          <section
            style={{
              display: "flex",
              gap: 28,
              alignItems: "center",
              marginTop: 28,
              background: "#10151c",
              border: "1px solid #1f2933",
              borderRadius: 16,
              padding: "24px 28px",
              flexWrap: "wrap",
            }}
          >
            <GradeBadge grade={report.grade} />
            <div style={{ flex: 1, minWidth: 240 }}>
              <div style={{ fontSize: 13, color: "#8b98a5" }}>Security Grade</div>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>
                {report.target}
              </div>
              <div style={{ fontSize: 13, color: "#aeb9c4", marginBottom: 14 }}>
                {report.summary}
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <StatCard label="Critical" value={critical} color="#f85149" />
                <StatCard label="High" value={high} color="#f0883e" />
                <StatCard label="Medium" value={medium} color="#e3b341" />
                <StatCard label="Files" value={report.files_scanned} color="#58a6ff" />
              </div>
            </div>
          </section>

          <section style={{ marginTop: 28 }}>
            <h2 style={{ fontSize: 18, marginBottom: 4 }}>Remediation Recommendations</h2>
            <div style={{ fontSize: 13, color: "#8b98a5", marginBottom: 16 }}>
              {findings.length === 0
                ? "No issues detected — baseline secure across all enabled checks."
                : `${findings.length} finding(s) to remediate:`}
            </div>
            {findings.map((f, i) => (
              <RemediationCard key={`${f.cwe}-${f.file}-${f.line ?? i}`} finding={f} />
            ))}
          </section>

          <footer style={{ marginTop: 32, fontSize: 12, color: "#6b7682" }}>
            Tool: {report.tool} v{report.version} · scanned_at: {report.scanned_at}
            {lastScan ? ` · last refresh: ${lastScan}` : ""} · checks:{" "}
            {report.checks_run.join(", ")}
          </footer>
        </>
      )}
    </main>
  );
}
