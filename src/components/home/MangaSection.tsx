"use client";
import { useState, useRef, useCallback } from "react";
import Link from "next/link";
import { Manga, SectionConfig, fetchSection, getScoreColor } from "@/lib/anilist";
import { useLazyLoad, useReveal } from "@/hooks/use-intersection";
import { MangaCard } from "./MangaCard";

function Skeleton({ layout, count }: { layout: "grid" | "row"; count: number }) {
  if (layout === "row") {
    return (
      <div className="omni-row">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="skeleton omni-row-skel" style={{ animationDelay: `${i * 80}ms` }}></div>
        ))}
      </div>
    );
  }
  return (
    <div className="omni-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton omni-grid-skel" style={{ animationDelay: `${i * 60}ms` }}></div>
      ))}
    </div>
  );
}

export function MangaSection({ section, sectionNumber }: { section: SectionConfig; sectionNumber?: number }) {
  const [data, setData] = useState<Manga[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageSize, setPageSize] = useState(section.perPage);
  const rowRef = useRef<HTMLDivElement>(null);
  const { ref: revealRef, inView } = useReveal<HTMLDivElement>();

  const load = useCallback(async () => {
    if (data || loading) return;
    setLoading(true);
    try {
      const r = await fetchSection(section.sort, section.genre || null, pageSize);
      setData(r);
    } catch (e) {
      console.error(`Failed to load section ${section.id}`, e);
      setData([]);
    }
    setLoading(false);
  }, [section, data, loading, pageSize]);

  const sectionRef = useLazyLoad<HTMLDivElement>(load, "400px");

  const scrollRow = (dir: number) => {
    if (rowRef.current) rowRef.current.scrollBy({ left: dir * 700, behavior: "smooth" });
  };

  const num = sectionNumber != null ? String(sectionNumber).padStart(2, "0") : "";

  return (
    <section ref={sectionRef} id={section.id} className={`omni-section ${inView ? "in-view" : ""}`}>
      {num && <div className="omni-section-bignum" aria-hidden="true">{num}</div>}

      <div className="omni-section-header">
        <div className="omni-section-title-wrap">
          {num && <span className="omni-section-num">{num}</span>}
          <h2 className="omni-section-title">{section.title}</h2>
        </div>
        <div className="omni-section-controls">
          <select
            className="omni-page-size"
            value={pageSize}
            onChange={(e) => { setPageSize(parseInt(e.target.value)); setData(null); }}
          >
            <option value={6}>Show 6</option>
            <option value={12}>Show 12</option>
            <option value={18}>Show 18</option>
            <option value={24}>Show 24</option>
          </select>
          {section.layout === "row" && (
            <div className="omni-pager">
              <button onClick={() => scrollRow(-1)} aria-label="Scroll left">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}><path d="M15 18l-6-6 6-6" /></svg>
              </button>
              <button onClick={() => scrollRow(1)} aria-label="Scroll right">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}><path d="M9 6l6 6-6 6" /></svg>
              </button>
            </div>
          )}
        </div>
      </div>

      {!data && <Skeleton layout={section.layout} count={section.layout === "row" ? 6 : 12} />}

      {data && data.length > 0 && section.layout === "row" && (
        <div id={`${section.id}-scroll`} className="omni-row" ref={rowRef}>
          {data.map((m, i) => (
            <div key={m.id} className="omni-row-card-wrap">
              {section.badge === "rank" && <div className="omni-row-rank">#{i + 1}</div>}
              <Link href={`/manga/${m.id}`} className="omni-row-card" style={{ ["--card-color" as string]: m.coverImage?.color || "#dc2626" }}>
                <div className="omni-row-cover">
                  <div className="omni-row-accent"></div>
                  <img src={m.coverImage?.extraLarge || m.coverImage?.large} alt={m.title.english || m.title.romaji} loading="lazy" />
                  <div className="omni-row-overlay"></div>
                  <div className="omni-row-glow"></div>
                  {m.averageScore && (
                    <div className="dense-card-score" style={{ color: getScoreColor(m.averageScore) }}>
                      <span className="star">★</span>
                      <span>{(m.averageScore / 10).toFixed(1)}</span>
                    </div>
                  )}
                  <div className="omni-row-info">
                    <div className="omni-row-title">{m.title.english || m.title.romaji}</div>
                    <div className="omni-row-sub">{m.format || "Manga"}{m.chapters ? ` · ${m.chapters} ch` : ""}</div>
                  </div>
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}

      {data && data.length > 0 && section.layout === "grid" && (
        <div className="omni-grid">
          {data.map((m) => (
            <MangaCard key={m.id} manga={m} />
          ))}
        </div>
      )}

      {data && data.length === 0 && (
        <div style={{ color: "#666", padding: "20px 0", fontSize: 13 }}>No data available.</div>
      )}
    </section>
  );
}
