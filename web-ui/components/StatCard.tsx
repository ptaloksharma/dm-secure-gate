export function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <div
      style={{
        background: "#10151c",
        border: "1px solid #1f2933",
        borderRadius: 12,
        padding: "16px 18px",
        minWidth: 120,
        flex: 1,
      }}
    >
      <div style={{ fontSize: 30, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 12, color: "#8b98a5", letterSpacing: 0.4, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}
