"use client";
import { useState, useEffect, use } from "react";
import Link from "next/link";
import MangaDetailPage from "@/components/manga/manga-detail";
import { fetchMangaById, Manga } from "@/lib/anilist";

export default function MangaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [providerId, setProviderId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        if (id.includes(":")) {
          setProviderId(id);
          setLoading(false);
          return;
        }

        const anilistId = parseInt(id, 10);
        if (Number.isFinite(anilistId)) {
          // Fetch AniList data for high-quality banner + cover
          const manga = await fetchMangaById(anilistId);
          if (manga) {
            const title = manga.title.english || manga.title.romaji;
            const anilistCover = manga.coverImage?.extraLarge || manga.coverImage?.large || "";
            const anilistBanner = manga.bannerImage || anilistCover;

            // Search scrape API by title to find provider ID (for chapters + reading)
            const searchRes = await fetch(`/api/manga/search?q=${encodeURIComponent(title)}`);
            let foundProviderId: string | null = null;
            if (searchRes.ok) {
              const searchData = await searchRes.json();
              const firstResult = searchData?.results?.[0];
              if (firstResult?.id) {
                foundProviderId = firstResult.id;
                // Pre-set sessionStorage with AniList images so the detail component
                // uses them as fallback/enrichment (component reads manga-poster-{id})
                try {
                  sessionStorage.setItem(`manga-poster-${foundProviderId}`, anilistCover);
                } catch {}
              }
            }

            // Store AniList data for the banners enrichment route
            // The component fetches /api/manga/banners?ids={anilistId}
            // We need to set the anilistId on the manga object the component will fetch
            try {
              sessionStorage.setItem(`manga-anilist-id-${foundProviderId || id}`, String(anilistId));
              sessionStorage.setItem(`manga-anilist-banner-${foundProviderId || id}`, anilistBanner);
              sessionStorage.setItem(`manga-anilist-cover-${foundProviderId || id}`, anilistCover);
            } catch {}

            setProviderId(foundProviderId || `atsumaru:${id}`);
            setLoading(false);
            return;
          }
        }
        setProviderId(`atsumaru:${id}`);
      } catch (e: any) {
        setError(e?.message || "Failed to load manga");
      }
      setLoading(false);
    })();
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <div style={{ textAlign: "center" }}>
          <div className="skeleton" style={{ width: 200, height: 280, borderRadius: 12, margin: "0 auto 20px" }} />
          <p style={{ color: "#888", fontSize: 14 }}>Loading manga…</p>
        </div>
      </div>
    );
  }

  if (error && !providerId) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", flexDirection: "column", gap: 12 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Failed to load</h1>
        <p style={{ color: "#888" }}>{error}</p>
        <Link href="/" style={{ color: "#dc2626", marginTop: 12 }}>← Back to home</Link>
      </div>
    );
  }

  return <MangaDetailPage mangaId={providerId || `atsumaru:${id}`} />;
}
