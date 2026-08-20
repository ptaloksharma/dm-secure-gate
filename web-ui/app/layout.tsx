import type { ReactNode } from "react";

export const metadata = {
  title: "DM SecureGate — Security Dashboard",
  description: "Static security baseline scanner & dashboard (CWE-798/306/942)",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          background: "#0b0f14",
          color: "#e6edf3",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
        }}
      >
        {children}
      </body>
    </html>
  );
}
