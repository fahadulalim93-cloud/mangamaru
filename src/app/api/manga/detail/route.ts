import { NextRequest, NextResponse } from "next/server";
import { getMangaDetail } from "@/lib/manga-api";
import { rewriteMangaImageUrl } from "@/lib/cdn/manga-rewrite";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 });

  try {
    const result = await getMangaDetail(id);
    if (!result) return NextResponse.json({ error: "Not found" }, { status: 404 });
    
    // Rewrite poster/cover URLs
    const r = result as any;
    if (r.poster) r.poster = rewriteMangaImageUrl(r.poster);
    if (r.cover) r.cover = rewriteMangaImageUrl(r.cover);
    
    return NextResponse.json(r);
  } catch {
    return NextResponse.json({ error: "Failed" }, { status: 500 });
  }
}
