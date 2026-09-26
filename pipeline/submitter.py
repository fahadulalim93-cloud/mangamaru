#!/usr/bin/env python3
"""
LuffyTV URL Submitter - Web interface at port 9000
Lets you paste direct download URLs (cloud-dl workers.dev links, etc.)
and the existing luffytv-uploader service handles the rest:
  - Downloads to /root/downloads/
  - Extracts zips
  - Uploads each video to byse.sx
  - Saves to database with anime_name + episode + URL
  - Deletes local files
"""
import os
import json
import sqlite3
import threading
import subprocess
import queue as queue_mod
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, make_response
from urllib.parse import urlparse, unquote

# ============================================================
# CONFIG
# ============================================================
DOWNLOAD_DIR = "/root/downloads"
DB_FILE = "/var/lib/luffytv/anime.db"
JSON_FILE = "/var/lib/luffytv/anime.json"
PORT = 9000
SUBMITTED_URLS_LOG = "/var/log/luffytv-submitted-urls.txt"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SUBMITTED_URLS_LOG), exist_ok=True)

app = Flask(__name__)

# ============================================================
# HTML PAGE
# ============================================================
HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LuffyTV - URL Submitter</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🏴‍☠️%3C/text%3E%3C/svg%3E">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --bg: #000; --surface: #0a0a0a; --surface-2: #141414;
    --border: #262626; --text: #fff; --text-2: #9ca3af; --text-3: #6b7280;
    --accent: #FF4D6A; --cyan: #00E5FF; --purple: #A855F7; --green: #22c55e;
  }
  body {
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    min-height: 100vh; padding: 24px;
  }
  .container { max-width: 1100px; margin: 0 auto; }
  .header {
    display: flex; align-items: center; gap: 16px;
    padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 32px;
  }
  .logo {
    font-size: 24px; font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle { color: var(--text-2); font-size: 14px; }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 24px;
  }
  .card h2 {
    font-size: 18px; font-weight: 700; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }
  .form-group { margin-bottom: 16px; }
  label {
    display: block; font-size: 13px; font-weight: 600;
    color: var(--text-2); margin-bottom: 6px; text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  input, textarea, select {
    width: 100%; background: var(--surface-2); color: var(--text);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 12px 14px; font-size: 14px; font-family: inherit;
  }
  input:focus, textarea:focus, select:focus {
    outline: none; border-color: var(--accent);
  }
  textarea { min-height: 120px; resize: vertical; font-family: monospace; }
  .btn {
    background: var(--accent); color: white; border: none;
    padding: 12px 24px; border-radius: 8px; font-size: 14px;
    font-weight: 600; cursor: pointer; transition: all 0.15s;
  }
  .btn:hover { background: #e63e58; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .hint { font-size: 12px; color: var(--text-3); margin-top: 6px; }
  .hint code { background: var(--surface-2); padding: 2px 6px; border-radius: 4px; font-size: 11px; }
  .status {
    padding: 12px 16px; border-radius: 8px; margin-top: 16px;
    font-size: 14px; display: none;
  }
  .status.show { display: block; }
  .status.success { background: rgba(34, 197, 94, 0.1); border: 1px solid var(--green); color: var(--green); }
  .status.error { background: rgba(255, 77, 106, 0.1); border: 1px solid var(--accent); color: var(--accent); }
  .status.info { background: rgba(0, 229, 255, 0.1); border: 1px solid var(--cyan); color: var(--cyan); }
  /* Stats */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px;
  }
  .stat-value { font-size: 28px; font-weight: 800; }
  .stat-label { font-size: 12px; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.5px; }
  /* Table */
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--text-2); font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }
  tr:hover { background: var(--surface-2); }
  .anime-name { color: var(--text); font-weight: 600; }
  .episode { color: var(--cyan); font-family: monospace; }
  .url-link { color: var(--accent); text-decoration: none; word-break: break-all; }
  .url-link:hover { text-decoration: underline; }
  .empty { color: var(--text-3); text-align: center; padding: 32px; font-size: 14px; }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white; border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  /* Queue */
  .queue-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 14px; background: var(--surface-2);
    border-radius: 8px; margin-bottom: 8px; font-size: 13px;
  }
  .queue-status {
    padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
  }
  .queue-status.downloading { background: rgba(0, 229, 255, 0.15); color: var(--cyan); }
  .queue-status.done { background: rgba(34, 197, 94, 0.15); color: var(--green); }
  .queue-status.failed { background: rgba(255, 77, 106, 0.15); color: var(--accent); }
  .queue-status.processing { background: rgba(168, 85, 247, 0.15); color: var(--purple); }
  /* JSON viewer */
  .json-toolbar {
    display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
    margin-bottom: 16px;
  }
  .btn-secondary {
    background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
    padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all 0.15s; text-decoration: none;
    display: inline-block;
  }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
  .json-search {
    flex: 1; min-width: 200px;
    background: var(--surface-2); color: var(--text);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 14px; font-size: 13px; font-family: inherit;
  }
  .json-search:focus { outline: none; border-color: var(--accent); }
  .json-tree {
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px; overflow-x: auto;
    font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace;
    font-size: 13px; line-height: 1.6; max-height: 70vh; overflow-y: auto;
  }
  .json-key { color: var(--accent); }
  .json-string { color: var(--green); }
  .json-number { color: var(--cyan); }
  .json-bool { color: var(--purple); }
  .json-null { color: var(--text-3); }
  .json-bracket { color: var(--text-2); }
  .json-card { margin-bottom: 24px; }
  .json-summary {
    color: var(--text-2); font-size: 13px; margin-bottom: 12px;
  }
  .lang-tag {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 11px; font-weight: 600; margin-right: 4px;
    background: rgba(168, 85, 247, 0.15); color: var(--purple);
  }
  .lang-tag.hindi { background: rgba(255, 77, 106, 0.15); color: var(--accent); }
  .lang-tag.japanese { background: rgba(0, 229, 255, 0.15); color: var(--cyan); }
  .lang-tag.english { background: rgba(34, 197, 94, 0.15); color: var(--green); }
  /* Current download progress */
  .dl-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  .dl-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 8px; font-size: 13px; }
  .dl-name { font-weight: 600; color: var(--text); word-break: break-all; flex: 1; }
  .dl-status {
    padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap;
  }
  .dl-status.downloading { background: rgba(0, 229, 255, 0.15); color: var(--cyan); }
  .dl-status.queued { background: rgba(156, 163, 175, 0.15); color: var(--text-2); }
  .dl-status.done { background: rgba(34, 197, 94, 0.15); color: var(--green); }
  .dl-status.failed { background: rgba(255, 77, 106, 0.15); color: var(--accent); }
  .dl-status.idle { background: rgba(156, 163, 175, 0.15); color: var(--text-3); }
  .progress-bar {
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 6px; height: 22px; overflow: hidden; position: relative;
    margin: 8px 0;
  }
  .progress-fill {
    height: 100%; background: linear-gradient(90deg, var(--accent), var(--purple));
    transition: width 0.4s ease; display: flex; align-items: center;
    justify-content: flex-end; padding-right: 8px;
    color: white; font-size: 11px; font-weight: 700;
  }
  .progress-fill.failed { background: linear-gradient(90deg, #b91c1c, var(--accent)); }
  .progress-fill.done { background: linear-gradient(90deg, #16a34a, var(--green)); }
  .progress-fill.queued { background: var(--surface-2); color: var(--text-2); }
  .dl-meta {
    display: flex; gap: 16px; flex-wrap: wrap; color: var(--text-2);
    font-size: 12px; margin-top: 8px;
  }
  .dl-meta span strong { color: var(--text); }
  .dl-log {
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 6px; padding: 10px; margin-top: 12px;
    font-family: monospace; font-size: 11px; color: var(--text-2);
    max-height: 200px; overflow-y: auto; white-space: pre-wrap;
  }
  .queue-summary {
    display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px;
    font-size: 12px; color: var(--text-2);
  }
  .queue-summary .badge {
    padding: 4px 10px; border-radius: 12px; font-weight: 600;
    background: var(--surface-2); border: 1px solid var(--border);
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="logo">🏴‍☠️ LuffyTV Uploader</div>
      <div class="subtitle">Manga/manhwa scraper — auto-download + upload to 8upload.com</div>
    </div>
  </div>

  <div class="stats" id="stats">
    <div class="stat-card">
      <div class="stat-value" id="mangaTotal">-</div>
      <div class="stat-label">Manga Series</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="mangaChapters">-</div>
      <div class="stat-label">Chapters</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="mangaPages">-</div>
      <div class="stat-label">Pages Uploaded</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="mangaQueue">-</div>
      <div class="stat-label">In Queue</div>
    </div>
  </div>

  <div class="card">
    <h2>📖 Manga Scraper (by AniList ID)</h2>
    <p class="hint" style="margin-bottom: 16px;">
      Enter one or more AniList manga IDs (comma-separated). The scraper will download ALL chapters for each manga serially,
      upload every page to 8upload.com, save URLs to the database, then delete the local file and move to the next manga.
    </p>
    <form id="mangaScrapeForm">
      <div class="form-group">
        <label>AniList Manga IDs *</label>
        <textarea id="anilistIds" placeholder="105398, 30013, 101517&#10;(Solo Leveling, One Piece, Jujutsu Kaisen)" required></textarea>
        <div class="hint">Find AniList IDs at <code>https://anilist.co/search/manga</code> — the number in the URL is the ID.</div>
      </div>
      <button type="submit" class="btn" id="mangaScrapeBtn" style="background: var(--purple);">
        📖 Start Serial Scraping
      </button>
    </form>
    <div class="status" id="mangaScrapeStatus"></div>
  </div>

  <div class="card">
    <h2>📖 Currently Uploading Manga</h2>
    <div id="mangaUploadingCard">
      <div class="empty">Loading...</div>
    </div>
  </div>

  <div class="card">
    <h2>💾 Manga Database</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Manga Name</th>
            <th>Chapter</th>
            <th>Page</th>
            <th>Image URL</th>
            <th>Uploaded</th>
          </tr>
        </thead>
        <tbody id="mangaDbRows">
          <tr><td colspan="6" class="empty">Loading...</td></tr>
        </tbody>
      </table>
    </div>
    <div style="margin-top: 16px;">
      <a href="/manga" class="btn-secondary" target="_blank">📖 View Manga Library</a>
      <a href="/api/manga/json" class="btn-secondary" target="_blank" style="margin-left: 8px;">⚡ Raw JSON API</a>
      <a href="/api/manga/db" class="btn-secondary" target="_blank" style="margin-left: 8px;">📊 Raw DB API</a> <a href="/manga/series" class="btn-secondary" target="_blank" style="margin-left: 8px;">📚 Series Overview</a>
    </div>
  </div>
</div>

<script>
async function refreshStats() {
  try {
    const r = await fetch('/api/manga/stats');
    const d = await r.json();
    document.getElementById('mangaTotal').textContent = d.total_manga || 0;
    document.getElementById('mangaChapters').textContent = d.total_chapters || 0;
    document.getElementById('mangaPages').textContent = d.total_pages || 0;
    // Get queue count from watcher
    const r2 = await fetch('/api/manga-watcher');
    const d2 = await r2.json();
    document.getElementById('mangaQueue').textContent = (d2.queue || []).length;
  } catch (e) { console.error(e); }
}

async function refreshMangaDb() {
  try {
    const r = await fetch('/api/manga/db');
    const d = await r.json();
    const el = document.getElementById('mangaDbRows');
    if (!d.rows || d.rows.length === 0) {
      el.innerHTML = '<tr><td colspan="6" class="empty">No manga uploaded yet</td></tr>';
      return;
    }
    el.innerHTML = d.rows.map(row => `
      <tr>
        <td>${row.id}</td>
        <td class="anime-name">${escapeHtml(row.manga_name)}</td>
        <td class="episode">${row.chapter_number}</td>
        <td>p${row.page_number}</td>
        <td><a href="${row.image_url}" target="_blank" class="url-link">${row.image_url.substring(0, 60)}...</a></td>
        <td style="color: var(--text-3); font-size: 12px;">${row.uploaded_at}</td>
      </tr>
    `).join('');
  } catch (e) {
    document.getElementById('mangaDbRows').innerHTML = '<tr><td colspan="6" class="empty">Failed to load DB</td></tr>';
  }
}

async function refreshQueue() {
  try {
    const r = await fetch('/api/queue');
    const d = await r.json();
    const el = document.getElementById('queueList');
    if (!d.queue || d.queue.length === 0) {
      el.innerHTML = '<div class="empty">No recent submissions</div>';
      return;
    }
    el.innerHTML = d.queue.slice(0, 10).map(item => `
      <div class="queue-item">
        <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%;">
          <span style="color: var(--text-2);">${item.timestamp}</span> &nbsp;
          <span>${escapeHtml(item.filename || item.url.substring(0, 80) + '...')}</span>
        </div>
        <span class="queue-status ${item.status}">${item.status}</span>
      </div>
    `).join('');
  } catch (e) { console.error(e); }
}

async function refreshDb() {
  try {
    const r = await fetch('/api/database');
    const d = await r.json();
    const el = document.getElementById('dbRows');
    if (!d.rows || d.rows.length === 0) {
      el.innerHTML = '<tr><td colspan="5" class="empty">No uploads yet</td></tr>';
      return;
    }
    el.innerHTML = d.rows.map(row => `
      <tr>
        <td>${row.id}</td>
        <td class="anime-name">${escapeHtml(row.anime_name)}</td>
        <td class="episode">${row.episode_number}</td>
        <td><a href="${row.byse_url}" target="_blank" class="url-link">${row.byse_url.substring(0, 60)}...</a></td>
        <td style="color: var(--text-3); font-size: 12px;">${row.uploaded_at}</td>
      </tr>
    `).join('');
  } catch (e) {
    document.getElementById('dbRows').innerHTML = '<tr><td colspan="5" class="empty">Failed to load DB</td></tr>';
  }
}

function fmtBytes(b) {
  if (!b || b === 0) return '—';
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  if (b < 1024 * 1024 * 1024) return (b / (1024 * 1024)).toFixed(1) + ' MB';
  return (b / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}
function fmtSpeed(kbps) {
  if (!kbps || kbps <= 0) return '—';
  if (kbps < 1024) return kbps.toFixed(0) + ' KB/s';
  return (kbps / 1024).toFixed(2) + ' MB/s';
}
function fmtEta(s) {
  if (!s || s <= 0) return '—';
  if (s < 60) return s + 's';
  if (s < 3600) return Math.floor(s / 60) + 'm ' + (s % 60) + 's';
  return Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
}

function timeAgo(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.floor(s / 60) + 'm ago';
  if (s < 86400) return Math.floor(s / 3600) + 'h ago';
  return Math.floor(s / 86400) + 'd ago';
}

async function refreshMangaUploading() {
  try {
    const r = await fetch('/api/manga-watcher');
    const d = await r.json();
    const el = document.getElementById('mangaUploadingCard');
    const cur = d.currently_uploading;
    const queue = d.queue || [];
    const recent = d.recently_completed || [];
    const stats = d.stats || {};
    const scanning = d.scanning;
    let html = '';
    if (cur) {
      const sizeMB = cur.size_bytes ? (cur.size_bytes / (1024 * 1024)).toFixed(1) : '?';
      const startedAgo = timeAgo(cur.started_at);
      html += `
        <div class="dl-card" style="border-color: var(--cyan); margin-bottom: 12px;">
          <div class="dl-row">
            <span class="dl-name">📖 ${escapeHtml(cur.filename || '')}</span>
            <span class="dl-status downloading">Uploading</span>
          </div>
          <div class="dl-meta">
            <span>Size: <strong>${sizeMB} MB</strong></span>
            <span>Started: <strong>${startedAgo}</strong></span>
          </div>
          <div style="margin-top: 8px; color: var(--text-3); font-size: 12px;">
            ⏳ Uploading pages to image host...
          </div>
        </div>`;
    } else {
      html += `
        <div class="dl-card" style="margin-bottom: 12px;">
          <div class="dl-row">
            <span class="dl-name" style="color: var(--text-2);">No manga chapter uploading</span>
            <span class="dl-status idle">Idle</span>
          </div>
        </div>`;
    }
    html += `
      <div class="queue-summary">
        <span class="badge">In queue: <strong>${queue.length}</strong></span>
        <span class="badge">Done: <strong>${stats.total_completed_today || 0}</strong></span>
        ${scanning ? '<span class="badge" style="color: var(--cyan);">⟳ Scanning...</span>' : ''}
      </div>`;
    if (queue.length > 0) {
      html += `<div style="margin-top: 12px; color: var(--text-2); font-size: 12px; font-weight: 600;">NEXT IN QUEUE</div>`;
      html += '<div style="margin-top: 6px;">';
      queue.slice(0, 5).forEach((q, i) => {
        const sizeKB = q.size_bytes ? (q.size_bytes / 1024).toFixed(0) : '?';
        html += `
          <div style="padding: 6px 10px; margin-bottom: 4px; background: var(--surface-2); border-radius: 4px; font-size: 12px; color: var(--text-2);">
            <strong style="color: var(--text);">${i + 1}.</strong> ${escapeHtml(q.filename.substring(0, 60))}
            <span style="color: var(--text-3); float: right;">${sizeKB} KB</span>
          </div>`;
      });
      if (queue.length > 5) {
        html += `<div style="text-align: center; color: var(--text-3); font-size: 12px; padding: 4px;">+ ${queue.length - 5} more...</div>`;
      }
      html += '</div>';
    }
    if (recent.length > 0) {
      html += `<div style="margin-top: 16px; color: var(--text-2); font-size: 12px; font-weight: 600;">RECENTLY UPLOADED</div>`;
      html += '<div style="margin-top: 6px;">';
      recent.slice(0, 5).forEach((r2) => {
        html += `
          <div style="padding: 6px 10px; margin-bottom: 4px; background: var(--surface-2); border-radius: 4px; font-size: 12px;">
            <div style="color: var(--text); font-weight: 600;">✓ ${escapeHtml(r2.filename.substring(0, 60))}</div>
            <div style="color: var(--text-3); font-size: 11px;">${timeAgo(r2.completed_at)}</div>
          </div>`;
      });
      html += '</div>';
    }
    el.innerHTML = html;
  } catch (e) {
    console.error('refreshMangaUploading error:', e);
  }
}

async function refreshCurrentlyUploading() {
  try {
    const r = await fetch('/api/media-watcher');
    const d = await r.json();
    const el = document.getElementById('currentlyUploadingCard');

    const cur = d.currently_uploading;
    const queue = d.queue || [];
    const recent = d.recently_completed || [];
    const stats = d.stats || {};
    const scanning = d.scanning;

    let html = '';

    // === Current upload ===
    if (cur) {
      const sizeMB = cur.size_bytes ? (cur.size_bytes / (1024 * 1024)).toFixed(0) : '?';
      const startedAgo = timeAgo(cur.started_at);
      html += `
        <div class="dl-card" style="border-color: var(--green); margin-bottom: 12px;">
          <div class="dl-row">
            <span class="dl-name">⬆️ ${escapeHtml(cur.filename || '')}</span>
            <span class="dl-status downloading">Uploading</span>
          </div>
          <div class="dl-meta">
            <span>Size: <strong>${sizeMB} MB</strong></span>
            <span>Started: <strong>${startedAgo}</strong></span>
          </div>
          <div style="margin-top: 8px; color: var(--text-3); font-size: 12px;">
            ⏳ Waiting for luffytv-uploader to finish (deletes the symlink when done)...
          </div>
        </div>`;
    } else {
      html += `
        <div class="dl-card" style="margin-bottom: 12px;">
          <div class="dl-row">
            <span class="dl-name" style="color: var(--text-2);">No file currently uploading</span>
            <span class="dl-status idle">Idle</span>
          </div>
        </div>`;
    }

    // === Queue summary ===
    html += `
      <div class="queue-summary">
        <span class="badge">In queue: <strong>${queue.length}</strong></span>
        <span class="badge">Completed today: <strong>${stats.total_completed_today || 0}</strong></span>
        <span class="badge">Skipped (already uploaded): <strong>${stats.total_skipped_already_uploaded || 0}</strong></span>
        ${scanning ? '<span class="badge" style="color: var(--cyan);">⟳ Scanning...</span>' : ''}
      </div>`;

    // === Next 5 in queue ===
    if (queue.length > 0) {
      html += `<div style="margin-top: 12px; color: var(--text-2); font-size: 12px; font-weight: 600;">NEXT IN QUEUE</div>`;
      html += '<div style="margin-top: 6px;">';
      queue.slice(0, 5).forEach((q, i) => {
        const sizeMB = q.size_bytes ? (q.size_bytes / (1024 * 1024)).toFixed(0) : '?';
        html += `
          <div style="padding: 6px 10px; margin-bottom: 4px; background: var(--surface-2); border-radius: 4px; font-size: 12px; color: var(--text-2);">
            <strong style="color: var(--text);">${i + 1}.</strong> ${escapeHtml(q.filename.substring(0, 70))}
            <span style="color: var(--text-3); float: right;">${sizeMB} MB</span>
          </div>`;
      });
      if (queue.length > 5) {
        html += `<div style="text-align: center; color: var(--text-3); font-size: 12px; padding: 4px;">+ ${queue.length - 5} more...</div>`;
      }
      html += '</div>';
    }

    // === Recently completed (with byse links) ===
    if (recent.length > 0) {
      html += `<div style="margin-top: 16px; color: var(--text-2); font-size: 12px; font-weight: 600;">RECENTLY UPLOADED</div>`;
      html += '<div style="margin-top: 6px;">';
      recent.slice(0, 8).forEach((r2) => {
        const url = r2.byse_url ? `<a href="${escapeHtml(r2.byse_url)}" target="_blank" class="url-link">${escapeHtml(r2.byse_url.substring(0, 40))}...</a>` : '<span style="color: var(--text-3);">—</span>';
        const name = r2.anime_name ? `${escapeHtml(r2.anime_name)} ${escapeHtml(r2.episode || '')}` : escapeHtml(r2.filename.substring(0, 50));
        html += `
          <div style="padding: 6px 10px; margin-bottom: 4px; background: var(--surface-2); border-radius: 4px; font-size: 12px;">
            <div style="color: var(--text); font-weight: 600;">✓ ${name}</div>
            <div style="color: var(--text-3); font-size: 11px;">${timeAgo(r2.completed_at)} — ${url}</div>
          </div>`;
      });
      html += '</div>';
    }

    el.innerHTML = html;
  } catch (e) {
    console.error('refreshCurrentlyUploading error:', e);
  }
}

async function refreshCurrent() {
  try {
    const r = await fetch('/api/current');
    const d = await r.json();
    const el = document.getElementById('currentDownloadCard');

    // No active download — show queue summary if there's queued work
    if (!d.url && d.status === 'idle') {
      const q = d.queue_stats || {};
      if (q.queued > 0) {
        el.innerHTML = `
          <div class="dl-card">
            <div class="dl-row">
              <span class="dl-name" style="color: var(--text-2);">Waiting for next download…</span>
              <span class="dl-status queued">Idle</span>
            </div>
            <div class="queue-summary">
              <span class="badge">Queued: <strong>${q.queued}</strong></span>
              <span class="badge">Done: <strong>${q.done}</strong></span>
              ${q.failed > 0 ? `<span class="badge" style="color: var(--accent);">Failed: <strong>${q.failed}</strong></span>` : ''}
            </div>
          </div>`;
      } else {
        el.innerHTML = `<div class="empty">No active download. Submit a URL above to start.</div>`;
      }
      return;
    }

    let pct = d.percent || 0;
    if (pct > 100) pct = 100;
    let statusClass = d.status || 'idle';
    if (statusClass === 'failed') statusClass = 'failed';
    else if (statusClass === 'done') statusClass = 'done';

    let progressHTML = '';
    if (d.bytes_total > 0 || d.percent > 0) {
      progressHTML = `
        <div class="progress-bar">
          <div class="progress-fill ${statusClass}" style="width: ${pct.toFixed(1)}%;">
            ${pct > 5 ? pct.toFixed(0) + '%' : ''}
          </div>
        </div>`;
    }

    let metaHTML = `
      <div class="dl-meta">
        <span>Downloaded: <strong>${fmtBytes(d.bytes_downloaded)}</strong> / ${fmtBytes(d.bytes_total)}</span>
        <span>Speed: <strong>${fmtSpeed(d.speed_kbps)}</strong></span>
        <span>ETA: <strong>${fmtEta(d.eta_seconds)}</strong></span>
      </div>`;

    let logHTML = '';
    if (d.log_tail && d.log_tail.length > 0) {
      logHTML = `<div class="dl-log">${d.log_tail.map(escapeHtml).join('\\n')}</div>`;
    }

    let queueBadges = '';
    if (d.queue_stats) {
      const q = d.queue_stats;
      queueBadges = `
        <div class="queue-summary">
          <span class="badge">Queued: <strong>${q.queued}</strong></span>
          <span class="badge">Done: <strong>${q.done}</strong></span>
          ${q.failed > 0 ? `<span class="badge" style="color: var(--accent);">Failed: <strong>${q.failed}</strong></span>` : ''}
        </div>`;
    }

    el.innerHTML = `
      <div class="dl-card">
        <div class="dl-row">
          <span class="dl-name">${escapeHtml(d.filename || d.url || '')}</span>
          <span class="dl-status ${statusClass}">${escapeHtml(d.status || 'idle')}</span>
        </div>
        ${progressHTML}
        ${metaHTML}
        ${queueBadges}
        ${logHTML}
      </div>`;
  } catch (e) {
    console.error('refreshCurrent error:', e);
  }
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

function showStatus(msg, type = 'info') {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status show ' + type;
}

// === Manga scraper form handler ===
document.getElementById('mangaScrapeForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('mangaScrapeBtn');
  const ids = document.getElementById('anilistIds').value.trim();
  const statusEl = document.getElementById('mangaScrapeStatus');

  if (!ids) {
    statusEl.textContent = 'Please enter at least one AniList ID';
    statusEl.className = 'status show error';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Scraping...';
  statusEl.textContent = '📖 Starting serial scrape for AniList IDs: ' + ids;
  statusEl.className = 'status show info';

  try {
    const r = await fetch('/api/manga/scrape', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ anilist_ids: ids })
    });
    const d = await r.json();
    if (d.success) {
      statusEl.textContent = `✅ Started! ${d.message} Watch the "Currently Uploading Manga" card above for live progress.`;
      statusEl.className = 'status show success';
      document.getElementById('anilistIds').value = '';
      setTimeout(refreshMangaUploading, 2000);
    } else {
      statusEl.textContent = `❌ ${d.error || 'Failed to start scraping'}`;
      statusEl.className = 'status show error';
    }
  } catch (err) {
    statusEl.textContent = `❌ Error: ${err.message}`;
    statusEl.className = 'status show error';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '📖 Start Serial Scraping';
  }
});

refreshStats();
refreshMangaDb();
refreshMangaUploading();
setInterval(() => {
  refreshStats();
  refreshMangaDb();
  refreshMangaUploading();
}, 2000);
</script>
</body>
</html>
'''

# ============================================================
# QUEUE TRACKING (serial worker)
# ============================================================
queue = []           # list of dicts (for display) — newest first
queue_lock = threading.Lock()
work_queue = queue_mod.Queue()   # internal FIFO of (url, filename)

current_download = {
    "url": None,
    "filename": None,
    "status": "idle",          # idle | downloading | extracting | uploading | done | failed
    "started_at": None,
    "finished_at": None,
    "bytes_total": 0,
    "bytes_downloaded": 0,
    "percent": 0.0,
    "speed_kbps": 0.0,
    "eta_seconds": None,
    "error": None,
    "log_tail": [],
}
current_lock = threading.Lock()


def add_to_queue(url, filename, status="queued"):
    with queue_lock:
        # Duplicate detection — skip if same URL OR same filename already in queue
        for item in queue:
            if item["url"] == url:
                return False  # already in queue
            if item["filename"] == filename and item["status"] in ("queued", "downloading"):
                return False  # same filename is currently being processed
        queue.insert(0, {
            "url": url,
            "filename": filename,
            "status": status,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        if len(queue) > 100:
            queue.pop()
        return True


def update_queue_status(url, status):
    """Update ALL queue items matching this URL (in case of any duplicates)."""
    with queue_lock:
        for item in queue:
            if item["url"] == url:
                item["status"] = status
                # Don't break — keep going to update all matching items


def set_current(**fields):
    with current_lock:
        current_download.update(fields)


def append_log(line):
    """Keep the last 20 log lines for the current download."""
    with current_lock:
        current_download["log_tail"].append(line.rstrip()[:200])
        if len(current_download["log_tail"]) > 20:
            current_download["log_tail"] = current_download["log_tail"][-20:]


def parse_bytes_param(url):
    """Some download URLs include a `?bytes=` param with total file size."""
    m = re.search(r'[?&]bytes=(\d+)', url)
    return int(m.group(1)) if m else 0

# ============================================================
# BACKGROUND DOWNLOAD (serial worker — one at a time)
# ============================================================
def download_in_background(url, filename):
    """Enqueue a URL for serial download. The worker picks it up when the previous finishes.
    Skips if the same URL/filename is already in the queue (dedup).
    """
    added = add_to_queue(url, filename, status="queued")
    if not added:
        print(f"[dedup] Skipping duplicate URL: {filename}")
        return False
    work_queue.put((url, filename))
    return True


def _download_worker():
    """Background thread that processes the queue ONE AT A TIME.
    Each download fully completes (extract + upload handled by luffytv-uploader service)
    before the next one starts.
    """
    while True:
        url, filename = work_queue.get()  # blocks until next item
        bytes_total = parse_bytes_param(url)
        update_queue_status(url, "downloading")
        set_current(
            url=url, filename=filename, status="downloading",
            started_at=datetime.now().isoformat(),
            finished_at=None,
            bytes_total=bytes_total,
            bytes_downloaded=0,
            percent=0.0,
            speed_kbps=0.0,
            eta_seconds=None,
            error=None,
            log_tail=[],
        )
        append_log(f"▶ Starting download: {filename}")
        if bytes_total:
            append_log(f"  Expected size: {bytes_total / (1024**3):.2f} GB")

        dest = os.path.join(DOWNLOAD_DIR, filename)

        # Check if file is already fully downloaded (skip wget entirely)
        if os.path.exists(dest):
            existing_size = os.path.getsize(dest)
            if bytes_total and existing_size >= bytes_total:
                append_log(f"✓ File already fully downloaded ({existing_size / (1024**3):.2f} GB) — skipping wget")
                update_queue_status(url, "done")
                set_current(
                    status="done",
                    finished_at=datetime.now().isoformat(),
                    bytes_downloaded=existing_size,
                    bytes_total=existing_size,
                    percent=100.0,
                    speed_kbps=0.0,
                    eta_seconds=None,
                )
                append_log("⏸ Notifying luffytv-uploader to process the existing file...")
                # Touch the file to update its mtime — luffytv-uploader's stability check
                # will detect the change and start processing it
                os.utime(dest, None)
                set_current(status="idle")
                work_queue.task_done()
                continue
            else:
                append_log(f"  Partial file exists ({existing_size / (1024**2):.0f} MB) — resuming with wget -c")

        cmd = [
            "wget", "-c", "--progress=dot:force", "--no-cache",
            "-O", dest,
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            url,
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        # wget prints progress to stderr; we read line-by-line and parse
        last_size = 0
        last_ts = datetime.now()
        for line in proc.stdout:
            append_log(line)
            m = re.search(r'(\d+)K[\s,]*([\d.]+)%', line)
            if m:
                kb_down = int(m.group(1))
                pct = float(m.group(2))
                bytes_down = kb_down * 1024
                now = datetime.now()
                dt = (now - last_ts).total_seconds()
                speed_kbps = ((bytes_down - last_size) / 1024) / dt if dt > 0 else 0
                eta = None
                if pct > 0 and bytes_total:
                    bytes_remaining = bytes_total - bytes_down
                    eta = int(bytes_remaining / (speed_kbps * 1024)) if speed_kbps > 0 else None
                set_current(
                    bytes_downloaded=bytes_down,
                    percent=pct,
                    speed_kbps=speed_kbps,
                    eta_seconds=eta,
                )
                last_size = bytes_down
                last_ts = now
        proc.wait()
        rc = proc.returncode

        if rc == 0:
            actual_size = os.path.getsize(dest) if os.path.exists(dest) else 0
            update_queue_status(url, "done")
            set_current(
                status="done",
                finished_at=datetime.now().isoformat(),
                bytes_downloaded=actual_size,
                bytes_total=actual_size or bytes_total,
                percent=100.0,
                speed_kbps=0.0,
                eta_seconds=None,
            )
            append_log(f"✓ Download complete ({actual_size / (1024**3):.2f} GB)")
            append_log("⏸ Waiting for luffytv-uploader to process...")
        elif rc == 0 or (rc is None):
            # Safety: if proc.wait() returned None or 0 but exit code was ambiguous
            update_queue_status(url, "done")
            set_current(status="done", finished_at=datetime.now().isoformat())
        else:
            # Even on wget error 416 (Range Not Satisfiable), the file is already complete
            # Check if the file exists with correct size — treat that as success
            if os.path.exists(dest):
                actual_size = os.path.getsize(dest)
                if bytes_total and actual_size >= bytes_total:
                    append_log(f"✓ File already complete ({actual_size / (1024**3):.2f} GB, exit {rc})")
                    update_queue_status(url, "done")
                    set_current(
                        status="done",
                        finished_at=datetime.now().isoformat(),
                        bytes_downloaded=actual_size,
                        bytes_total=actual_size,
                        percent=100.0,
                        speed_kbps=0.0,
                        eta_seconds=None,
                    )
                    append_log("⏸ Notifying luffytv-uploader to process...")
                else:
                    update_queue_status(url, "failed")
                    set_current(
                        status="failed",
                        finished_at=datetime.now().isoformat(),
                        error=f"wget exited with code {rc}, file size {actual_size} < expected {bytes_total}",
                    )
                    append_log(f"✗ wget exited with code {rc}, file incomplete")
            else:
                update_queue_status(url, "failed")
                set_current(
                    status="failed",
                    finished_at=datetime.now().isoformat(),
                    error=f"wget exited with code {rc}",
                )
                append_log(f"✗ wget exited with code {rc}")

        # Give uploader a moment to pick up the file (it polls every 10s)
        # We don't wait for the upload itself to finish — we just wait for download,
        # then immediately start the next download. Uploader runs in parallel.
        # (User wanted: "one should download fully than other start" — that's what we do.)
        set_current(status="idle")
        work_queue.task_done()


# Start the worker thread once at module import
_worker_thread = threading.Thread(target=_download_worker, daemon=True)
_worker_thread.start()


def filename_from_url(url):
    """Extract a reasonable filename from a URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    name = path.split("/")[-1]
    name = name.split("?")[0]
    if not name or "." not in name:
        name = f"download_{int(datetime.now().timestamp())}.mp4"
    return name


# ============================================================
# DATABASE QUERIES
# ============================================================
def get_db_stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM anime")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT anime_name) FROM anime")
        distinct = c.fetchone()[0]
        conn.close()
        return total, distinct
    except:
        return 0, 0

def get_db_rows(limit=100):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT id, anime_name, episode_number, byse_url, uploaded_at
            FROM anime ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = []
        for r in c.fetchall():
            rows.append({
                "id": r[0],
                "anime_name": r[1],
                "episode_number": r[2],
                "byse_url": r[3],
                "uploaded_at": r[4],
            })
        conn.close()
        return rows
    except Exception as e:
        print(f"DB error: {e}")
        return []


# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def index():
    # Add cache-control headers to force browser to NEVER cache this page
    resp = make_response(render_template_string(HTML_PAGE))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@app.route("/api/stats")
def api_stats():
    total, distinct = get_db_stats()
    with queue_lock:
        queue_count = sum(1 for q in queue if q["status"] == "downloading")
        queued_count = sum(1 for q in queue if q["status"] == "queued")
    return jsonify({
        "total_uploads": total,
        "total_anime": distinct,
        "queue_count": queue_count,
        "queued_count": queued_count,
    })

@app.route("/api/queue")
def api_queue():
    with queue_lock:
        q = list(queue)
    return jsonify({"queue": q})

@app.route("/api/current")
def api_current():
    """Return the current download/upload state for the live progress widget."""
    with current_lock:
        cur = dict(current_download)
    # Compute how many downloads are still queued
    with queue_lock:
        queued_count = sum(1 for x in queue if x["status"] == "queued")
        downloading_count = sum(1 for x in queue if x["status"] == "downloading")
        done_count = sum(1 for x in queue if x["status"] == "done")
        failed_count = sum(1 for x in queue if x["status"] == "failed")
    cur["queue_stats"] = {
        "queued": queued_count,
        "downloading": downloading_count,
        "done": done_count,
        "failed": failed_count,
    }
    return jsonify(cur)

@app.route("/api/database")
def api_database():
    return jsonify({"rows": get_db_rows()})

# ============================================================
# MEDIA WATCHER STATE ENDPOINT
# ============================================================
MEDIA_WATCHER_STATE_FILE = "/var/lib/luffytv/media-watcher-state.json"

@app.route("/api/media-watcher")
def api_media_watcher():
    """Return the current state of the media-watcher service."""
    try:
        with open(MEDIA_WATCHER_STATE_FILE, "r") as f:
            data = json.load(f)
        return jsonify(data)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({
            "currently_uploading": None,
            "queue": [],
            "recently_completed": [],
            "scanning": False,
            "last_scan_at": None,
            "stats": {
                "total_queued_today": 0,
                "total_completed_today": 0,
                "total_skipped_already_uploaded": 0,
            },
            "online": False,
        })

# ============================================================
# MANGA WATCHER STATE ENDPOINT
# ============================================================
MANGA_WATCHER_STATE_FILE = "/var/lib/luffytv/manga-watcher-state.json"
MANGA_ORCHESTRATOR_STATE_FILE = "/var/lib/luffytv/manga-orchestrator-state.json"
MANGA_QUEUE_FILE = "/var/lib/luffytv/manga-queue.json"
MANGA_SINGLE_STATE_FILE = "/var/lib/luffytv/manga-single-state.json"
MANGA_DB_FILE = "/var/lib/luffytv/manga.db"
MANGA_JSON_FILE = "/var/lib/luffytv/manga.json"

@app.route("/api/manga-watcher")
def api_manga_watcher():
    """Return orchestrator state in a watcher-compatible format so the admin panel works."""
    try:
        with open(MANGA_ORCHESTRATOR_STATE_FILE, "r") as f:
            data = json.load(f)
        current_manga = data.get("current_manga")
        current_chapter = data.get("current_chapter")
        stats = data.get("stats", {})
        completed = data.get("completed_manga", [])
        in_progress = data.get("in_progress_manga", [])
        if current_manga:
            cur = {
                "filename": f"{current_manga} - {current_chapter or '.'}",
                "manga": current_manga,
                "chapter": current_chapter,
                "started_at": data.get("started_at"),
                "size_bytes": 0,
            }
        else:
            cur = None
        return jsonify({
            "currently_uploading": cur,
            "queue": [],
            "recently_completed": [{"filename": m, "completed_at": None} for m in completed[-10:]],
            "scanning": False,
            "last_scan_at": data.get("started_at"),
            "active_manga": current_manga,
            "current_chapter": current_chapter,
            "completed_manga": completed,
            "in_progress_manga": in_progress,
            "stats": {
                "total_queued_today": 0,
                "total_completed_today": stats.get("chapters_uploaded", 0),
                "total_skipped": 0,
                "total_pages_uploaded": stats.get("pages_uploaded", 0),
            },
            "online": True,
        })
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return jsonify({
            "currently_uploading": None,
            "queue": [],
            "recently_completed": [],
            "scanning": False,
            "last_scan_at": None,
            "stats": {
                "total_queued_today": 0,
                "total_completed_today": 0,
                "total_skipped": 0,
            },
            "online": False,
            "error": str(e),
        })

# ============================================================
# MANGA SERIAL SCRAPE ENDPOINT
# ============================================================
import subprocess as _subprocess

# Track if scraper is currently running
_manga_scraper_running = {"active": False, "started_at": None, "anilist_ids": []}

def _run_manga_scraper_background(anilist_ids_str):
    """Background thread: runs the orchestrator which:
    1. Scrapes each manga (downloads all chapters as ZIPs)
    2. Waits for the watcher + uploader to process each chapter
    3. Verifies all chapters are in manga.db
    4. Deletes local files after verification
    5. Moves to next manga
    """
    global _manga_scraper_running
    _manga_scraper_running["active"] = True
    _manga_scraper_running["started_at"] = datetime.now().isoformat()
    _manga_scraper_running["anilist_ids"] = [x.strip() for x in anilist_ids_str.split(",") if x.strip()]
    try:
        proc = _subprocess.Popen(
            ["python3", "/root/luffytv-manga-scraper/orchestrator.py", anilist_ids_str],
            stdout=_subprocess.PIPE,
            stderr=_subprocess.STDOUT,
            text=True,
        )
        # Wait for completion (this runs in background thread, doesn't block Flask)
        proc.wait()
    except Exception as e:
        print(f"Manga scraper background error: {e}")
    finally:
        _manga_scraper_running["active"] = False
        _manga_scraper_running["started_at"] = None

@app.route("/api/manga/scrape", methods=["POST"])
def api_manga_scrape():
    """Start the manga serial scraper with the given AniList IDs.
    Runs in background — the caller gets immediate response + watches progress via /api/manga-watcher.
    """
    if _manga_scraper_running["active"]:
        return jsonify({
            "success": False,
            "error": "A manga scrape is already running. Wait for it to finish before starting another.",
            "running_since": _manga_scraper_running.get("started_at"),
        })

    data = request.get_json()
    if not data or "anilist_ids" not in data:
        return jsonify({"success": False, "error": "Missing 'anilist_ids' field"}), 400

    ids_text = str(data["anilist_ids"]).strip()
    if not ids_text:
        return jsonify({"success": False, "error": "No AniList IDs provided"}), 400

    # Parse + validate IDs
    ids = []
    for x in ids_text.split(","):
        x = x.strip()
        if x.isdigit():
            ids.append(x)
        elif x:
            return jsonify({"success": False, "error": f"Invalid AniList ID: '{x}' — must be a number"}), 400

    if not ids:
        return jsonify({"success": False, "error": "No valid AniList IDs found"}), 400

    # Start scraper in background thread
    t = threading.Thread(
        target=_run_manga_scraper_background,
        args=(ids_text,),
        daemon=True,
    )
    t.start()

    return jsonify({
        "success": True,
        "submitted": len(ids),
        "anilist_ids": ids,
        "message": f"Serial scrape started for {len(ids)} manga: {', '.join(ids)}. Watch the 'Currently Uploading Manga' card for live progress.",
    })

@app.route("/api/manga/scrape/status")
def api_manga_scrape_status():
    """Check if the manga scraper is currently running."""
    return jsonify({
        "active": _manga_scraper_running["active"],
        "started_at": _manga_scraper_running.get("started_at"),
        "anilist_ids": _manga_scraper_running.get("anilist_ids", []),
    })

@app.route("/api/manga/stats")
def api_manga_stats():
    """Return manga DB stats: total manga, chapters, pages."""
    try:
        conn = sqlite3.connect(MANGA_DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM manga")
        total_pages = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT manga_name) FROM manga")
        total_manga = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT manga_name || chapter_number) FROM manga")
        total_chapters = c.fetchone()[0]
        conn.close()
        return jsonify({
            "total_manga": total_manga,
            "total_chapters": total_chapters,
            "total_pages": total_pages,
        })
    except Exception as e:
        return jsonify({
            "total_manga": 0,
            "total_chapters": 0,
            "total_pages": 0,
            "error": str(e),
        })

@app.route("/api/manga/db")
def api_manga_db():
    """Return recent manga uploads from DB."""
    try:
        conn = sqlite3.connect(MANGA_DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT id, manga_name, chapter_number, page_number, COALESCE(NULLIF(catbox_url, ''), image_url) AS image_url, uploaded_at
            FROM manga ORDER BY id DESC LIMIT 500
        """)
        rows = []
        for r in c.fetchall():
            rows.append({
                "id": r[0], "manga_name": r[1], "chapter_number": r[2],
                "page_number": r[3], "image_url": r[4], "uploaded_at": r[5],
            })
        conn.close()
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"rows": [], "error": str(e)})

@app.route("/api/manga/series")
def api_manga_series():
    """Return list of all manga series with chapter + page counts (grouped view)."""
    try:
        conn = sqlite3.connect(MANGA_DB_FILE)
        c = conn.cursor()
        # Check if anilist_id column exists
        c.execute("PRAGMA table_info(manga)")
        cols = [col[1] for col in c.fetchall()]
        has_anilist = "anilist_id" in cols
        if has_anilist:
            c.execute("""
                SELECT manga_name, anilist_id,
                       COUNT(DISTINCT chapter_number), COUNT(*),
                       MIN(uploaded_at), MAX(uploaded_at)
                FROM manga GROUP BY manga_name ORDER BY MAX(uploaded_at) DESC
            """)
        else:
            c.execute("""
                SELECT manga_name, NULL,
                       COUNT(DISTINCT chapter_number), COUNT(*),
                       MIN(uploaded_at), MAX(uploaded_at)
                FROM manga GROUP BY manga_name ORDER BY MAX(uploaded_at) DESC
            """)
        series = []
        for r in c.fetchall():
            series.append({
                "manga_name": r[0],
                "anilist_id": r[1],
                "chapter_count": r[2],
                "page_count": r[3],
                "first_upload": r[4],
                "last_upload": r[5],
            })
        conn.close()
        return jsonify({
            "total_series": len(series),
            "total_chapters": sum(s["chapter_count"] for s in series),
            "total_pages": sum(s["page_count"] for s in series),
            "series": series,
        })
    except Exception as e:
        return jsonify({"total_series": 0, "series": [], "error": str(e)})


@app.route("/api/manga/json")
def api_manga_json():
    """Return manga data rebuilt fresh from SQLite DB (not the stale JSON mirror file).

    The JSON structure is compatible with the existing Manga Library view:
    {
      "Hajime no Ippo": {
        "anilist_id": 30007,
        "chapters": {
          "C163": { "pages": { "1": "https://iili.io/...", "2": "..." } },
          "C164": { "pages": { ... } },
          ...
        }
      },
      ...
    }
    """
    try:
        conn = sqlite3.connect(MANGA_DB_FILE)
        c = conn.cursor()
        # Check if anilist_id column exists
        c.execute("PRAGMA table_info(manga)")
        cols = [col[1] for col in c.fetchall()]
        has_anilist = "anilist_id" in cols

        # Get all rows ordered by manga_name, chapter_number, page_number
        if has_anilist:
            c.execute("""
                SELECT manga_name, anilist_id, chapter_number, page_number, COALESCE(NULLIF(catbox_url, ''), image_url) AS image_url
                FROM manga
                ORDER BY manga_name, chapter_number, page_number
            """)
        else:
            c.execute("""
                SELECT manga_name, NULL, chapter_number, page_number, COALESCE(NULLIF(catbox_url, ''), image_url) AS image_url
                FROM manga
                ORDER BY manga_name, chapter_number, page_number
            """)
        result = {}
        row_count = 0
        for row in c.fetchall():
            manga_name = row[0]
            anilist_id = row[1]
            chapter_number = row[2]
            page_number = row[3]
            image_url = row[4]
            row_count += 1
            if manga_name not in result:
                result[manga_name] = {
                    "anilist_id": anilist_id,
                    "chapters": {}
                }
            if anilist_id and not result[manga_name].get("anilist_id"):
                result[manga_name]["anilist_id"] = anilist_id
            if chapter_number not in result[manga_name]["chapters"]:
                result[manga_name]["chapters"][chapter_number] = {"pages": {}}
            result[manga_name]["chapters"][chapter_number]["pages"][str(page_number)] = image_url
        conn.close()
        print(f"[api_manga_json] rebuilt from DB: {len(result)} series, {row_count} rows")
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


# ============================================================
# JSON DATABASE ENDPOINTS
# ============================================================
def load_json_db():
    """Load the JSON DB. Returns empty dict if missing."""
    try:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"JSON load error: {e}")
    return {}

@app.route("/api/json")
def api_json():
    """Return the raw JSON database."""
    return jsonify(load_json_db())

@app.route("/api/json/anime/<path:anime_name>")
def api_json_anime(anime_name):
    """Return one anime's record from the JSON DB."""
    data = load_json_db()
    return jsonify(data.get(anime_name, {}))

@app.route("/api/json/search")
def api_json_search():
    """Search the JSON DB by anime name, language, or season.
    Example: /api/json/search?q=mob&lang=Hindi&season=S01
    """
    q = (request.args.get("q") or "").strip().lower()
    lang = (request.args.get("lang") or "").strip().lower()
    season = (request.args.get("season") or "").strip().upper()
    data = load_json_db()
    results = []
    for anime_name, anime in data.items():
        if q and q not in anime_name.lower():
            continue
        for season_key, season_obj in anime.get("seasons", {}).items():
            if season and season != season_key:
                continue
            for ep_key, ep in season_obj.get("episodes", {}).items():
                if lang:
                    langs = [l.lower() for l in ep.get("languages", [])]
                    if lang not in langs:
                        continue
                results.append({
                    "anime_name": anime_name,
                    "season": season_key,
                    "episode": ep_key,
                    "languages": ep.get("languages", []),
                    "byse_url": ep.get("byse_url"),
                    "file_name": ep.get("file_name"),
                    "uploaded_at": ep.get("uploaded_at"),
                })
    return jsonify({"count": len(results), "results": results})


JSON_VIEW_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LuffyTV - JSON Database Viewer</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E📄%3C/text%3E%3C/svg%3E">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --bg: #000; --surface: #0a0a0a; --surface-2: #141414;
    --border: #262626; --text: #fff; --text-2: #9ca3af; --text-3: #6b7280;
    --accent: #FF4D6A; --cyan: #00E5FF; --purple: #A855F7; --green: #22c55e;
  }
  body {
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    min-height: 100vh; padding: 24px;
  }
  .container { max-width: 1300px; margin: 0 auto; }
  .header {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 32px;
  }
  .logo {
    font-size: 24px; font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle { color: var(--text-2); font-size: 14px; margin-top: 4px; }
  .toolbar {
    display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 16px;
  }
  .btn {
    background: var(--accent); color: white; border: none;
    padding: 10px 20px; border-radius: 8px; font-size: 13px;
    font-weight: 600; cursor: pointer; transition: all 0.15s; text-decoration: none;
    display: inline-block;
  }
  .btn:hover { background: #e63e58; }
  .btn-secondary {
    background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
    padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all 0.15s; text-decoration: none; display: inline-block;
  }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
  .btn-secondary.active { background: var(--accent); color: white; border-color: var(--accent); }
  .search-input {
    flex: 1; min-width: 200px;
    background: var(--surface-2); color: var(--text);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 10px 14px; font-size: 14px; font-family: inherit;
  }
  .search-input:focus { outline: none; border-color: var(--accent); }
  .stats {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin-bottom: 24px;
  }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 18px;
  }
  .stat-value { font-size: 32px; font-weight: 800; }
  .stat-label { font-size: 12px; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 24px;
  }
  .card h2 {
    font-size: 18px; font-weight: 700; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }
  .summary { color: var(--text-2); font-size: 14px; margin-bottom: 16px; }
  .anime-card {
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: 10px; padding: 20px; margin-bottom: 16px;
  }
  .anime-title {
    font-size: 20px; font-weight: 700; color: var(--text);
    display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
  }
  .anime-title .emoji { font-size: 22px; }
  .season-row {
    display: flex; align-items: flex-start; gap: 12px; padding: 12px 0;
    border-top: 1px solid var(--border);
  }
  .season-label {
    font-family: 'SF Mono', monospace; font-size: 13px; font-weight: 700;
    color: var(--cyan); background: rgba(0, 229, 255, 0.1);
    padding: 4px 12px; border-radius: 6px; min-width: 60px; text-align: center;
  }
  .episodes-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 10px; flex: 1;
  }
  .episode-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 12px; transition: all 0.15s;
  }
  .episode-card:hover { border-color: var(--accent); }
  .ep-title {
    font-family: monospace; font-size: 13px; font-weight: 700; color: var(--cyan);
    margin-bottom: 6px;
  }
  .ep-url {
    display: block; color: var(--accent); font-size: 12px;
    text-decoration: none; word-break: break-all; margin-bottom: 6px;
  }
  .ep-url:hover { text-decoration: underline; }
  .lang-tags { margin-top: 6px; }
  .lang-tag {
    display: inline-block; padding: 2px 8px; border-radius: 10px;
    font-size: 10px; font-weight: 700; margin-right: 4px; text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .lang-tag.Hindi { background: rgba(255, 77, 106, 0.15); color: var(--accent); }
  .lang-tag.Japanese { background: rgba(0, 229, 255, 0.15); color: var(--cyan); }
  .lang-tag.English { background: rgba(34, 197, 94, 0.15); color: var(--green); }
  .lang-tag.Dual { background: rgba(168, 85, 247, 0.15); color: var(--purple); }
  .lang-tag.Multi { background: rgba(168, 85, 247, 0.15); color: var(--purple); }
  .lang-tag.Unknown { background: rgba(156, 163, 175, 0.15); color: var(--text-2); }
  .ep-meta { color: var(--text-3); font-size: 11px; }
  .empty { color: var(--text-3); text-align: center; padding: 40px; font-size: 14px; }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white; border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="logo">📄 LuffyTV JSON Database</div>
      <div class="subtitle">Anime &rarr; Season &rarr; Episode &rarr; Language</div>
    </div>
    <div>
      <a href="/" class="btn-secondary">&larr; Back to Submitter</a>
      &nbsp;
      <a href="/api/json" target="_blank" class="btn-secondary">⚡ Raw JSON</a>
    </div>
  </div>

  <div class="stats" id="stats">
    <div class="stat-card"><div class="stat-value" id="totalAnime">-</div><div class="stat-label">Anime Series</div></div>
    <div class="stat-card"><div class="stat-value" id="totalSeasons">-</div><div class="stat-label">Seasons</div></div>
    <div class="stat-card"><div class="stat-value" id="totalEpisodes">-</div><div class="stat-label">Episodes</div></div>
    <div class="stat-card"><div class="stat-value" id="totalHindi">-</div><div class="stat-label">Hindi Episodes</div></div>
  </div>

  <div class="card">
    <h2>🔍 Filter</h2>
    <div class="toolbar">
      <input type="text" id="searchInput" class="search-input" placeholder="Search by anime name...">
      <button class="btn-secondary" data-lang-filter="">All Languages</button>
      <button class="btn-secondary" data-lang-filter="Hindi">Hindi</button>
      <button class="btn-secondary" data-lang-filter="Japanese">Japanese</button>
      <button class="btn-secondary" data-lang-filter="English">English</button>
    </div>
  </div>

  <div class="card">
    <h2>📚 Database</h2>
    <div class="summary" id="summary">Loading...</div>
    <div id="animeList">
      <div class="empty"><span class="spinner"></span>Loading JSON database...</div>
    </div>
  </div>
</div>

<script>
let allData = {};
let currentLangFilter = '';

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

function fmtSize(bytes) {
  if (!bytes) return '-';
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) return mb.toFixed(1) + ' MB';
  return (mb / 1024).toFixed(2) + ' GB';
}

function renderAnimeList() {
  const search = document.getElementById('searchInput').value.trim().toLowerCase();
  const el = document.getElementById('animeList');
  const animeNames = Object.keys(allData).sort();

  const filtered = animeNames.filter(name => !search || name.toLowerCase().includes(search));

  if (filtered.length === 0) {
    el.innerHTML = '<div class="empty">No anime found matching your filter</div>';
    document.getElementById('summary').textContent = '0 anime series';
    return;
  }

  let totalEps = 0;
  let totalSeasons = 0;

  let html = '';
  for (const animeName of filtered) {
    const anime = allData[animeName];
    const seasons = anime.seasons || {};
    const seasonKeys = Object.keys(seasons).sort();
    totalSeasons += seasonKeys.length;

    let seasonHtml = '';
    for (const seasonKey of seasonKeys) {
      const season = seasons[seasonKey];
      const episodes = season.episodes || {};
      const epKeys = Object.keys(episodes).sort();
      let epHtml = '';
      let epsShown = 0;
      for (const epKey of epKeys) {
        const ep = episodes[epKey];
        // Apply language filter
        if (currentLangFilter) {
          const langs = (ep.languages || []).map(l => l.toLowerCase());
          if (!langs.includes(currentLangFilter.toLowerCase())) continue;
        }
        epsShown++;
        totalEps++;
        const langTags = (ep.languages || []).map(l => `<span class="lang-tag ${escapeHtml(l)}">${escapeHtml(l)}</span>`).join('');
        epHtml += `
          <div class="episode-card">
            <div class="ep-title">${escapeHtml(epKey)}</div>
            <a href="${escapeHtml(ep.byse_url)}" target="_blank" class="ep-url">${escapeHtml(ep.byse_url)}</a>
            <div class="lang-tags">${langTags}</div>
            <div class="ep-meta">${fmtSize(ep.file_size)} &middot; ${escapeHtml((ep.uploaded_at || '').substring(0, 16))}</div>
          </div>
        `;
      }
      if (epsShown === 0) continue;
      seasonHtml += `
        <div class="season-row">
          <div class="season-label">${escapeHtml(seasonKey)}</div>
          <div class="episodes-grid">${epHtml}</div>
        </div>
      `;
    }
    if (!seasonHtml) continue;
    html += `
      <div class="anime-card">
        <div class="anime-title"><span class="emoji">🎬</span> ${escapeHtml(animeName)}</div>
        ${seasonHtml}
      </div>
    `;
  }

  if (!html) {
    el.innerHTML = '<div class="empty">No episodes match your filter</div>';
  } else {
    el.innerHTML = html;
  }
  document.getElementById('summary').textContent =
    `${filtered.length} anime series &middot; ${totalSeasons} seasons &middot; ${totalEps} episodes shown`;
}

function renderStats() {
  const animeNames = Object.keys(allData);
  let totalSeasons = 0, totalEps = 0, totalHindi = 0;
  for (const name of animeNames) {
    const seasons = allData[name].seasons || {};
    totalSeasons += Object.keys(seasons).length;
    for (const sk of Object.keys(seasons)) {
      const eps = seasons[sk].episodes || {};
      for (const ek of Object.keys(eps)) {
        totalEps++;
        if ((eps[ek].languages || []).includes('Hindi')) totalHindi++;
      }
    }
  }
  document.getElementById('totalAnime').textContent = animeNames.length;
  document.getElementById('totalSeasons').textContent = totalSeasons;
  document.getElementById('totalEpisodes').textContent = totalEps;
  document.getElementById('totalHindi').textContent = totalHindi;
}

async function loadJson() {
  try {
    const r = await fetch('/api/json');
    allData = await r.json();
    renderStats();
    renderAnimeList();
  } catch (e) {
    document.getElementById('animeList').innerHTML =
      '<div class="empty">Failed to load JSON: ' + escapeHtml(e.message) + '</div>';
  }
}

document.getElementById('searchInput').addEventListener('input', renderAnimeList);
document.querySelectorAll('[data-lang-filter]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-lang-filter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentLangFilter = btn.dataset.langFilter;
    renderAnimeList();
  });
});
// Default: All Languages active
document.querySelector('[data-lang-filter=""]').classList.add('active');

loadJson();
setInterval(loadJson, 5000);
</script>
</body>
</html>
'''

@app.route("/json")
def json_view():
    return render_template_string(JSON_VIEW_PAGE)


# ============================================================
# MANGA DB VIEWER PAGE
# ============================================================
MANGA_VIEW_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LuffyTV - Manga Library</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E📖%3C/text%3E%3C/svg%3E">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --bg: #000; --surface: #0a0a0a; --surface-2: #141414;
    --border: #262626; --text: #fff; --text-2: #9ca3af; --text-3: #6b7280;
    --accent: #FF4D6A; --cyan: #00E5FF; --purple: #A855F7; --green: #22c55e;
  }
  body {
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    min-height: 100vh; padding: 24px;
  }
  .container { max-width: 1400px; margin: 0 auto; }
  .header {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 32px;
  }
  .logo {
    font-size: 24px; font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle { color: var(--text-2); font-size: 14px; margin-top: 4px; }
  .btn-secondary {
    background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
    padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; transition: all 0.15s; text-decoration: none; display: inline-block;
  }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }
  .stats {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin-bottom: 24px;
  }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 18px;
  }
  .stat-value { font-size: 32px; font-weight: 800; }
  .stat-label { font-size: 12px; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 24px;
  }
  .card h2 { font-size: 18px; font-weight: 700; margin-bottom: 16px; }
  .manga-card {
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: 10px; padding: 20px; margin-bottom: 16px;
  }
  .manga-title { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 8px; }
  .manga-meta { color: var(--text-2); font-size: 13px; margin-bottom: 12px; }
  .chapter-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 8px;
  }
  .chapter-link {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 12px; text-align: center;
    color: var(--cyan); text-decoration: none; font-size: 13px; font-weight: 600;
    transition: all 0.15s;
  }
  .chapter-link:hover { border-color: var(--accent); color: var(--accent); }
  .chapter-pages {
    margin-top: 12px; display: none;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px;
  }
  .chapter-pages.show { display: grid; }
  .page-thumb {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 6px; overflow: hidden;
  }
  .page-thumb img { width: 100%; height: auto; display: block; }
  .page-thumb .label {
    padding: 4px 8px; font-size: 11px; color: var(--text-2); text-align: center;
    border-top: 1px solid var(--border);
  }
  .empty { color: var(--text-3); text-align: center; padding: 40px; font-size: 14px; }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white; border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle; margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="logo">📖 LuffyTV Manga Library</div>
      <div class="subtitle">Browse uploaded manga + chapters + pages</div>
    </div>
    <div>
      <a href="/" class="btn-secondary">&larr; Back to Admin</a>
      &nbsp;
      <a href="/api/manga/json" target="_blank" class="btn-secondary">⚡ Raw JSON</a>
    </div>
  </div>

  <div class="stats" id="stats">
    <div class="stat-card"><div class="stat-value" id="totalManga">-</div><div class="stat-label">Manga Series</div></div>
    <div class="stat-card"><div class="stat-value" id="totalChapters">-</div><div class="stat-label">Chapters</div></div>
    <div class="stat-card"><div class="stat-value" id="totalPages">-</div><div class="stat-label">Pages Uploaded</div></div>
  </div>

  <div class="card">
    <h2>📚 Manga Library</h2>
    <div id="mangaList">
      <div class="empty"><span class="spinner"></span>Loading manga library...</div>
    </div>
  </div>
</div>

<script>
function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

async function loadStats() {
  try {
    const r = await fetch('/api/manga/stats');
    const d = await r.json();
    document.getElementById('totalManga').textContent = d.total_manga || 0;
    document.getElementById('totalChapters').textContent = d.total_chapters || 0;
    document.getElementById('totalPages').textContent = d.total_pages || 0;
  } catch (e) { console.error(e); }
}

async function loadManga() {
  try {
    const r = await fetch('/api/manga/json');
    const data = await r.json();
    const el = document.getElementById('mangaList');
    const mangaNames = Object.keys(data).sort();
    if (mangaNames.length === 0) {
      el.innerHTML = '<div class="empty">No manga uploaded yet. Run the scraper to download chapters.</div>';
      return;
    }
    let html = '';
    for (const name of mangaNames) {
      const manga = data[name];
      const chapters = manga.chapters || {};
      const chapterKeys = Object.keys(chapters).sort();
      const anilistBadge = manga.anilist_id
        ? `<a href="https://anilist.co/manga/${manga.anilist_id}" target="_blank" style="color: var(--purple); text-decoration: none; font-size: 12px;">AniList: ${manga.anilist_id}</a>`
        : '';
      let chapterLinks = '';
      for (const chKey of chapterKeys) {
        chapterLinks += `<a href="#" class="chapter-link" data-manga="${escapeHtml(name)}" data-chapter="${escapeHtml(chKey)}">${escapeHtml(chKey)} (${Object.keys(chapters[chKey].pages || {}).length}p)</a>`;
      }
      html += `
        <div class="manga-card">
          <div class="manga-title">${escapeHtml(name)}</div>
          <div class="manga-meta">${chapterKeys.length} chapters • ${anilistBadge}</div>
          <div class="chapter-grid">${chapterLinks}</div>
          <div class="chapter-pages" id="pages-${escapeHtml(name).replace(/[^a-zA-Z0-9]/g, '_')}_${escapeHtml(chapterKeys[0] || '').replace(/[^a-zA-Z0-9]/g, '_')}"></div>
        </div>`;
    }
    el.innerHTML = html;
    // Wire up chapter links
    document.querySelectorAll('.chapter-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const mangaName = link.dataset.manga;
        const chapter = link.dataset.chapter;
        const pages = data[mangaName].chapters[chapter].pages || {};
        const pageEntries = Object.entries(pages).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
        if (pageEntries.length === 0) return;
        // Open pages in a new window/tab
        const w = window.open('', '_blank');
        w.document.write(`
          <html><head><title>${escapeHtml(mangaName)} - ${escapeHtml(chapter)}</title>
          <style>
            body { background: #000; color: #fff; font-family: sans-serif; margin: 0; padding: 20px; }
            h1 { color: #00E5FF; margin-bottom: 20px; }
            img { max-width: 100%; display: block; margin: 0 auto 10px; }
            .page-num { text-align: center; color: #9ca3af; font-size: 12px; margin-bottom: 20px; }
          </style></head><body>
          <h1>${escapeHtml(mangaName)} — ${escapeHtml(chapter)}</h1>
          ${pageEntries.map(([n, url]) => `
            <div class="page-num">Page ${n}</div>
            <img src="${escapeHtml(url)}" loading="lazy" />
          `).join('')}
          </body></html>
        `);
        w.document.close();
      });
    });
  } catch (e) {
    document.getElementById('mangaList').innerHTML = '<div class="empty">Failed to load: ' + escapeHtml(e.message) + '</div>';
  }
}

