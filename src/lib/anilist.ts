// AniList GraphQL client + types

export interface MangaTitle {
  romaji: string;
  english: string | null;
}

export interface MangaCover {
  large: string;
  extraLarge: string;
  color: string | null;
}

export interface Manga {
  id: number;
  title: MangaTitle;
  coverImage: MangaCover;
  bannerImage: string | null;
  averageScore: number | null;
  meanScore: number | null;
  popularity: number | null;
  favourites?: number | null;
  genres: string[];
  format: string;
  chapters: number | null;
  volumes: number | null;
  status: string;
  description: string | null;
  startDate: { year: number | null; month: number | null; day: number | null } | null;
  endDate: { year: number | null; month: number | null; day: number | null } | null;
  season: string | null;
  seasonYear: number | null;
  countryOfOrigin?: string;
  source?: string;
  externalLinks?: any[];
  characters?: { edges: { node: { id: number; name: { full: string }; image: { large: string } }; role: string }[] };
  staff?: { edges: { node: { id: number; name: { full: string }; image: { large: string | null } }; role: string }[] };
  recommendations?: { nodes: any[] };
}

const ANILIST_API = "https://graphql.anilist.co";

export async function anilist<T = any>(query: string, variables: Record<string, unknown> = {}): Promise<T> {
  const r = await fetch(ANILIST_API, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({ query, variables }),
    next: { revalidate: 1800 },
  });
  if (r.status === 429) {
    await new Promise((res) => setTimeout(res, 1800));
    return anilist<T>(query, variables);
  }
  if (!r.ok) throw new Error(`AniList ${r.status}: ${await r.text()}`);
  const json = await r.json();
  if (json.errors) throw new Error(`AniList GraphQL: ${JSON.stringify(json.errors)}`);
  return json.data as T;
}

const MANGA_FIELDS = `
  id
  title { romaji english }
  coverImage { large extraLarge color }
  bannerImage
  averageScore
  meanScore
  popularity
  favourites
  genres
  format
  chapters
  volumes
  status
  description(asHtml: false)
  startDate { year month day }
  endDate { year month day }
  season
  seasonYear
  countryOfOrigin
  source
  externalLinks { url icon site type }
`;

export async function fetchSection(sort: string, genre: string | null = null, perPage = 12): Promise<Manga[]> {
  const query = `query($page:Int,$perPage:Int,$sort:[MediaSort],$genre:String){
    Page(page:$page,perPage:$perPage){
      media(type:MANGA,sort:$sort,genre:$genre){
        ${MANGA_FIELDS}
      }
    }
  }`;
  const data = await anilist<{ Page: { media: Manga[] } }>(query, {
    page: 1,
    perPage,
    sort: [sort],
    genre,
  });
  return data.Page.media.filter((m) => m.coverImage?.large);
}

export async function fetchMangaById(id: number): Promise<Manga | null> {
  const query = `query($id:Int){
    Media(id:$id,type:MANGA){
      ${MANGA_FIELDS}
      characters(sort:ROLE,role:MAIN){
        edges { node { id name { full } image { large } } role }
      }
      staff(sort:RELEVANCE){
        edges { node { id name { full } image { large } } role }
      }
      recommendations(sort:RATING_DESC,perPage:8){
        nodes {
          id
          mediaRecommendation {
            id
            title { romaji english }
            coverImage { large extraLarge color }
            averageScore
          }
        }
      }
    }
  }`;
  const data = await anilist<{ Media: Manga }>(query, { id });
  return data.Media;
}

export async function searchManga(search: string, perPage = 8): Promise<Manga[]> {
  const query = `query($search:String,$perPage:Int){
    Page(page:1,perPage:$perPage){
      media(type:MANGA,search:$search,sort:POPULARITY_DESC){
        ${MANGA_FIELDS}
      }
    }
  }`;
  const data = await anilist<{ Page: { media: Manga[] } }>(query, { search, perPage });
  return data.Page.media.filter((m) => m.coverImage?.large);
}

export interface SectionConfig {
  id: string;
  title: string;
  icon: string;
  sort: string;
  genre?: string;
  perPage: number;
  layout: "grid" | "row";
  badge?: "year" | "rank";
}

