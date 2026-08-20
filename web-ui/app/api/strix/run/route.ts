import { spawn } from "node:child_process";
import { execFileSync } from "node:child_process";
import fs from "node:fs";

/**
 * POST /api/strix/run
 *
 * Triggers an autonomous Strix execution against a target and streams live agent
 * progress back to the browser as Server-Sent Events (text/event-stream).
 *
 * Body: { target?: string, install?: boolean }
 *   - install=true (or strix missing): pipe the official installer through bash.
 *   - otherwise: spawn `strix --target <path> -n -m quick` and forward its stdout/stderr.
 */
export const dynamic = "force-dynamic";

const INSTALL_CMD =
  "curl -sSL https://strix.ai/install | bash";

function findStrix(): string | null {
  const home = process.env.HOME || "/home/opc";
  const candidates: string[] = [
    process.env.STRIX_BIN || "",
    `${home}/strix-venv/bin/strix`,
    "/home/opc/strix-venv/bin/strix",
    "/home/opc/.strix/bin/strix",
  ].filter(Boolean);
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

export async function POST(request: Request) {
  let body: { target?: string; install?: boolean } = {};
  try {
    body = await request.json();
  } catch {
    /* empty body is fine */
  }

  const target =
    body.target || process.env.SECUREGATE_TARGET || process.cwd();
  const doInstall = !!body.install;
  const strix = findStrix();

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      let closed = false;
      const send = (line: string) => {
        if (closed) return;
        const clean = line.replace(/\n+$/, "");
        try {
          controller.enqueue(encoder.encode(`data: ${clean}\n\n`));
        } catch {
          closed = true;
        }
      };
      const finish = (tail: string) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`data: ${tail}\n\n`));
          controller.close();
        } catch {
          /* already closed */
        }
        closed = true;
      };

      if (doInstall || !strix) {
        send("[strix] engine not found locally — launching installer…");
        const proc = spawn("bash", ["-c", INSTALL_CMD], {
          env: process.env,
        });
        proc.stdout.on("data", (d) => send("[install] " + d.toString()));
        proc.stderr.on("data", (d) => send("[install] " + d.toString()));
        proc.on("error", (e) => send("[install] error: " + (e as Error).message));
        proc.on("close", (code) => {
          send(`[install] installer exited (${code})`);
          finish("__DONE__");
        });
        return;
      }

      send(`[strix] launching autonomous pentest → target: ${target}`);
      send(`[strix] engine: ${strix}`);
      const proc = spawn(strix, ["--target", target, "-n", "-m", "quick"], {
        env: process.env,
      });
      proc.stdout.on("data", (d) => send(d.toString()));
      proc.stderr.on("data", (d) => send(d.toString()));
      proc.on("error", (e) => send("[strix] error: " + (e as Error).message));
      proc.on("close", (code) => {
        send(`[strix] pentest finished (exit ${code})`);
        finish("__DONE__");
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
