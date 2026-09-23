"use client";
import Link from "next/link";

interface IconRailProps {
  onNavigate?: (id: string) => void;
  activeSection?: string;
}

// Akari-inspired: 64px wide icon-only left rail (no text labels)
export function IconRail({ onNavigate, activeSection = "home" }: IconRailProps) {
  const items = [
    { id: "home", icon: "🏠", label: "Home", href: "/" },
    { id: "trending", icon: "🔥", label: "Trending", action: "trending" },
    { id: "popular", icon: "⭐", label: "Popular", action: "popular" },
    { id: "new", icon: "✨", label: "Fresh", action: "new" },
    { id: "top", icon: "🏆", label: "Top Rated", action: "top" },
  ];

  const bottomItems = [
    { id: "library", icon: "📚", label: "Library", href: "/library" },
    { id: "calendar", icon: "📅", label: "Calendar", href: "/calendar" },
    { id: "bookmarks", icon: "🔖", label: "Bookmarks", href: "/bookmarks" },
    { id: "settings", icon: "⚙️", label: "Settings", href: "/settings" },
  ];

  return (
    <aside className="icon-rail">
      <div className="rail-top">
        <Link href="/" className="rail-logo" aria-label="MangaMaru home">
          <svg viewBox="0 0 32 32" fill="none" style={{ width: 22, height: 22 }}>
            <path d="M6 6h6c4 0 6 2 6 5s-2 5-6 5H10v8H6V6z" fill="#ffffff" />
            <circle cx="24" cy="22" r="4" fill="#ffffff" opacity="0.7" />
          </svg>
        </Link>
      </div>

      <nav className="rail-nav">
        {items.map((item) =>
          item.href ? (
            <Link
              key={item.id}
              href={item.href}
              className={`rail-item ${activeSection === item.id ? "active" : ""}`}
              title={item.label}
            >
              <span className="rail-icon">{item.icon}</span>
            </Link>
          ) : (
            <button
              key={item.id}
              className={`rail-item ${activeSection === item.id ? "active" : ""}`}
              onClick={() => onNavigate?.(item.action || item.id)}
              title={item.label}
              aria-label={item.label}
            >
              <span className="rail-icon">{item.icon}</span>
            </button>
          )
        )}
      </nav>

      <div className="rail-bottom">
        {bottomItems.map((item) => (
          <Link
            key={item.id}
            href={item.href}
            className="rail-item"
            title={item.label}
            aria-label={item.label}
          >
            <span className="rail-icon">{item.icon}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}
