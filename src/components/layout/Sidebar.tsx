"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Bookmark,
  TrendingUp,
  Search,
  Settings,
  Users,
  BookType,
  Theater,
  Mountain,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: number;
  shortcut?: string;
}

interface GenreCategory {
  name: string;
  icon: LucideIcon;
  genres: string[];
}

const TOP_NAV: NavItem[] = [
  { label: "Home", href: "/", icon: Home },
  { label: "Bookmarks", href: "/bookmarks", icon: Bookmark, shortcut: "⌘⇧B" },
  { label: "Popular", href: "/#popular", icon: TrendingUp },
  { label: "Search", href: "/#search", icon: Search, shortcut: "⌘K" },
];

const GENRE_CATEGORIES: GenreCategory[] = [
  {
    name: "Demographics",
    icon: Users,
    genres: ["Shounen", "Shoujo", "Seinen", "Josei"],
  },
  {
    name: "Format",
    icon: BookType,
    genres: ["Manga", "Novel", "One Shot", "Doujinshi"],
  },
  {
    name: "Genres",
    icon: Theater,
    genres: [
      "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror",
      "Mystery", "Romance", "Sci-Fi", "Slice of Life", "Sports",
      "Supernatural", "Psychological", "Thriller",
    ],
  },
  {
    name: "Themes",
    icon: Mountain,
    genres: ["Isekai", "Mecha", "School", "Military", "Historical", "Harem"],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({
    Genres: true,
    Themes: false,
    Demographics: false,
    Format: false,
  });

  const toggleCat = (cat: string) => {
    if (collapsed) return; // can't expand when collapsed
    setExpandedCats((s) => ({ ...s, [cat]: !s[cat] }));
  };

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    if (href.startsWith("/#")) return false;
    return pathname === href || pathname.startsWith(href + "/");
  };

  const isGenreActive = (genre: string) => {
    return pathname === `/genre/${genre.toLowerCase().replace(/\s+/g, "-")}`;
  };

  return (
    <aside className={`akari-sidebar ${collapsed ? "collapsed" : "expanded"}`}>
      {/* Top: Logo + collapse toggle */}
      <div className="akari-sidebar-top">
        <Link href="/" className="akari-logo" aria-label="MangaMaru home">
          <img src="/logo-small.png" alt="MangaMaru" className="akari-logo-img" />
        </Link>
        <button
          className="akari-sidebar-toggle"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand (⌘B)" : "Collapse (⌘B)"}
        >
          <ChevronRight
            size={16}
            className={`akari-toggle-icon ${collapsed ? "rotated" : ""}`}
          />
        </button>
      </div>

      {/* Main nav */}
      <nav className="akari-sidebar-nav">
        {TOP_NAV.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.href);
          return (
            <Link
              key={item.label}
              href={item.href}
              className={`akari-nav-item ${active ? "active" : ""}`}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} className="akari-nav-icon" />
              {!collapsed && (
                <>
                  <span className="akari-nav-label">{item.label}</span>
                  {item.shortcut && (
                    <kbd className="akari-shortcut">{item.shortcut}</kbd>
                  )}
                  {item.badge && item.badge > 0 && (
                    <span className="akari-nav-badge">{item.badge}</span>
                  )}
                </>
              )}
            </Link>
          );
        })}

        <div className="akari-sidebar-separator" />

        {/* Genre categories (collapsible) */}
        {GENRE_CATEGORIES.map((cat) => {
          const CatIcon = cat.icon;
          const isExpanded = expandedCats[cat.name] || false;
          const hasActiveGenre = cat.genres.some(isGenreActive);

          return (
            <div key={cat.name} className="akari-cat-group">
              <button
                className={`akari-cat-header ${hasActiveGenre ? "has-active" : ""}`}
                onClick={() => toggleCat(cat.name)}
                title={collapsed ? cat.name : undefined}
              >
                <CatIcon size={16} className="akari-cat-icon" />
                {!collapsed && (
                  <>
                    <span className="akari-cat-label">{cat.name}</span>
                    <ChevronRight
                      size={14}
                      className={`akari-cat-chevron ${isExpanded ? "rotated" : ""}`}
                    />
                  </>
                )}
              </button>
              {!collapsed && isExpanded && (
                <div className="akari-cat-items">
                  {cat.genres.map((genre) => {
                    const genreHref = `/genre/${genre.toLowerCase().replace(/\s+/g, "-")}`;
                    return (
                      <Link
                        key={genre}
                        href={genreHref}
                        className={`akari-genre-item ${isGenreActive(genre) ? "active" : ""}`}
                      >
                        {genre}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer: Settings + Account */}
      <div className="akari-sidebar-footer">
        <div className="akari-sidebar-separator" />
        <Link
          href="/settings"
          className={`akari-nav-item ${isActive("/settings") ? "active" : ""}`}
          title={collapsed ? "Settings" : undefined}
        >
          <Settings size={18} className="akari-nav-icon" />
          {!collapsed && (
            <>
              <span className="akari-nav-label">Settings</span>
              <kbd className="akari-shortcut">⌘,</kbd>
            </>
          )}
        </Link>
        <button
          className="akari-account-btn"
          title={collapsed ? "Sign in" : undefined}
        >
          <div className="akari-account-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21c0-4 4-7 8-7s8 3 8 7" />
            </svg>
          </div>
          {!collapsed && (
            <div className="akari-account-info">
              <div className="akari-account-name">Sign in</div>
              <div className="akari-account-sub">AniList account</div>
            </div>
          )}
        </button>
      </div>
    </aside>
  );
}
