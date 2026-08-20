/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output lets us ship a self-contained server (incl. API routes like
  // /api/report and /api/strix/*) inside the dm-secure-gate wheel. `dm-secure ui`
  // launches the produced server.js with Node — no separate `npm install` needed.
  output: "standalone",
};

export default nextConfig;