export const SECTIONS: SectionConfig[] = [
  { id: "trending", title: "Trending Now", icon: "", sort: "TRENDING_DESC", perPage: 10, layout: "row", badge: "rank" },
  { id: "popular", title: "Popular Manga", icon: "", sort: "POPULARITY_DESC", perPage: 18, layout: "grid" },
  { id: "top", title: "Top Rated of All Time", icon: "", sort: "SCORE_DESC", perPage: 18, layout: "grid" },
  { id: "new", title: "Fresh Releases", icon: "", sort: "START_DATE_DESC", perPage: 18, layout: "grid" },
  { id: "action", title: "Action", icon: "", sort: "POPULARITY_DESC", genre: "Action", perPage: 12, layout: "row" },
  { id: "adventure", title: "Adventure", icon: "", sort: "POPULARITY_DESC", genre: "Adventure", perPage: 12, layout: "row" },
  { id: "comedy", title: "Comedy", icon: "", sort: "POPULARITY_DESC", genre: "Comedy", perPage: 12, layout: "row" },
  { id: "drama", title: "Drama", icon: "", sort: "POPULARITY_DESC", genre: "Drama", perPage: 12, layout: "row" },
  { id: "fantasy", title: "Fantasy", icon: "", sort: "POPULARITY_DESC", genre: "Fantasy", perPage: 12, layout: "row" },
  { id: "horror", title: "Horror", icon: "", sort: "POPULARITY_DESC", genre: "Horror", perPage: 12, layout: "row" },
  { id: "mystery", title: "Mystery", icon: "", sort: "POPULARITY_DESC", genre: "Mystery", perPage: 12, layout: "row" },
  { id: "romance", title: "Romance", icon: "", sort: "POPULARITY_DESC", genre: "Romance", perPage: 12, layout: "row" },
  { id: "scifi", title: "Sci-Fi", icon: "", sort: "POPULARITY_DESC", genre: "Sci-Fi", perPage: 12, layout: "row" },
  { id: "sol", title: "Slice of Life", icon: "", sort: "POPULARITY_DESC", genre: "Slice of Life", perPage: 12, layout: "row" },
  { id: "sports", title: "Sports", icon: "", sort: "POPULARITY_DESC", genre: "Sports", perPage: 12, layout: "row" },
  { id: "super", title: "Supernatural", icon: "", sort: "POPULARITY_DESC", genre: "Supernatural", perPage: 12, layout: "row" },
  { id: "psych", title: "Psychological", icon: "", sort: "POPULARITY_DESC", genre: "Psychological", perPage: 12, layout: "row" },
  { id: "thriller", title: "Thriller", icon: "", sort: "POPULARITY_DESC", genre: "Thriller", perPage: 12, layout: "row" },
];

export function getScoreColor(score: number | null): string {
  if (!score) return "#666";
  const s = score / 10;
  if (s >= 8.5) return "#dc2626";  // bright red for top scores
  if (s >= 7) return "#f87171";    // light red for good scores
  if (s >= 5) return "#888888";    // gray for mediocre
  return "#555555";                // dark gray for bad
}

export function getStatusLabel(status: string | undefined): string {
  if (!status) return "";
  if (status === "RELEASING") return "Ongoing";
  if (status === "FINISHED") return "Done";
  if (status === "HIATUS") return "Hiatus";
  if (status === "CANCELLED") return "Cancelled";
  return status;
}

export function truncate(text: string, len: number): string {
  if (!text) return "";
  const clean = text.replace(/<[^>]*>/g, "").replace(/&[^;]+;/g, " ").replace(/\s+/g, " ").trim();
  return clean.length > len ? clean.slice(0, len).trim() + "…" : clean;
}

// Mood presets — each mood has a genre to query + a tint color for the page
export interface Mood {
  id: string;
  label: string;
  emoji: string;
  color: string;
  genre: string | null;
  description: string;
}

export const MOODS: Mood[] = [
  { id: "all", label: "Discover", emoji: "✦", color: "#ffffff", genre: null, description: "Popular right now" },
  { id: "cozy", label: "Cozy", emoji: "☕", color: "#fbbf24", genre: "Slice of Life", description: "Slice of Life · gentle reads" },
  { id: "action", label: "Action", emoji: "⚔", color: "#ef4444", genre: "Action", description: "Pulse-pounding battles" },
  { id: "dark", label: "Dark", emoji: "◉", color: "#a855f7", genre: "Psychological", description: "Mind-bending, intense" },
  { id: "romance", label: "Romance", emoji: "♡", color: "#f472b6", genre: "Romance", description: "Love stories" },
  { id: "mystery", label: "Mystery", emoji: "?", color: "#3b82f6", genre: "Mystery", description: "Whodunits & enigmas" },
  { id: "isekai", label: "Isekai", emoji: "✧", color: "#22c55e", genre: "Fantasy", description: "Other worlds await" },
];

// Get random manga ID for "Surprise me" feature
export async function fetchRandomMangaId(): Promise<number> {
  const data = await fetchSection("POPULARITY_DESC", null, 50);
  if (data.length === 0) throw new Error("No manga available");
  return data[Math.floor(Math.random() * data.length)].id;
}
