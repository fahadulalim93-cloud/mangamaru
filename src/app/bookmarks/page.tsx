"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { TopBar } from "@/components/layout/TopBar";

interface Bookmark { id: number; title: string; cover: string; chapter: string; page: number; addedAt: string; }

export default function BookmarksPage() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  useEffect(() => {
    try {
      const raw = localStorage.getItem("mangamaru:bookmarks");
      if (raw) setBookmarks(JSON.parse(raw));
    } catch {}
  }, []);

  return (
    <>
      <TopBar />
      <div className="lib-page">
        <div className="lib-header">
          <h1 className="page-title">Bookmarks</h1>
          <p className="page-subtitle">{bookmarks.length > 0 ? `${bookmarks.length} bookmarked pages` : "Save your favorite pages while reading — they'll show up here."}</p>
        </div>
        {bookmarks.length === 0 ? (
          <div className="library-empty">
            <div className="empty-icon">🔖</div>
            <h2>No bookmarks yet</h2>
            <p>While reading, click the bookmark icon on any page to save it here.</p>
            <Link href="/" className="btn-primary" style={{ marginTop: 20, display: "inline-flex" }}><span>Find manga to read</span></Link>
          </div>
        ) : (
          <div className="omni-grid">
            {bookmarks.map((b) => (
              <Link key={`${b.id}-${b.chapter}-${b.page}`} href={`/read/${b.id}/${b.chapter}`} className="dense-card">
                <div className="dense-card-cover">
                  <img src={b.cover} alt={b.title} className="dense-card-cover img" loading="lazy" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  <div className="dense-card-overlay"></div>
                  <div className="dense-card-title-overlay">
                    <div className="dense-card-title">{b.title}</div>
                    <div className="dense-card-meta">Ch {b.chapter} · P{b.page}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
