import { NextResponse } from "next/server";
import { execFileSync } from "node:child_process";
import fs from "node:fs";

/**
 * GET /api/strix/status
 *
 * Reports whether an autonomous Strix pentest engine is available on the host.
 * Mirrors the Python `shutil.which("strix")` intent, but also probes a few known
 * install locations so we prefer a *runnable* binary over a broken PATH stub.
 *
 * Returns: { installed: boolean, path: string | null }
 */
export const dynamic = "force-dynamic";

function findStrix(): string | null {
  const home = process.env.HOME || "/home/opc";
  const candidates: string[] = [
    process.env.STRIX_BIN || "",
    `${home}/strix-venv/bin/strix`,
    "/home/opc/strix-venv/bin/strix",
    "/home/opc/.strix/bin/strix",
  ].filter(Boolean);

  // Also honour whatever `strix` resolves to on PATH (the shutil.which equivalent).
  try {
    const onPath = execFileSync("bash", ["-lc", "command -v strix"], {
      encoding: "utf-8",
    })
      .trim()
      .split(/\r?\n/)[0];
    if (onPath) candidates.push(onPath);
  } catch {
    /* not on PATH */
  }

  for (const c of candidates) {
    try {
      if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
    } catch {
      /* keep looking */
    }
  }
  return null;
}

export async function GET() {
  const path = findStrix();
  return NextResponse.json({ installed: path !== null, path });
}
