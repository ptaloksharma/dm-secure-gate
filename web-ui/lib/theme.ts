import type { ScanReport } from "@/lib/types";

const GRADE_COLORS: Record<string, string> = {
  A: "#3fb950",
  B: "#d29922",
  C: "#e3b341",
  D: "#f0883e",
  F: "#f85149",
};

export function gradeColor(grade: string): string {
  return GRADE_COLORS[grade] ?? "#8b98a5";
}

export const SEVERITY_COLORS: Record<string, string> = {
  Critical: "#f85149",
  High: "#f0883e",
  Medium: "#e3b341",
  Low: "#58a6ff",
  Info: "#8b98a5",
};
