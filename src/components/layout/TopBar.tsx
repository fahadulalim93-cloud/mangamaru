"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { searchManga, getScoreColor, Manga } from "@/lib/anilist";

// Omnibus-inspired: header-heavy top bar with logo + breadcrumb counter + big search + user menu
export function TopBar({ mangaCount = 0 }: { mangaCount?: number }) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [results, setResults] = useState<Manga[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r = await searchManga(query);
        setResults(r);
        setShowResults(true);
      } catch (e) {
        console.error("search failed", e);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [query]);

  // ⌘K shortcut to focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        const input = document.querySelector<HTMLInputElement>(".topbar-search-input");
        input?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <header className={`topbar ${scrolled ? "scrolled" : ""}`}>
      <div className="topbar-left">
        <Link href="/" className="topbar-logo">
          <img src="/logo-small.png" alt="MangaMaru" className="topbar-logo-img" />
        </Link>
        {mangaCount > 0 && (
          <span className="topbar-counter">
            {mangaCount.toLocaleString()} Manga
          </span>
        )}
      </div>

      <div className="topbar-search-wrap">
        <div className={`topbar-search ${focused || query ? "focus" : ""}`}>
          <svg className="topbar-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            className="topbar-search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => { setFocused(false); setShowResults(false); }, 200)}
            placeholder="What are we reading today?  (⌘K)"
            aria-label="Search manga"
          />
          {query && (
            <button
              className="topbar-search-clear"
              onClick={() => { setQuery(""); setShowResults(false); setResults([]); }}
              aria-label="Clear"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        {showResults && results.length > 0 && (
          <div className="topbar-search-dropdown">
            {results.map((m) => (
              <a key={m.id} href={`/manga/${m.id}`} className="topbar-search-item">
                <img
                  src={m.coverImage?.extraLarge || m.coverImage?.large}
                  alt=""
                  className="topbar-search-thumb"
                  loading="lazy"
                />
                <div className="topbar-search-meta">
                  <div className="topbar-search-title">{m.title.english || m.title.romaji}</div>
                  <div className="topbar-search-sub">
                    <span>{m.format || "Manga"}</span>
                    {m.chapters && <span>· {m.chapters} ch</span>}
                    {m.averageScore && (
                      <span className="topbar-search-score" style={{ color: getScoreColor(m.averageScore) }}>
                        ★ {(m.averageScore / 10).toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      <div className="topbar-right">
        <Link href="/library" className="topbar-nav-link">Library</Link>
        <Link href="/calendar" className="topbar-nav-link">Calendar</Link>
        <Link href="/settings" className="topbar-icon-btn" aria-label="Settings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 18, height: 18 }}>
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </Link>
      </div>
    </header>
  );
}
