"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { fetchSection, Manga, truncate, getScoreColor, getStatusLabel } from "@/lib/anilist";

// Akari split-card hero + color theming: background tints with active manga's cover color
export function HeroCarousel() {
  const [heroPool, setHeroPool] = useState<Manga[]>([]);
  const [heroIndex, setHeroIndex] = useState(0);
  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchSection("TRENDING_DESC", null, 6);
        setHeroPool(data);
      } catch (e) {
        console.error("Failed to load hero", e);
      }
    })();
  }, []);

  const goToHero = useCallback((i: number) => {
    if (transitioning || i === heroIndex) return;
    setTransitioning(true);
    setTimeout(() => {
      setHeroIndex(i);
      setTimeout(() => setTransitioning(false), 600);
    }, 300);
  }, [transitioning, heroIndex]);

  useEffect(() => {
    if (heroPool.length < 2) return;
    const interval = setInterval(() => {
      goToHero((heroIndex + 1) % heroPool.length);
    }, 7000);
    return () => clearInterval(interval);
  }, [heroPool, heroIndex, goToHero]);

  if (heroPool.length === 0) {
    return (
      <section className="split-hero split-hero-loading">
        <div className="skeleton split-hero-cover-skel"></div>
        <div className="split-hero-info">
          <div className="skeleton" style={{ width: 80, height: 24, marginBottom: 16 }}></div>
          <div className="skeleton" style={{ width: "70%", height: 40, marginBottom: 12 }}></div>
          <div className="skeleton" style={{ width: "40%", height: 14, marginBottom: 24 }}></div>
          <div className="split-hero-meta-grid">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="split-hero-meta-cell">
                <div className="skeleton" style={{ width: 60, height: 10, marginBottom: 6 }}></div>
                <div className="skeleton" style={{ width: 80, height: 16 }}></div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  const current = heroPool[heroIndex];
  if (!current) return null;
  const title = current.title.english || current.title.romaji;
  const coverUrl = current.coverImage?.extraLarge || current.coverImage?.large;
  const heroColor = current.coverImage?.color || "#888";

  return (
    <section
      className={`split-hero ${transitioning ? "transitioning" : ""}`}
      style={{ ["--hero-color" as string]: heroColor }}
    >
      {/* Color-tinted background glow (uses active manga's cover color) */}
      <div className="split-hero-bg-tint" aria-hidden="true"></div>

      <Link href={`/manga/${current.id}`} className="split-hero-cover-wrap">
        <div className="split-hero-cover-shadow"></div>
        <img src={coverUrl} alt={title} className="split-hero-cover" />
        {current.averageScore && (
          <div className="split-hero-cover-score" style={{ color: getScoreColor(current.averageScore) }}>
            <span className="star">★</span>
            <span>{(current.averageScore / 10).toFixed(1)}</span>
          </div>
        )}
      </Link>

      <div className="split-hero-info">
        <div className="split-hero-badge">
          <span className="pulse-dot"></span>
          <span>#{heroIndex + 1} Trending</span>
        </div>
        <h1 className="split-hero-title">{title}</h1>
        {current.title.english && current.title.romaji && current.title.english !== current.title.romaji && (
          <div className="split-hero-romaji">{current.title.romaji}</div>
        )}

        <div className="split-hero-meta-grid">
          <div className="split-hero-meta-cell">
            <div className="split-hero-meta-label">Status</div>
            <div className="split-hero-meta-value">
              <span className={`status-dot ${current.status === "RELEASING" ? "ongoing" : "done"}`}></span>
              {getStatusLabel(current.status)}
            </div>
          </div>
          <div className="split-hero-meta-cell">
            <div className="split-hero-meta-label">Type</div>
            <div className="split-hero-meta-value">{current.format || "Manga"}</div>
          </div>
          <div className="split-hero-meta-cell">
            <div className="split-hero-meta-label">Chapters</div>
            <div className="split-hero-meta-value">{current.chapters ?? "—"}</div>
          </div>
          <div className="split-hero-meta-cell">
            <div className="split-hero-meta-label">Year</div>
            <div className="split-hero-meta-value">{current.startDate?.year ?? "—"}</div>
          </div>
        </div>

        <div className="split-hero-genres">
          {current.genres.slice(0, 5).map((g) => (
            <span key={g} className="split-hero-genre-pill">{g}</span>
          ))}
        </div>

        <p className="split-hero-desc">{truncate(current.description || "No description available.", 240)}</p>

        <div className="split-hero-actions">
          <Link href={`/manga/${current.id}`} className="btn-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 16, height: 16 }}>
              <path d="M5 4v17M5 4h11l-3 4 3 4H5" />
            </svg>
            <span>Start Reading</span>
          </Link>
          <a href={`https://anilist.co/manga/${current.id}`} target="_blank" rel="noopener" className="btn-secondary">
            <span>View on AniList</span>
          </a>
          <div className="split-hero-pager">
            <button onClick={() => goToHero((heroIndex - 1 + heroPool.length) % heroPool.length)} aria-label="Previous">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}><path d="M15 18l-6-6 6-6" /></svg>
            </button>
            <span className="split-hero-pager-count">{heroIndex + 1} / {heroPool.length}</span>
            <button onClick={() => goToHero((heroIndex + 1) % heroPool.length)} aria-label="Next">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}><path d="M9 6l6 6-6 6" /></svg>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
