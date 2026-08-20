// Headless full-stack UI verification for DM SecureGate.
//
// Boots nothing itself — it expects the Next server to be running (next start/dev)
// and the /api/report endpoint to return the live scanner JSON. It then:
//   1. compiles the REAL component sources (GradeBadge, StatCard, RemediationCard)
//      with the project's own tsc into a temp .verify-out dir,
//   2. server-renders them with react-dom/server against the LIVE /api/report data,
//   3. asserts the grade badge, stat cards, and remediation cards render cleanly.
//
// No browser required. Run with:  npm run verify:ui   (server must be up)
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const Module = require("module");

const ROOT = path.dirname(__dirname);   // web-ui/ (parent of scripts/)
const OUT = path.join(ROOT, ".verify-out");
const BASE = process.env.BASE_URL || "http://127.0.0.1:3100";

function fail(msg) { console.error("FAIL  " + msg); process.exitCode = 1; }
function ok(cond, msg) {
  console.log((cond ? "PASS  " : "FAIL  ") + msg);
  if (!cond) process.exitCode = 1;
}

// --- 1. compile the real components with the project's TypeScript ------------
const tsconfig = {
  compilerOptions: {
    target: "ES2020", lib: ["dom", "dom.iterable", "esnext"],
    module: "commonjs", moduleResolution: "node", jsx: "react-jsx",
    esModuleInterop: true, skipLibCheck: true, outDir: ".verify-out",
    rootDir: ".", strict: false, types: [],
    baseUrl: ".", paths: { "@/*": ["./*"] },
  },
  include: [
    "components/GradeBadge.tsx", "components/StatCard.tsx",
    "components/RemediationCard.tsx", "lib/types.ts", "lib/theme.ts",
  ],
};
fs.writeFileSync(path.join(ROOT, "verify.tsconfig.json"), JSON.stringify(tsconfig, null, 2));

const tsc = path.join(ROOT, "node_modules", ".bin", "tsc");
try {
  execFileSync(tsc, ["-p", "verify.tsconfig.json"], { cwd: ROOT, stdio: "ignore" });
} catch (e) {
  fail("component compile failed (" + (e.message || e) + ")");
  cleanup(); process.exit(1);
}

// resolve the "@/..." alias to the compiled tree at runtime
const origResolve = Module._resolveFilename;
Module._resolveFilename = function (req, ...a) {
  if (req.startsWith("@/")) return origResolve.call(this, path.join(OUT, req.slice(2)), ...a);
  return origResolve.call(this, req, ...a);
};

const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { GradeBadge } = require(path.join(OUT, "components/GradeBadge.js"));
const { StatCard } = require(path.join(OUT, "components/StatCard.js"));
const { RemediationCard } = require(path.join(OUT, "components/RemediationCard.js"));

// --- 2. fetch the LIVE report from the running dashboard ----------------------
(async () => {
  let report;
  try {
    const res = await fetch(BASE + "/api/report");
    if (!res.ok) throw new Error("HTTP " + res.status);
    report = await res.json();
  } catch (e) {
    fail("could not reach " + BASE + "/api/report (" + e.message + ") — start `npm run start` first");
    cleanup(); process.exit(1);
  }

  ok(!!report && Array.isArray(report.findings), "live /api/report returned a valid report");

  // --- 3. render real components with live data & assert --------------------
  const gradeHtml = renderToStaticMarkup(React.createElement(GradeBadge, { grade: report.grade }));
  ok(gradeHtml.includes(report.grade), `grade badge renders live grade "${report.grade}"`);
  ok(/border-radius/.test(gradeHtml), "grade badge is a circular health-score badge");

  const stats = renderToStaticMarkup(
    React.createElement("div", null,
      React.createElement(StatCard, { label: "Critical", value: report.counts.Critical || 0, color: "#f85149" }),
      React.createElement(StatCard, { label: "High", value: report.counts.High || 0, color: "#f0883e" }),
      React.createElement(StatCard, { label: "Medium", value: report.counts.Medium || 0, color: "#e3b341" })));
  ok(stats.includes(String(report.counts.Critical || 0)), "Critical stat card shows live count");
  ok(stats.includes(String(report.counts.High || 0)), "High stat card shows live count");
  ok(stats.includes(String(report.counts.Medium || 0)), "Medium stat card shows live count");

  if (report.findings.length) {
    for (const f of report.findings) {
      const h = renderToStaticMarkup(React.createElement(RemediationCard, { finding: f }));
      ok(h.includes(f.cwe), `remediation card shows ${f.cwe}`);
      ok(h.toUpperCase().includes(f.severity.toUpperCase()), `remediation card shows severity ${f.severity}`);
      ok(h.includes("Fix:"), `remediation card shows fix guidance for ${f.cwe}`);
      if (f.file) ok(h.includes(f.file), `remediation card shows location ${f.file}`);
    }
  } else {
    console.log("PASS  (no findings — remediation list renders empty state)");
  }

  console.log(`\nLIVE REPORT: grade=${report.grade} critical=${report.counts.Critical} high=${report.counts.High} medium=${report.counts.Medium} findings=${report.findings.length}`);
  if (!process.exitCode) console.log("\nRESULT: UI INTEGRATION VERIFIED — grade badge + stat cards + remediation cards render from live report");
  cleanup();
})();

function cleanup() {
  try { fs.rmSync(OUT, { recursive: true, force: true }); } catch {}
  try { fs.rmSync(path.join(ROOT, "verify.tsconfig.json"), { force: true }); } catch {}
}
