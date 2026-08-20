import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import { statSync } from "node:fs";
import { existsSync } from "node:fs";
import { promises as fs } from "node:fs";
import path from "node:path";
import type { ScanReport } from "@/lib/types";

/**
 * GET /api/report
 *
 * Runs the DM SecureGate CLI engine against the target repository on demand and
 * returns the standardized JSON scan report. This is what makes the dashboard
 * "dynamic" — every refresh re-scans the live source tree.
 *
 * Target resolution order:
 *   1. ?target=<abs-or-rel-path> query param
 *   2. SECUREGATE_TARGET env var
 *   3. Default: the sibling expense-tracker repository
 *
 * If the Python engine is unavailable, it falls back to a committed sample
 * report (web-ui/sample-report.json) so the UI still renders.
 */
export const dynamic = "force-dynamic";

function resolveTarget(): string {
  const cwd = process.cwd();
  const env = process.env.SECUREGATE_TARGET;
  const candidates: string[] = [];
  if (env) candidates.push(path.resolve(cwd, env));
  // default: ../../expense-tracker relative to web-ui/ (i.e. sibling of dm-securegate)
  candidates.push(path.resolve(cwd, "..", "..", "expense-tracker"));
  // secondary heuristic: ../expense-tracker (when cwd is the repo root)
  candidates.push(path.resolve(cwd, "..", "expense-tracker"));
  for (const c of candidates) {
    try {
      if (statSync(c).isDirectory()) return c;
    } catch {
      /* keep looking */
    }
  }
  return candidates[0];
}

function findCliDir(): string | null {
  // Prefer an explicit location supplied by `dm-secure ui` (or the operator).
  const env = process.env.SECUREGATE_CLI_DIR;
  if (env) return env;
  // web-ui/ -> ../cli  (and repo-root layouts)
  const cwd = process.cwd();
  for (const rel of [
    ["..", "cli"],
    ["cli"],
    ["..", "..", "cli"],
  ]) {
    const p = path.resolve(cwd, ...rel);
    if (existsSync(path.join(p, "dm_secure", "cli.py"))) return p;
  }
  return null;
}

function runScanner(target: string): Promise<ScanReport> {
  return new Promise((resolve, reject) => {
    const cliDir = findCliDir();
    if (!cliDir) return reject(new Error("cli dir not found"));
    execFile(
      "python3",
      ["-m", "dm_secure", target],
      { cwd: cliDir, maxBuffer: 10 * 1024 * 1024 },
      (err, stdout, stderr) => {
        if (err && !stdout) {
          return reject(new Error(stderr || err.message));
        }
        try {
          const parsed = JSON.parse(stdout) as ScanReport;
          resolve(parsed);
        } catch (e) {
          reject(new Error("failed to parse scanner output: " + (e as Error).message));
        }
      }
    );
  });
}

async function loadSample(): Promise<ScanReport> {
  const p = path.join(process.cwd(), "sample-report.json");
  const raw = await fs.readFile(p, "utf-8");
  return JSON.parse(raw) as ScanReport;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const targetParam = searchParams.get("target");
  const target = targetParam
    ? path.resolve(process.cwd(), targetParam)
    : resolveTarget();

  try {
    const report = await runScanner(target);
    return NextResponse.json(report);
  } catch (e) {
    // Fallback so the dashboard still renders if the engine can't run here.
    try {
      const sample = await loadSample();
      return NextResponse.json({
        ...sample,
        summary:
          sample.summary + " (sample — live scanner unavailable: " + (e as Error).message + ")",
      });
    } catch {
      return NextResponse.json(
        { error: "scanner unavailable", detail: (e as Error).message },
        { status: 500 }
      );
    }
  }
}
