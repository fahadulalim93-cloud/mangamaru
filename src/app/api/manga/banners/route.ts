import { NextRequest, NextResponse } from "next/server";
import { anilist } from "@/lib/anilist";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const FIELDS = `
  id
  title { romaji english }
  coverImage { large extraLarge color }
  bannerImage
  characters(sort:ROLE, role:MAIN, perPage:6) {
    edges { node { id name { full } image { large } } role }
  }
  recommendations(sort:RATING_DESC, perPage:6) {
    nodes {
      id
      mediaRecommendation {
        id
        title { romaji english }
        coverImage { large extraLarge color }
        averageScore
        status
      }
    }
  }
  relations {
    edges {
      relationType(version:2)
      node {
        id
        title { romaji english }
        coverImage { large }
        type
        format
        status
      }
    }
  }
`;

export async function GET(request: NextRequest) {
  const idsParam = request.nextUrl.searchParams.get("ids");
  if (!idsParam) return NextResponse.json({ banners: {} });

  const ids = idsParam.split(",").map(s => parseInt(s.trim(), 10)).filter(n => Number.isFinite(n));
  if (ids.length === 0) return NextResponse.json({ banners: {} });

  const query = `query($ids:[Int]) {
    Page(page:1, perPage:50) {
      media(id_in:$ids, type:MANGA) {
        ${FIELDS}
      }
    }
  }`;

  try {
    const data = await anilist<{ Page: { media: any[] } }>(query, { ids });
    const banners: Record<number, any> = {};

    for (const m of data.Page.media) {
      const recs = (m.recommendations?.nodes || [])
        .map((n: any) => n.mediaRecommendation)
        .filter(Boolean)
        .slice(0, 6);

      banners[m.id] = {
        banner: m.bannerImage || m.coverImage?.extraLarge || m.coverImage?.large || "",
        cover: m.coverImage?.extraLarge || m.coverImage?.large || "",
        relations: (m.relations?.edges || []).map((e: any) => ({
          relationType: e.relationType,
          id: e.node.id,
          title: e.node.title?.english || e.node.title?.romaji || "",
          cover: e.node.coverImage?.large || "",
          type: e.node.type,
          format: e.node.format,
          status: e.node.status,
        })),
        characters: (m.characters?.edges || []).map((e: any) => ({
          role: e.role,
          id: e.node.id,
          name: e.node.name?.full || "",
          image: e.node.image?.large || "",
        })),
        recommendations: recs.map((r: any) => ({
          id: r.id,
          title: r.title?.english || r.title?.romaji || "",
          cover: r.coverImage?.extraLarge || r.coverImage?.large || "",
          status: r.status,
          score: r.averageScore,
        })),
      };
    }

    return NextResponse.json({ banners });
  } catch (e) {
    console.error("[manga/banners] Error:", e);
    return NextResponse.json({ banners: {} });
  }
}
