"use client";
import { useState, useEffect } from "react";
import { Manga, Mood, fetchSection, getScoreColor, getStatusLabel } from "@/lib/anilist";
import Link from "next/link";

interface MoodGridProps {
  mood: Mood;
  onLoad?: (manga: Manga[]) => void;
}

export function MoodGrid({ mood, onLoad }: MoodGridProps) {
  const [data, setData] = useState<Manga[]>([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(24);

  useEffect(() => {
    setLoading(true);
    setData([]);
    fetchSection("POPULARITY_DESC", mood.genre, limit)
      .then((d) => { setData(d); onLoad?.(d); })
      .catch((e) => console.error("Mood grid load failed", e))
      .finally(() => setLoading(false));
  }, [mood.id, mood.genre, limit, onLoad]);

  const loadMore = () => setLimit((l) => l + 24);

  return (
    <section className="mood-grid-section" style={{ ["--mood-color" as string]: mood.color }}>
      <div className="mood-grid-header">
        <div>
          <span className="mood-grid-eyebrow">{mood.label}</span>
          <h2 className="mood-grid-title">Manga to read now</h2>
        </div>
        <div className="mood-grid-count">{data.length} titles</div>
      </div>

      {loading && data.length === 0 && (
        <div className="omni-grid">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton omni-grid-skel" style={{ animationDelay: `${i * 60}ms` }}></div>
          ))}
        </div>
      )}

      {data.length > 0 && (
        <div className="omni-grid" data-spotlight="on">
          {data.map((m, i) => (
            <Link
              key={m.id}
              href={`/manga/${m.id}`}
              className="dense-card"
              style={{ ["--card-color" as string]: m.coverImage?.color || "#888" }}
            >
              <div className="dense-card-cover">
                <img src={m.coverImage?.extraLarge || m.coverImage?.large} alt={m.title.english || m.title.romaji} loading="lazy" />
                <div className="dense-card-overlay"></div>
                <div className="dense-card-accent"></div>
                <div className="dense-card-glow"></div>
                {m.averageScore && (
                  <div className="dense-card-score" style={{ color: getScoreColor(m.averageScore) }}>
                    <span className="star">★</span>
                    <span>{(m.averageScore / 10).toFixed(1)}</span>
                  </div>
                )}
                {m.status && (
                  <div className="dense-card-status">{getStatusLabel(m.status)}</div>
                )}
                <div className="dense-card-title-overlay">
                  <div className="dense-card-title">{m.title.english || m.title.romaji}</div>
                  <div className="dense-card-meta">{m.format || "Manga"}{m.chapters ? ` · ${m.chapters} ch` : ""}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      <div className="mood-grid-actions">
        <button onClick={loadMore} className="mood-load-more" disabled={loading}>
          {loading ? "Loading…" : "Load 24 more"}
        </button>
      </div>
    </section>
  );
}
