"use client";
import { useState, useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";

const TABS = [
  { id: "general", label: "General", icon: "⚙️" },
  { id: "reader", label: "Reader", icon: "📖" },
  { id: "library", label: "Library", icon: "📚" },
  { id: "appearance", label: "Appearance", icon: "🎨" },
  { id: "shortcuts", label: "Shortcuts", icon: "⌨️" },
  { id: "account", label: "Account", icon: "👤" },
  { id: "data", label: "Data & Sync", icon: "🔄" },
  { id: "about", label: "About", icon: "ℹ️" },
];

const DEFAULT_SETTINGS = {
  theme: "dark" as "dark" | "light" | "system",
  fancyAnimations: true,
  showToast: true,
  pageDisplayType: "auto" as "auto" | "page" | "strip",
  showPageProgress: true,
  stripReaderWidth: 800,
  readingDirection: "ltr" as "ltr" | "rtl",
  advanceChapterOnLastPage: true,
  showFrame: true,
  defaultSort: "title" as "title" | "recent" | "score",
  showAlphabetRail: true,
  accentColor: "#ffffff",
  cardDensity: "comfortable" as "comfortable" | "compact",
};

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("mangamaru:settings");
      if (raw) setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(raw) });
    } catch {}
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (loaded) localStorage.setItem("mangamaru:settings", JSON.stringify(settings));
  }, [settings, loaded]);

  const update = <K extends keyof typeof DEFAULT_SETTINGS>(key: K, value: (typeof DEFAULT_SETTINGS)[K]) => setSettings((s) => ({ ...s, [key]: value }));

  return (
    <>
      <TopBar />
      <div className="settings-page">
        <div className="lib-header">
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Customize MangaMaru to fit your reading style</p>
        </div>

        <div className="settings-layout">
          <nav className="settings-tabs">
            {TABS.map((t) => (
              <button key={t.id} className={`settings-tab ${activeTab === t.id ? "active" : ""}`} onClick={() => setActiveTab(t.id)}>
                <span className="tab-icon">{t.icon}</span>
                <span className="tab-label">{t.label}</span>
              </button>
            ))}
          </nav>

          <div className="settings-content">
            {activeTab === "general" && (
              <div className="settings-section">
                <h2 className="settings-section-title">General</h2>
                <SettingRow label="Theme" desc="Light, dark, or follow system">
                  <select className="setting-select" value={settings.theme} onChange={(e) => update("theme", e.target.value as any)}>
                    <option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option>
                  </select>
                </SettingRow>
                <SettingRow label="Fancy Animations" desc="Cover image animations and transitions">
                  <Toggle checked={settings.fancyAnimations} onChange={(v) => update("fancyAnimations", v)} />
                </SettingRow>
                <SettingRow label="Show Toast Notifications" desc="Brief pop-ups for actions">
                  <Toggle checked={settings.showToast} onChange={(v) => update("showToast", v)} />
                </SettingRow>
              </div>
            )}

            {activeTab === "reader" && (
              <div className="settings-section">
                <h2 className="settings-section-title">Reader</h2>
                <SettingRow label="Page Display Type" desc="Auto detects by format, or force page/strip">
                  <select className="setting-select" value={settings.pageDisplayType} onChange={(e) => update("pageDisplayType", e.target.value as any)}>
                    <option value="auto">Auto</option><option value="page">Page-by-page</option><option value="strip">Vertical strip</option>
                  </select>
                </SettingRow>
                <SettingRow label="Show Page Progress" desc="Progress bar at the bottom when reading">
                  <Toggle checked={settings.showPageProgress} onChange={(v) => update("showPageProgress", v)} />
                </SettingRow>
                <SettingRow label="Panel Frame" desc="Bold framed panel with offset shadow around active page">
                  <Toggle checked={settings.showFrame} onChange={(v) => update("showFrame", v)} />
                </SettingRow>
                <SettingRow label="Strip Reader Width" desc="Max width of vertical strip reader">
                  <input type="range" min={500} max={1200} step={50} value={settings.stripReaderWidth} onChange={(e) => update("stripReaderWidth", parseInt(e.target.value))} className="setting-range" />
                  <span style={{ marginLeft: 12, color: "var(--dim)", fontSize: 13 }}>{settings.stripReaderWidth}px</span>
                </SettingRow>
                <SettingRow label="Reading Direction" desc="Left-to-right (manga) or right-to-left (Japanese)">
                  <select className="setting-select" value={settings.readingDirection} onChange={(e) => update("readingDirection", e.target.value as any)}>
                    <option value="ltr">Left to Right</option><option value="rtl">Right to Left</option>
                  </select>
                </SettingRow>
                <SettingRow label="Auto-advance on Last Page" desc="Move to next chapter when reaching the last page">
                  <Toggle checked={settings.advanceChapterOnLastPage} onChange={(v) => update("advanceChapterOnLastPage", v)} />
                </SettingRow>
              </div>
            )}

            {activeTab === "library" && (
              <div className="settings-section">
                <h2 className="settings-section-title">Library</h2>
                <SettingRow label="Default Sort" desc="How saved manga are sorted by default">
                  <select className="setting-select" value={settings.defaultSort} onChange={(e) => update("defaultSort", e.target.value as any)}>
                    <option value="title">Title (A-Z)</option><option value="recent">Recently Added</option><option value="score">Score</option>
                  </select>
                </SettingRow>
                <SettingRow label="Alphabet Jump Rail" desc="Show floating A-Z rail on library page">
                  <Toggle checked={settings.showAlphabetRail} onChange={(v) => update("showAlphabetRail", v)} />
                </SettingRow>
              </div>
            )}

            {activeTab === "appearance" && (
              <div className="settings-section">
                <h2 className="settings-section-title">Appearance</h2>
                <SettingRow label="Accent Color" desc="The single accent color used throughout the UI">
                  <input type="color" value={settings.accentColor} onChange={(e) => update("accentColor", e.target.value)} className="setting-color" />
                  <span style={{ marginLeft: 12, color: "var(--dim)", fontSize: 13, fontFamily: "monospace" }}>{settings.accentColor}</span>
                </SettingRow>
                <SettingRow label="Card Density" desc="How tightly cards pack in grids">
                  <select className="setting-select" value={settings.cardDensity} onChange={(e) => update("cardDensity", e.target.value as any)}>
                    <option value="comfortable">Comfortable</option><option value="compact">Compact</option>
                  </select>
                </SettingRow>
              </div>
            )}

            {activeTab === "shortcuts" && (
              <div className="settings-section">
                <h2 className="settings-section-title">Keyboard Shortcuts</h2>
                <p style={{ color: "var(--dim)", fontSize: 13, marginBottom: 16 }}>Mod = Ctrl (Windows/Linux) or Cmd (Mac).</p>
                {[
                  { key: "Mod + K", desc: "Focus the search bar" },
                  { key: "→", desc: "Next page (in reader)" },
                  { key: "←", desc: "Previous page (in reader)" },
                ].map((s) => (
                  <div key={s.key} className="shortcut-row">
                    <div className="shortcut-desc">{s.desc}</div>
                    <kbd className="shortcut-key">{s.key}</kbd>
                  </div>
                ))}
              </div>
            )}

            {activeTab === "account" && (
              <div className="settings-section">
                <h2 className="settings-section-title">Account</h2>
                <div style={{ padding: 20, textAlign: "center", background: "var(--surface-2)", borderRadius: 12, border: "1px solid var(--border)" }}>
                  <div style={{ fontSize: 48, marginBottom: 12 }}>👤</div>
                  <h3 style={{ fontSize: 18, marginBottom: 6 }}>Not signed in</h3>
                  <p style={{ color: "var(--dim)", fontSize: 13, marginBottom: 18 }}>Sign in with AniList to sync bookmarks and reading progress.</p>
                  <a href="https://anilist.co/api/v2/oauth/authorize?client_id=46773&response_type=code" className="btn-primary" style={{ display: "inline-flex" }}>
                    <span>Sign in with AniList</span>
                  </a>
                </div>
              </div>
            )}

            {activeTab === "data" && (
              <div className="settings-section">
                <h2 className="settings-section-title">Data & Sync</h2>
                <SettingRow label="Local Storage" desc="All your bookmarks, tags, and reading progress are stored locally">
                  <button className="btn-secondary" onClick={() => { if (confirm('Clear all local data?')) { localStorage.clear(); alert('Cleared.'); } }}>Clear Local Data</button>
                </SettingRow>
              </div>
            )}

            {activeTab === "about" && (
              <div className="settings-section">
                <h2 className="settings-section-title">About MangaMaru</h2>
                <div style={{ padding: 24, background: "var(--surface-2)", borderRadius: 12, border: "1px solid var(--border)" }}>
                  <h3 style={{ fontSize: 22, marginBottom: 6 }}>Manga<span style={{ color: "var(--accent)" }}>Maru</span> v9.1</h3>
                  <p style={{ color: "var(--dim)", fontSize: 13, marginBottom: 16, lineHeight: 1.6 }}>A hybrid manga reader combining ideas from three open-source projects:</p>
                  <ul style={{ listStyle: "none", fontSize: 13, color: "var(--dim)", lineHeight: 1.8 }}>
                    <li>🦀 <a href="https://github.com/manga-you-know/desktop" target="_blank" rel="noopener" style={{ color: "var(--accent)" }}>MangaYouKnow</a> — dense 8-col grid, floating unread badges, gradient frame</li>
                    <li>🌸 <a href="https://github.com/sn0w12/akari" target="_blank" rel="noopener" style={{ color: "var(--accent)" }}>Akari</a> — 64px icon-only rail, split-card hero with metadata grid, settings panel</li>
                    <li>📚 <a href="https://github.com/hankscafe/omnibus" target="_blank" rel="noopener" style={{ color: "var(--accent)" }}>Omnibus</a> &mdash; header-heavy topbar, &ldquo;Show N&rdquo; dropdown + pagination, card progress bars</li>
                  </ul>
                  <p style={{ color: "var(--dim)", fontSize: 12, marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>Data source: <a href="https://anilist.co" target="_blank" rel="noopener" style={{ color: "var(--accent)" }}>AniList GraphQL API</a></p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function SettingRow({ label, desc, children }: { label: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="setting-row">
      <div className="setting-label-wrap"><div className="setting-label">{label}</div>{desc && <div className="setting-desc">{desc}</div>}</div>
      <div className="setting-control">{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button className={`toggle ${checked ? "on" : ""}`} onClick={() => onChange(!checked)} role="switch" aria-checked={checked}>
      <span className="toggle-thumb"></span>
    </button>
  );
}
