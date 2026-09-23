"use client";
import { use } from "react";
import MangaReader from "@/components/manga/manga-reader";

export default function ReadPage({ params }: { params: Promise<{ id: string; chapter: string }> }) {
  const { id, chapter } = use(params);
  return <MangaReader mangaId={id} chapterId={chapter} />;
}
