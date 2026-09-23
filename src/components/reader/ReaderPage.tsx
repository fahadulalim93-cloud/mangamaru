"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { TopBar } from "@/components/layout/TopBar";
import { useKeyboardShortcuts } from "@/hooks/use-intersection";

export function ReaderPage({ mangaId, chapter }: { mangaId: number; chapter: string }) {
  const [mode, setMode] = useState<"page" | "strip">("page");
  const [direction, setDirection] = useState<"ltr" | "rtl">("ltr");
  const [pageIndex, setPageIndex] = useState(0);
  const [pages, setPages] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const placeholders = Array.from({ length: 12 }).map((_, i) =>
      `https://placehold.co/800x1200/000000/ffffff?text=Page+${i + 1}&font=Poppins`
    );
    setPages(placeholders);
    setLoading(false);
  }, [mangaId, chapter]);

  const nextPage = useCallback(() => setPageIndex((i) => Math.min(i + 1, pages.length - 1)), [pages.length]);
  const prevPage = useCallback(() => setPageIndex((i) => Math.max(i - 1, 0)), []);

  useKeyboardShortcuts({
    nextPage: direction === "ltr" ? nextPage : prevPage,
    prevPage: direction === "ltr" ? prevPage : nextPage,
  });

  useEffect(() => {
    if (pages.length === 0) return;
    const key = `manga-progress:${mangaId}:${chapter}`;
    localStorage.setItem(key, String(pageIndex));
  }, [mangaId, chapter, pageIndex, pages.length]);

  useEffect(() => {
    const key = `manga-progress:${mangaId}:${chapter}`;
    const saved = localStorage.getItem(key);
    if (saved) {
      const i = parseInt(saved, 10);
      if (Number.isFinite(i) && i >= 0 && i < pages.length) setPageIndex(i);
    }
  }, [mangaId, chapter, pages.length]);

  if (loading) {
    return (
      <>
        <TopBar />
        <div style={{ padding: 60, display: "flex", justifyContent: "center" }}>
          <div className="skeleton" style={{ width: 800, height: 1200, borderRadius: 12 }} />
        </div>
      </>
    );
  }

  return (
    <>
      <TopBar />
      <div className="reader-controls">
        <Link href={`/manga/${mangaId}`} className="back-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}><path d="M15 18l-6-6 6-6" /></svg>
          <span>Back to manga</span>
        </Link>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>Chapter {chapter}</span>
          <span style={{ fontSize: 12, color: "var(--dim)", padding: "4px 10px", background: "rgba(255,255,255,0.04)", borderRadius: 10 }}>{pageIndex + 1} / {pages.length}</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={`reader-toggle ${mode === "page" ? "active" : ""}`} onClick={() => setMode("page")} title="Page-by-page (panel-frame)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 16, height: 16 }}><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 12h18M12 3v18" /></svg>
          </button>
          <button className={`reader-toggle ${mode === "strip" ? "active" : ""}`} onClick={() => setMode("strip")} title="Vertical strip (webtoon)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 16, height: 16 }}><rect x="6" y="3" width="12" height="18" rx="2" /><path d="M6 9h12M6 15h12" /></svg>
          </button>
          <button className={`reader-toggle ${direction === "rtl" ? "active" : ""}`} onClick={() => setDirection((d) => (d === "ltr" ? "rtl" : "ltr"))} title="Toggle reading direction">
            <span style={{ fontSize: 11, fontWeight: 700 }}>{direction === "ltr" ? "LTR" : "RTL"}</span>
          </button>
        </div>
      </div>

      {mode === "page" ? (
        <div className={`page-reader ${direction === "rtl" ? "rtl" : ""}`}>
          <button className="page-nav-btn page-nav-prev" onClick={prevPage} disabled={pageIndex === 0}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 24, height: 24 }}><path d="M15 18l-6-6 6-6" /></svg>
          </button>
          <div className="page-frame with-frame">
            <img src={pages[pageIndex]} alt={`Page ${pageIndex + 1}`} className="page-image" />
          </div>
          <button className="page-nav-btn page-nav-next" onClick={nextPage} disabled={pageIndex === pages.length - 1}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 24, height: 24 }}><path d="M9 6l6 6-6 6" /></svg>
          </button>
          <div className="page-progress">
            <div className="page-progress-bar" style={{ width: `${((pageIndex + 1) / pages.length) * 100}%` }} />
          </div>
        </div>
      ) : (
        <div className="strip-reader">
          {pages.map((src, i) => (
            <img key={i} src={src} alt={`Page ${i + 1}`} className="strip-image" loading={i < 2 ? "eager" : "lazy"} />
          ))}
        </div>
      )}
    </>
  );
}
