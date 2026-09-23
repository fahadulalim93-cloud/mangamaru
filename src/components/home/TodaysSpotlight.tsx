"use client";
import Link from "next/link";
import { Manga, truncate, getScoreColor, getStatusLabel } from "@/lib/anilist";
import { useReveal } from "@/hooks/use-intersection";

interface SpotlightProps {
  manga: Manga[]; // expect 3 items
}

export function TodaysSpotlight({ manga }: SpotlightProps) {
  const { ref, inView } = useReveal<HTMLDivElement>();
  if (!manga || manga.length < 3) return null;
  const [hero, m1, m2] = manga;

  return (
    <section ref={ref} className={`spotlight-section ${inView ? "in-view" : ""}`}>
      <div className="spotlight-header">
        <span className="spotlight-eyebrow">Today&apos;s</span>
        <h2 className="spotlight-title">Spotlight</h2>
        <p className="spotlight-sub">Editor&apos;s picks of the moment — 3 reads worth your time</p>
      </div>

      <div className="spotlight-grid">
        {/* Big card (left, takes 2 cols + 2 rows) */}
        <Link href={`/manga/${hero.id}`} className="spotlight-card spotlight-card-big" style={{ ["--card-color" as string]: hero.coverImage?.color || "#888" }}>
          <div className="spotlight-card-cover">
            <img src={hero.coverImage?.extraLarge || hero.coverImage?.large} alt={hero.title.english || hero.title.romaji} loading="lazy" />
            <div className="spotlight-card-overlay"></div>
            <div className="spotlight-card-glow"></div>
            <div className="spotlight-card-accent"></div>
          </div>
          <div className="spotlight-card-info">
            <div className="spotlight-card-tags">
              {hero.genres.slice(0, 3).map((g) => (
                <span key={g} className="spotlight-tag">{g}</span>
              ))}
            </div>
            <h3 className="spotlight-card-title">{hero.title.english || hero.title.romaji}</h3>
            <p className="spotlight-card-desc">{truncate(hero.description || "", 160)}</p>
            <div className="spotlight-card-meta">
              {hero.averageScore && (
                <span className="spotlight-score" style={{ color: getScoreColor(hero.averageScore) }}>
                  ★ {(hero.averageScore / 10).toFixed(1)}
                </span>
              )}
              <span className="spotlight-status">{getStatusLabel(hero.status)}</span>
              {hero.chapters && <span>· {hero.chapters} ch</span>}
            </div>
          </div>
        </Link>

        {/* Two medium cards stacked right */}
        <Link href={`/manga/${m1.id}`} className="spotlight-card spotlight-card-med" style={{ ["--card-color" as string]: m1.coverImage?.color || "#888" }}>
          <div className="spotlight-card-cover">
            <img src={m1.coverImage?.extraLarge || m1.coverImage?.large} alt={m1.title.english || m1.title.romaji} loading="lazy" />
            <div className="spotlight-card-overlay"></div>
            <div className="spotlight-card-glow"></div>
            <div className="spotlight-card-accent"></div>
          </div>
          <div className="spotlight-card-info">
            <h3 className="spotlight-card-title">{m1.title.english || m1.title.romaji}</h3>
            <div className="spotlight-card-meta">
              {m1.averageScore && <span className="spotlight-score" style={{ color: getScoreColor(m1.averageScore) }}>★ {(m1.averageScore / 10).toFixed(1)}</span>}
              <span className="spotlight-status">{getStatusLabel(m1.status)}</span>
            </div>
          </div>
        </Link>

        <Link href={`/manga/${m2.id}`} className="spotlight-card spotlight-card-med" style={{ ["--card-color" as string]: m2.coverImage?.color || "#888" }}>
          <div className="spotlight-card-cover">
            <img src={m2.coverImage?.extraLarge || m2.coverImage?.large} alt={m2.title.english || m2.title.romaji} loading="lazy" />
            <div className="spotlight-card-overlay"></div>
            <div className="spotlight-card-glow"></div>
            <div className="spotlight-card-accent"></div>
          </div>
          <div className="spotlight-card-info">
            <h3 className="spotlight-card-title">{m2.title.english || m2.title.romaji}</h3>
            <div className="spotlight-card-meta">
              {m2.averageScore && <span className="spotlight-score" style={{ color: getScoreColor(m2.averageScore) }}>★ {(m2.averageScore / 10).toFixed(1)}</span>}
              <span className="spotlight-status">{getStatusLabel(m2.status)}</span>
            </div>
          </div>
        </Link>
      </div>
    </section>
  );
}
