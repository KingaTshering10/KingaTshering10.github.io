import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "DrukAgriLink",
  description:
    "Bhutan-focused agricultural aggregation, market coordination, and shared-transport platform.",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#4a7230",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-earth-50 text-field-800 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
