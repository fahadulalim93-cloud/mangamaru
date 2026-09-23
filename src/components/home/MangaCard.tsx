"use client";
import Link from "next/link";
import { Manga, getScoreColor, getStatusLabel } from "@/lib/anilist";

interface MangaCardProps {
  manga: Manga;
  progress?: number;
  unreadCount?: number;
  variant?: "default" | "hero";
}

// v9.9.2 — restore color-aware card design (glow + title overlay on image)
// but with SIMPLE hover: just title turns red + small lift. No spotlight, no 3D tilt.
export function MangaCard({ manga, progress, unreadCount, variant = "default" }: MangaCardProps) {
  const title = manga.title.english || manga.title.romaji;
  const cardColor = manga.coverImage?.color || "#dc2626";

  return (
    <Link
      href={`/manga/${manga.id}`}
      className="dense-card"
      style={{ ["--card-color" as string]: cardColor }}
    >
      <div className="dense-card-cover">
        <img
          src={manga.coverImage?.extraLarge || manga.coverImage?.large}
          alt={title}
          loading="lazy"
        />
        <div className="dense-card-overlay"></div>
        <div className="dense-card-accent"></div>
        <div className="dense-card-glow"></div>

        {manga.status && manga.status === "RELEASING" && (
          <div className="dense-card-status">{getStatusLabel(manga.status)}</div>
        )}
        {manga.averageScore && (
          <div className="dense-card-score" style={{ color: getScoreColor(manga.averageScore) }}>
            <span className="star">★</span>
            <span>{(manga.averageScore / 10).toFixed(1)}</span>
          </div>
        )}
        {unreadCount && unreadCount > 0 && (
          <div className="dense-card-unread">+{unreadCount}</div>
        )}

        {/* Title overlay at bottom of image (MangaYouKnow style — KEPT) */}
        <div className="dense-card-title-overlay">
          <div className="dense-card-title">{title}</div>
          <div className="dense-card-meta">
            {manga.format || "Manga"}{manga.chapters ? ` · ${manga.chapters} ch` : ""}
          </div>
        </div>

        {progress != null && progress > 0 && (
          <div className="dense-card-progress">
            <div className="dense-card-progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
        )}
      </div>
    </Link>
  );
}
