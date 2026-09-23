"use client";
import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { TopBar } from "@/components/layout/TopBar";
import { fetchSection, Manga } from "@/lib/anilist";

export default function LibraryPage() {
  const [popular, setPopular] = useState<Manga[]>([]);
  const [activeLetter, setActiveLetter] = useState("#");

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchSection("POPULARITY_DESC", null, 60);
        setPopular(data);
      } catch (e) { console.error(e); }
    })();
  }, []);

  const groupedByLetter = useMemo(() => {
    const groups: Record<string, Manga[]> = {};
    popular.forEach((m) => {
      const t = m.title.english || m.title.romaji;
      const first = t[0]?.toUpperCase() || "#";
      const letter = /[A-Z]/.test(first) ? first : "#";
      if (!groups[letter]) groups[letter] = [];
      groups[letter].push(m);
    });
    return groups;
  }, [popular]);

  const letters = ["#", ...Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i))];

  const scrollToLetter = (letter: string) => {
    setActiveLetter(letter);
    document.getElementById(`letter-${letter}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    const handler = () => {
      for (let i = letters.length - 1; i >= 0; i--) {
        const el = document.getElementById(`letter-${letters[i]}`);
        if (el && el.getBoundingClientRect().top < 220) {
          setActiveLetter(letters[i]);
          break;
        }
      }
    };
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, [letters]);

  return (
    <>
      <TopBar />
      <div className="lib-page">
        <div className="lib-header">
          <h1 className="page-title">Library</h1>
          <p className="page-subtitle">{popular.length > 0 ? `${popular.length} manga to explore — bookmark to save to your collection` : "Loading popular manga…"}</p>
        </div>

        {popular.length > 5 && (
          <div className="alphabet-rail">
            {letters.map((l) => {
              const has = groupedByLetter[l];
              return (
                <button
                  key={l}
                  className={`alphabet-letter ${activeLetter === l ? "active" : ""} ${!has ? "empty" : ""}`}
                  onClick={() => has && scrollToLetter(l)}
                  disabled={!has}
                >
                  {l}
                </button>
              );
            })}
          </div>
        )}

        {popular.length === 0 ? (
          <div className="omni-grid">
            {Array.from({ length: 12 }).map((_, i) => <div key={i} className="skeleton omni-grid-skel" style={{ animationDelay: `${i * 60}ms` }} />)}
          </div>
        ) : (
          <div>
            {letters.map((letter) => {
              const items = groupedByLetter[letter];
              if (!items || items.length === 0) return null;
              return (
                <div key={letter} className="letter-group" id={`letter-${letter}`}>
                  <div className="letter-header">{letter}</div>
                  <div className="omni-grid">
                    {items.map((m) => (
                      <Link key={m.id} href={`/manga/${m.id}`} className="dense-card">
                        <div className="dense-card-cover">
                          <img src={m.coverImage?.extraLarge || m.coverImage?.large} alt={m.title.english || m.title.romaji} loading="lazy" />
                          <div className="dense-card-overlay"></div>
                          <div className="dense-card-title-overlay">
                            <div className="dense-card-title">{m.title.english || m.title.romaji}</div>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
