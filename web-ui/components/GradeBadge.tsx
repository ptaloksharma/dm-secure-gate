import { gradeColor } from "@/lib/theme";

export function GradeBadge({ grade }: { grade: string }) {
  const color = gradeColor(grade);
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 96,
        height: 96,
        borderRadius: "50%",
        border: `3px solid ${color}`,
        color,
        fontWeight: 800,
        fontSize: 44,
        lineHeight: 1,
        boxShadow: `0 0 24px ${color}55`,
      }}
    >
      {grade}
    </div>
  );
}
