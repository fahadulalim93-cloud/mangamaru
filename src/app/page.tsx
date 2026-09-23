"use client";
import { useEffect, useState } from "react";
import { HeroCarousel } from "@/components/home/HeroCarousel";
import { MangaSection } from "@/components/home/MangaSection";
import { TopBar } from "@/components/layout/TopBar";
import { SECTIONS } from "@/lib/anilist";

export default function HomePage() {
  const [showScrollTop, setShowScrollTop] = useState(false);

  useEffect(() => {
    const handler = () => setShowScrollTop(window.scrollY > 600);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <>
      <TopBar mangaCount={8800} />
      <HeroCarousel />
      {SECTIONS.map((section, i) => (
        <MangaSection key={section.id} section={section} sectionNumber={i + 1} />
      ))}
      <footer className="omni-footer">
        <div className="omni-footer-inner">
          <div className="omni-footer-brand">
            <img src="/logo-small.png" alt="MangaMaru" style={{ height: 32, marginBottom: 8 }} />
            <p>The cinematic way to discover your next manga obsession.</p>
          </div>
          <div className="omni-footer-links">
            <a href="https://anilist.co" target="_blank" rel="noopener">Data: AniList</a>
            <a href="https://everythingmoe.com/section/manga" target="_blank" rel="noopener">More manga sites</a>
            <a href="https://luffytv.live" target="_blank" rel="noopener">LuffyTV</a>
            <a href="https://github.com/fahadulalim93-cloud/mangamaru" target="_blank" rel="noopener">GitHub</a>
          </div>
        </div>
      </footer>
      {showScrollTop && (
        <button
          className="scroll-top-fab"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          aria-label="Scroll to top"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 22, height: 22 }}>
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      )}
    </>
  );
}
