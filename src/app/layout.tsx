import type { Metadata, Viewport } from "next";
import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "MangaMaru — Discover Your Next Manga Obsession",
  description: "The cinematic way to discover and read manga. Powered by AniList. Sidebar navigation, dual-mode reader, calendar, bookmarks.",
  manifest: "/manifest.json",
  icons: {
    icon: [{ url: "/favicon.png", type: "image/png" }, { url: "/favicon.svg", type: "image/svg+xml" }],
    apple: "/favicon.png",
  },
  openGraph: {
    title: "MangaMaru — Discover Your Next Manga Obsession",
    description: "The cinematic way to discover and read manga. Powered by AniList.",
    type: "website",
    url: "https://manga.luffytv.online",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#000000",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
