import type { Finding } from "@/lib/types";
import { SEVERITY_COLORS } from "@/lib/theme";

export function RemediationCard({ finding }: { finding: Finding }) {
  const color = SEVERITY_COLORS[finding.severity] ?? "#8b98a5";
  return (
    <div
      style={{
        background: "#10151c",
        border: `1px solid ${color}55`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 10,
        padding: "14px 16px",
        marginBottom: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
        <span
          style={{
            background: color,
            color: "#0b0f14",
            fontSize: 11,
            fontWeight: 800,
            padding: "2px 8px",
            borderRadius: 6,
          }}
        >
          {finding.severity.toUpperCase()}
        </span>
        <span style={{ fontWeight: 700, color: "#e6edf3" }}>{finding.cwe}</span>
        <span style={{ color: "#8b98a5", fontSize: 13 }}>{finding.title}</span>
      </div>

      <div style={{ fontSize: 13, color: "#aeb9c4", marginBottom: 8 }}>
        {finding.description}
      </div>

      {finding.file && (
        <div
          style={{
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 12,
            color: "#58a6ff",
            marginBottom: 8,
          }}
        >
          {finding.file}
          {finding.line ? `:${finding.line}` : ""}
        </div>
      )}

      {finding.snippet && (
        <pre
          style={{
            background: "#0b0f14",
            border: "1px solid #1f2933",
            borderRadius: 6,
            padding: "8px 10px",
            fontSize: 12,
            color: "#ffa657",
            overflowX: "auto",
            margin: "0 0 8px 0",
          }}
        >
          {finding.snippet}
        </pre>
      )}

      {finding.recommendation && (
        <div style={{ fontSize: 13, color: "#3fb950" }}>
          <strong>Fix:</strong> {finding.recommendation}
        </div>
      )}
    </div>
  );
}