loadStats();
loadManga();
setInterval(loadStats, 10000);
</script>
</body>
</html>
'''

@app.route("/manga")
def manga_view():
    return render_template_string(MANGA_VIEW_PAGE)


@app.route("/api/submit", methods=["POST"])
def api_submit():
    """Submit one or more URLs to download."""
    data = request.get_json()
    if not data or "urls" not in data:
        return jsonify({"success": False, "error": "Missing 'urls' field"}), 400

    urls_text = data["urls"].strip()
    if not urls_text:
        return jsonify({"success": False, "error": "No URLs provided"}), 400

    urls = [u.strip() for u in urls_text.split("\n") if u.strip()]

    submitted = 0
    skipped = 0
    skipped_filenames = []
    for url in urls:
        if not url.startswith(("http://", "https://")):
            continue

        filename = filename_from_url(url)

        # Dedup check — skip if filename already in queue or currently downloading
        with queue_lock:
            already_queued = any(
                (item["url"] == url or
                 (item["filename"] == filename and item["status"] in ("queued", "downloading")))
                for item in queue
            )
        if already_queued:
            skipped += 1
            skipped_filenames.append(filename)
            continue

        with open(SUBMITTED_URLS_LOG, "a") as f:
            f.write(f"{datetime.now().isoformat()} | SUBMITTED | {filename} | {url}\n")

        # download_in_background now also deduplicates internally as a safety net
        ok = download_in_background(url, filename)
        if ok:
            submitted += 1
        else:
            skipped += 1
            skipped_filenames.append(filename)

    if submitted == 0 and skipped > 0:
        return jsonify({
            "success": True,
            "submitted": 0,
            "skipped": skipped,
            "skipped_filenames": skipped_filenames,
            "message": f"All {skipped} URL(s) were already in the queue.",
        })

    if submitted == 0:
        return jsonify({"success": False, "error": "No valid URLs found"})

    msg = f"{submitted} URL(s) submitted."
    if skipped > 0:
        msg += f" {skipped} duplicate(s) skipped."
    msg += " Downloads will start when the queue gets to them."

    return jsonify({
        "success": True,
        "submitted": submitted,
        "skipped": skipped,
        "skipped_filenames": skipped_filenames,
        "message": msg,
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


if __name__ == "__main__":
    print("=" * 60)
    print("🏴‍☠️ LuffyTV URL Submitter")
    print(f"📁 Download dir: {DOWNLOAD_DIR}")
    print(f"💾 SQLite DB:    {DB_FILE}")
    print(f"📄 JSON DB:     {JSON_FILE}")
    print(f"🌐 Listening on: http://0.0.0.0:{PORT}")
    print(f"📊 JSON Viewer:  http://0.0.0.0:{PORT}/json")
    print("=" * 60)
# ============================================================
# MANGA PIPELINE
# ============================================================


@app.route("/manga/series")
def manga_series_view():
    """Dedicated page showing all manga series grouped."""
    return '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>Manga Series Overview - LuffyTV Admin</title>\n<style>\n* { box-sizing: border-box; margin: 0; padding: 0; }\nbody { background: #0a0a0a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; }\n.container { max-width: 1400px; margin: 0 auto; }\nh1 { color: #fff; margin-bottom: 8px; font-size: 24px; }\n.subtitle { color: #888; margin-bottom: 24px; }\n.stats-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }\n.stat-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; }\n.stat-card .label { color: #888; font-size: 12px; margin-bottom: 4px; }\n.stat-card .value { color: #fff; font-size: 28px; font-weight: 700; }\n.stat-card .value.accent { color: #10b981; }\n.back-link { display: inline-block; color: #60a5fa; text-decoration: none; margin-bottom: 16px; padding: 8px 12px; border: 1px solid #2a2a2a; border-radius: 6px; font-size: 13px; }\n.back-link:hover { background: #1a1a1a; }\ntable { width: 100%; border-collapse: collapse; background: #1a1a1a; border-radius: 8px; overflow: hidden; }\nth { background: #2a2a2a; color: #fff; text-align: left; padding: 12px 16px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }\ntd { padding: 12px 16px; border-top: 1px solid #2a2a2a; font-size: 14px; }\ntr:hover { background: #1f1f1f; }\n.manga-name { color: #fff; font-weight: 500; }\n.anilist-id { color: #60a5fa; font-family: monospace; font-size: 12px; }\n.chapter-count, .page-count { color: #10b981; font-weight: 600; }\n.date-cell { color: #888; font-size: 12px; }\n.actions a { color: #f59e0b; text-decoration: none; font-size: 12px; padding: 4px 8px; border: 1px solid #2a2a2a; border-radius: 4px; }\n.actions a:hover { background: #1f1f1f; }\n</style>\n</head>\n<body>\n<div class="container">\n  <a href="/manga" class="back-link">&larr; Back to Manga Admin</a>\n  <h1>📚 Manga Series Overview</h1>\n  <p class="subtitle">All series with chapter + page counts (grouped from manga.db)</p>\n\n  <div class="stats-bar">\n    <div class="stat-card"><div class="label">Total Series</div><div class="value accent" id="totalSeries">—</div></div>\n    <div class="stat-card"><div class="label">Total Chapters</div><div class="value" id="totalChapters">—</div></div>\n    <div class="stat-card"><div class="label">Total Pages</div><div class="value" id="totalPages">—</div></div>\n    <div class="stat-card"><div class="label">Latest Upload</div><div class="value" style="font-size: 14px;" id="latestUpload">—</div></div>\n  </div>\n\n  <table>\n    <thead>\n      <tr>\n        <th>#</th>\n        <th>Manga Name</th>\n        <th>AniList ID</th>\n        <th>Chapters</th>\n        <th>Pages</th>\n        <th>First Upload</th>\n        <th>Last Upload</th>\n        <th>Actions</th>\n      </tr>\n    </thead>\n    <tbody id="seriesRows">\n      <tr><td colspan="8" style="text-align: center; padding: 40px; color: #888;">Loading...</td></tr>\n    </tbody>\n  </table>\n</div>\n<script>\nasync function loadSeries() {\n  try {\n    const res = await fetch(\'/api/manga/series\');\n    const data = await res.json();\n    document.getElementById(\'totalSeries\').textContent = data.total_series || 0;\n    document.getElementById(\'totalChapters\').textContent = data.total_chapters || 0;\n    document.getElementById(\'totalPages\').textContent = data.total_pages || 0;\n    const series = data.series || [];\n    if (series.length === 0) {\n      document.getElementById(\'seriesRows\').innerHTML = \'<tr><td colspan="8" style="text-align:center;padding:40px;color:#888;">No series in DB yet</td></tr>\';\n      return;\n    }\n    document.getElementById(\'latestUpload\').textContent = series[0].last_upload || \'—\';\n    document.getElementById(\'seriesRows\').innerHTML = series.map((s, i) => {\n      const anilistUrl = s.anilist_id ? \'https://anilist.co/manga/\' + s.anilist_id : \'#\';\n      return \'<tr>\' +\n        \'<td>\' + (i + 1) + \'</td>\' +\n        \'<td class="manga-name">\' + escapeHtml(s.manga_name) + \'</td>\' +\n        \'<td class="anilist-id">\' + (s.anilist_id || \'—\') + \'</td>\' +\n        \'<td class="chapter-count">\' + s.chapter_count + \'</td>\' +\n        \'<td class="page-count">\' + s.page_count + \'</td>\' +\n        \'<td class="date-cell">\' + (s.first_upload || \'—\') + \'</td>\' +\n        \'<td class="date-cell">\' + (s.last_upload || \'—\') + \'</td>\' +\n        \'<td class="actions">\' + (s.anilist_id ? \'<a href="\' + anilistUrl + \'" target="_blank">AniList ↗</a>\' : \'\') + \'</td>\' +\n      \'</tr>\';\n    }).join(\'\');\n  } catch (e) {\n    document.getElementById(\'seriesRows\').innerHTML = \'<tr><td colspan="8" style="text-align:center;padding:40px;color:#f87171;">Error: \' + e.message + \'</td></tr>\';\n  }\n}\nfunction escapeHtml(s) {\n  return String(s || \'\').replace(/[&<>"\']/g, c => ({\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\',\'"\':\'&quot;\',"\'":\'&#39;\'}[c]));\n}\nloadSeries();\nsetInterval(loadSeries, 10000);\n</script>\n</body>\n</html>'

@app.route("/api/manga-pipeline")
def api_manga_pipeline():
    """Return current state of the single sequential manga pipeline."""
    import subprocess as _sp
    pipeline_state = {}
    try:
        with open(MANGA_SINGLE_STATE_FILE) as f:
            pipeline_state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    queue_total = 0
    queue_index = 0
    queue_next = []
    try:
        with open(MANGA_QUEUE_FILE) as f:
            q = json.load(f)
            queue_total = len(q.get("queue", []))
            queue_index = q.get("current_index", 0)
            for item in q.get("queue", [])[queue_index:queue_index+5]:
                queue_next.append({"title": item.get("title"), "anilist_id": item.get("anilist_id")})
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    current_manga = pipeline_state.get("current_manga")
    disk_chapters = 0
    if current_manga:
        import re as _re, os as _os
        s = _re.sub(r"[^\w\s-]", "", current_manga.lower())
        slug = _re.sub(r"[\s_-]+", "-", s).strip("-")[:80]
        manga_dir = "/data/media/manga/" + slug
        if _os.path.exists(manga_dir):
            disk_chapters = len([f for f in _os.listdir(manga_dir) if f.endswith(".zip")])
    db_chapters = 0
    if current_manga:
        try:
            import sqlite3 as _sql
            conn = _sql.connect(MANGA_DB_FILE)
            c = conn.cursor()
            c.execute("SELECT COUNT(DISTINCT chapter_number) FROM manga WHERE manga_name=?", (current_manga,))
            db_chapters = c.fetchone()[0]
            conn.close()
        except:
            pass
    def _svc_active(name):
        try:
            r = _sp.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=3)
            return r.stdout.strip() == "active"
        except:
            return False
    return jsonify({
        "pipeline_active": _svc_active("luffytv-manga-single"),
        "current_manga": current_manga,
        "current_phase": pipeline_state.get("current_phase"),
        "current_chapter": pipeline_state.get("current_chapter"),
        "chapter_progress": pipeline_state.get("current_chapter_progress"),
        "disk_chapters": disk_chapters,
        "db_chapters": db_chapters,
        "completed_manga": pipeline_state.get("completed_manga", []),
        "manga_done_count": len(pipeline_state.get("completed_manga", [])),
        "stats": pipeline_state.get("stats", {}),
        "queue_total": queue_total,
        "queue_index": queue_index,
        "queue_remaining": max(0, queue_total - queue_index),
        "queue_next": queue_next,
        "last_run": pipeline_state.get("started_at"),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)

