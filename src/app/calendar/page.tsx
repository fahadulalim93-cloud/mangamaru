import { TopBar } from "@/components/layout/TopBar";
import { anilist } from "@/lib/anilist";

export const revalidate = 1800;

interface AiringSchedule {
  id: number;
  media: { id: number; title: { romaji: string; english: string | null }; coverImage: { large: string; extraLarge: string; color: string | null }; format: string; averageScore: number | null; genres: string[] };
  airingAt: number;
  episode: number;
}

async function fetchAiringManga(): Promise<AiringSchedule[]> {
  const query = `query {
    Page(page:1,perPage:50) {
      media(type:MANGA, sort:START_DATE_DESC, isAdult:false, startDate_greater:20250101) {
        id
        title { romaji english }
        coverImage { large extraLarge color }
        format
        averageScore
        genres
        startDate { year month day }
        status
      }
    }
  }`;
  const data = await anilist<{ Page: { media: any[] } }>(query, {});
  return data.Page.media
    .filter((m) => m.startDate?.year && m.startDate?.month)
    .map((m) => ({
      id: m.id,
      media: { id: m.id, title: m.title, coverImage: m.coverImage, format: m.format, averageScore: m.averageScore, genres: m.genres },
      airingAt: new Date(m.startDate.year, m.startDate.month - 1, m.startDate.day || 1).getTime() / 1000,
      episode: 1,
    }))
    .slice(0, 50);
}

function getMonthDays(year: number, month: number) { return new Date(year, month + 1, 0).getDate(); }

export default async function CalendarPage() {
  let releases: AiringSchedule[] = [];
  try { releases = await fetchAiringManga(); } catch (e) { console.error(e); }

  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth();
  const byDay: Record<number, AiringSchedule[]> = {};
  releases.forEach((r) => {
    const d = new Date(r.airingAt * 1000);
    if (d.getFullYear() === currentYear && d.getMonth() === currentMonth) {
      const day = d.getDate();
      if (!byDay[day]) byDay[day] = [];
      byDay[day].push(r);
    }
  });
  const daysInMonth = getMonthDays(currentYear, currentMonth);
  const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();
  const monthName = now.toLocaleString("en-US", { month: "long" });
  const upcoming = releases.filter((r) => r.airingAt * 1000 >= now.getTime()).sort((a, b) => a.airingAt - b.airingAt).slice(0, 10);

  return (
    <>
      <TopBar />
      <div className="cal-page">
        <div className="lib-header">
          <h1 className="page-title">Release Calendar</h1>
          <p className="page-subtitle">{monthName} {currentYear} · {releases.length} releases tracked</p>
        </div>

        <div className="cal-layout">
          <div className="cal-grid">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
              <div key={d} className="cal-weekday">{d}</div>
            ))}
            {Array.from({ length: firstDayOfMonth }).map((_, i) => <div key={`empty-${i}`} className="cal-day empty"></div>)}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const isToday = day === now.getDate();
              const items = byDay[day] || [];
              return (
                <div key={day} className={`cal-day ${isToday ? "today" : ""} ${items.length > 0 ? "has-releases" : ""}`}>
                  <div className="day-number">{day}</div>
                  {items.slice(0, 3).map((r) => (
                    <a key={r.id} href={`/manga/${r.media.id}`} className="day-release" title={r.media.title.english || r.media.title.romaji}>
                      <img src={r.media.coverImage?.large} alt="" className="day-release-cover" loading="lazy" />
                    </a>
                  ))}
                  {items.length > 3 && <div className="day-more">+{items.length - 3}</div>}
                </div>
              );
            })}
          </div>

          <div className="upcoming-sidebar">
            <h2 className="sidebar-title">Coming Up</h2>
            {upcoming.length === 0 ? <p className="empty-text">No upcoming releases in our tracker.</p> : (
              <div className="upcoming-list">
                {upcoming.map((r) => {
                  const d = new Date(r.airingAt * 1000);
                  return (
                    <a key={r.id} href={`/manga/${r.media.id}`} className="upcoming-item">
                      <img src={r.media.coverImage?.large} alt="" className="upcoming-cover" loading="lazy" />
                      <div className="upcoming-info">
                        <div className="upcoming-title">{r.media.title.english || r.media.title.romaji}</div>
                        <div className="upcoming-date">{d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}</div>
                      </div>
                    </a>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
