export type Severity = "Critical" | "High" | "Medium" | "Low" | "Info";

export interface Finding {
  cwe: string;
  title: string;
  severity: Severity;
  file: string;
  line?: number | null;
  snippet?: string;
  description?: string;
  recommendation?: string;
  confidence?: string;
}

export interface ScanReport {
  tool: string;
  version: string;
  target: string;
  scanned_at: string;
  files_scanned: number;
  checks_run: string[];
  findings: Finding[];
  grade: string;
  counts: Record<string, number>;
  summary: string;
}
