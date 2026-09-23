import { fetchMangaById, truncate, getScoreColor, getStatusLabel, Manga } from "@/lib/anilist";
import { TopBar } from "@/components/layout/TopBar";
import { notFound } from "next/navigation";
import Link from "next/link";

export const revalidate = 1800;
export const dynamic = "force-dynamic";

export default async function MangaDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const anilistId = parseInt(id, 10);
  if (!Number.isFinite(anilistId)) notFound();

  let manga: Manga | null = null;
  try {
    manga = await fetchMangaById(anilistId);
  } catch (e) {
    console.error("Failed to fetch manga", e);
    notFound();
  }
  if (!manga) notFound();

  const title = manga.title.english || manga.title.romaji;
  const coverUrl = manga.coverImage?.extraLarge || manga.coverImage?.large;
  const bannerUrl = manga.bannerImage || coverUrl;
  const externalLinks = (manga.externalLinks || []).filter((l: any) => l.type === "READING" || !l.type || l.type === "INFO");
  const mainChars = (manga.characters?.edges || []).slice(0, 8);
  const staffEdges = (manga.staff?.edges || []).slice(0, 6);
  // Extract the actual recommended manga from the nested structure
  const recs = (manga.recommendations?.nodes || [])
    .map((n: any) => n.mediaRecommendation)
    .filter(Boolean)
    .slice(0, 6);

  const startDateStr = manga.startDate?.year
    ? `${manga.startDate.year}${manga.startDate.month ? `-${String(manga.startDate.month).padStart(2, "0")}` : ""}${manga.startDate.day ? `-${String(manga.startDate.day).padStart(2, "0")}` : ""}`
    : "—";
  const endDateStr = manga.endDate?.year
    ? `${manga.endDate.year}${manga.endDate.month ? `-${String(manga.endDate.month).padStart(2, "0")}` : ""}${manga.endDate.day ? `-${String(manga.endDate.day).padStart(2, "0")}` : ""}`
    : manga.status === "RELEASING" ? "Ongoing" : "—";

  return (
    <>
      <TopBar />
      <div className="manga-detail">
        {/* BANNER — cover image as backdrop, blurred, darkened */}
        <div className="detail-banner">
          <img src={bannerUrl} alt="" className="banner-img" />
          <div className="banner-overlay"></div>
          <div className="banner-gradient"></div>
        </div>

        <div className="detail-content">
          {/* HERO ROW: cover + main info */}
          <div className="detail-hero">
            <div className="detail-cover-wrap">
              <div className="detail-cover-shadow"></div>
              <img src={coverUrl} alt={title} className="detail-cover" />
              {manga.averageScore && (
                <div className="detail-cover-score" style={{ color: getScoreColor(manga.averageScore) }}>
                  <span className="star">★</span>
                  <span className="score-val">{(manga.averageScore / 10).toFixed(1)}</span>
                </div>
              )}
            </div>

            <div className="detail-info">
              <div className="detail-tagline">
                {manga.format || "Manga"}{manga.countryOfOrigin ? ` · ${manga.countryOfOrigin}` : ""}
              </div>
              <h1 className="detail-title">{title}</h1>
              {manga.title.english && manga.title.romaji && manga.title.english !== manga.title.romaji && (
                <div className="detail-romaji">{manga.title.romaji}</div>
              )}

              {/* Genre pills */}
              {manga.genres.length > 0 && (
                <div className="detail-genres">
                  {manga.genres.map((g) => (
                    <span key={g} className="detail-genre-pill">{g}</span>
                  ))}
                </div>
              )}

              {/* Stats row */}
              <div className="detail-stats-row">
                {manga.averageScore != null && (
                  <div className="detail-stat">
                    <div className="stat-label">Score</div>
                    <div className="stat-value" style={{ color: getScoreColor(manga.averageScore) }}>
                      {(manga.averageScore / 10).toFixed(1)}
                      <span className="stat-out">/10</span>
                    </div>
                  </div>
                )}
                {manga.popularity != null && (
                  <div className="detail-stat">
                    <div className="stat-label">Popularity</div>
                    <div className="stat-value">{manga.popularity.toLocaleString()}</div>
                  </div>
                )}
                {manga.favourites != null && (
                  <div className="detail-stat">
                    <div className="stat-label">Favorites</div>
                    <div className="stat-value">{manga.favourites.toLocaleString()}</div>
                  </div>
                )}
                {manga.chapters != null && (
                  <div className="detail-stat">
                    <div className="stat-label">Chapters</div>
                    <div className="stat-value">{manga.chapters}</div>
                  </div>
                )}
                {manga.volumes != null && (
                  <div className="detail-stat">
                    <div className="stat-label">Volumes</div>
                    <div className="stat-value">{manga.volumes}</div>
                  </div>
                )}
                {manga.status && (
                  <div className="detail-stat">
                    <div className="stat-label">Status</div>
                    <div className="stat-value">
                      <span className={`status-dot ${manga.status === "RELEASING" ? "ongoing" : "done"}`}></span>
                      {getStatusLabel(manga.status)}
                    </div>
                  </div>
                )}
              </div>

              {/* CTA buttons */}
              <div className="detail-actions">
                <Link href={`/read/${manga.id}/1`} className="btn-primary detail-cta">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 18, height: 18 }}>
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                  </svg>
                  <span>Start Reading</span>
                </Link>
                <button className="btn-secondary detail-cta" type="button">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 18, height: 18 }}>
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                  </svg>
                  <span>Bookmark</span>
                </button>
                <button className="btn-secondary detail-cta" type="button">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 18, height: 18 }}>
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                  <span>Add to Library</span>
                </button>
                <a
                  href={`https://anilist.co/manga/${manga.id}`}
                  target="_blank"
                  rel="noopener"
                  className="btn-secondary detail-cta"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ width: 18, height: 18 }}>
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3" />
                  </svg>
                  <span>AniList</span>
                </a>
              </div>
            </div>
          </div>

          <div className="detail-body">
            {/* Two-column: left main content, right info sidebar */}
            <div className="detail-main-col">
              {/* SYNOPSIS */}
              <section className="detail-section">
                <h2 className="detail-section-title">Synopsis</h2>
                <p className="detail-synopsis">{truncate(manga.description || "No description available.", 1200)}</p>
              </section>

              {/* CHARACTERS */}
              {mainChars.length > 0 && (
                <section className="detail-section">
                  <h2 className="detail-section-title">Characters</h2>
                  <div className="char-grid">
                    {mainChars.map((c) => (
                      <div key={c.node.id} className="char-card">
                        <img src={c.node.image?.large} alt={c.node.name.full} className="char-img" loading="lazy" />
                        <div className="char-info">
                          <div className="char-name">{c.node.name.full}</div>
                          <div className="char-role">{c.role}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* STAFF */}
              {staffEdges.length > 0 && (
                <section className="detail-section">
                  <h2 className="detail-section-title">Staff</h2>
                  <div className="char-grid">
                    {staffEdges.map((s) => (
                      <div key={s.node.id} className="char-card">
                        {s.node.image?.large ? (
                          <img src={s.node.image.large} alt={s.node.name.full} className="char-img" loading="lazy" />
                        ) : (
                          <div className="char-img staff-img-empty"></div>
                        )}
                        <div className="char-info">
                          <div className="char-name">{s.node.name.full}</div>
                          <div className="char-role">{s.role}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* RECOMMENDATIONS — using actual cards now */}
              {recs.length > 0 && (
                <section className="detail-section">
                  <h2 className="detail-section-title">If you like this, try…</h2>
                  <div className="omni-grid">
                    {recs.map((r: any) => {
                      const recTitle = r.title?.english || r.title?.romaji || "Unknown";
                      return (
                        <Link key={r.id} href={`/manga/${r.id}`} className="dense-card" style={{ ["--card-color" as string]: r.coverImage?.color || "#dc2626" }}>
                          <div className="dense-card-cover">
                            <img src={r.coverImage?.extraLarge || r.coverImage?.large} alt={recTitle} loading="lazy" />
                            <div className="dense-card-overlay"></div>
                            <div className="dense-card-accent"></div>
                            <div className="dense-card-glow"></div>
                            {r.averageScore && (
                              <div className="dense-card-score" style={{ color: getScoreColor(r.averageScore) }}>
                                <span className="star">★</span>
                                <span>{(r.averageScore / 10).toFixed(1)}</span>
                              </div>
                            )}
                            <div className="dense-card-title-overlay">
                              <div className="dense-card-title">{recTitle}</div>
                            </div>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                </section>
              )}
            </div>

            {/* INFO SIDEBAR — right column with metadata table */}
            <aside className="detail-sidebar">
              <div className="info-card">
                <h3 className="info-card-title">Information</h3>
                <div className="info-row">
                  <span className="info-label">Format</span>
                  <span className="info-value">{manga.format || "Manga"}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Status</span>
                  <span className="info-value">
                    <span className={`status-dot ${manga.status === "RELEASING" ? "ongoing" : "done"}`}></span>
                    {getStatusLabel(manga.status)}
                  </span>
                </div>
                {manga.chapters != null && (
                  <div className="info-row">
                    <span className="info-label">Chapters</span>
                    <span className="info-value">{manga.chapters}</span>
                  </div>
                )}
                {manga.volumes != null && (
                  <div className="info-row">
                    <span className="info-label">Volumes</span>
                    <span className="info-value">{manga.volumes}</span>
                  </div>
                )}
                <div className="info-row">
                  <span className="info-label">Started</span>
                  <span className="info-value">{startDateStr}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Ended</span>
                  <span className="info-value">{endDateStr}</span>
                </div>
                {manga.seasonYear && (
                  <div className="info-row">
                    <span className="info-label">Season</span>
                    <span className="info-value">{manga.season ? `${manga.season} ` : ""}{manga.seasonYear}</span>
                  </div>
                )}
                {manga.countryOfOrigin && (
                  <div className="info-row">
                    <span className="info-label">Country</span>
                    <span className="info-value">{manga.countryOfOrigin}</span>
                  </div>
                )}
                {manga.source && (
                  <div className="info-row">
                    <span className="info-label">Source</span>
                    <span className="info-value">{manga.source}</span>
                  </div>
                )}
              </div>

              {/* Genres block */}
              {manga.genres.length > 0 && (
                <div className="info-card">
                  <h3 className="info-card-title">Genres</h3>
                  <div className="info-tags">
                    {manga.genres.map((g) => (
                      <span key={g} className="info-tag">{g}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* External links */}
              {externalLinks.length > 0 && (
                <div className="info-card">
                  <h3 className="info-card-title">Read on</h3>
                  <div className="info-links">
                    {externalLinks.map((link: any) => (
                      <a key={link.url} href={link.url} target="_blank" rel="noopener" className="info-link">
                        {link.icon && <img src={link.icon} alt="" className="info-link-icon" />}
                        <span>{link.site}</span>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 14, height: 14 }}>
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3" />
                        </svg>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </aside>
          </div>
        </div>
      </div>
    </>
  );
}
