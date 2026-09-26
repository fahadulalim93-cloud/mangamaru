#!/usr/bin/env node
/**
 * LuffyTV MangaGo.me Scraper
 * ===========================
 * Uses Playwright to render the JS-encrypted chapter page (imgsrcs → real CDN URLs),
 * then downloads the decoded images directly via curl (no token, no referer needed).
 *
 * Usage:
 *   node mangago_scraper.js <manga_url_or_slug> [--max-chapters N] [--start N] [--out DIR]
 *
 * Examples:
 *   node mangago_scraper.js crocodile --max-chapters 1
 *   node mangago_scraper.js https://www.mangago.me/read-manga/crocodile/
 *   node mangago_scraper.js beyblade_burst --start 0 --max-chapters 5
 *
 * Output: /root/downloads/manga/<slug>/<slug>_ch<NN>.zip
 *         (compatible with manga_uploader.py — imgur pipeline)
 */
const { chromium } = require('playwright');
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const AdmZip = require('adm-zip');

const OUT_DIR = process.env.MANGA_OUT_DIR || '/root/downloads/manga';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';

// ---------- helpers ----------
function parseArgs(argv) {
  const args = { manga: null, maxChapters: null, start: 0, out: OUT_DIR };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--max-chapters') args.maxChapters = parseInt(argv[++i]);
    else if (a === '--start') args.start = parseInt(argv[++i]);
    else if (a === '--out') args.out = argv[++i];
    else if (!a.startsWith('--')) args.manga = a;
  }
  if (!args.manga) {
    console.error('Usage: node mangago_scraper.js <manga_url_or_slug> [--max-chapters N] [--start N] [--out DIR]');
    process.exit(1);
  }
  return args;
}

function slugFromInput(input) {
  // Accept full URL or bare slug
  const m = input.match(/read-manga\/([^/]+)\//);
  if (m) return m[1];
  return input.replace(/^https?:\/\/[^/]+\/?/, '').replace(/\/$/, '');
}

function mangaInfoUrl(slug) {
  return `https://www.mangago.me/read-manga/${slug}/`;
}

function log(...a) { console.log(`[${new Date().toISOString()}]`, ...a); }

// ---------- chapter discovery ----------
// Visit the manga info page (mangago.me) and grab all chapter URLs.
// Returns array of { url, label } in oldest→newest order.
async function listChapters(infoUrl, page) {
  log(`Listing chapters: ${infoUrl}`);
  await page.goto(infoUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1500);

  const chapters = await page.evaluate(() => {
    const out = [];
    // The chapter_table lists every chapter
    const rows = document.querySelectorAll('#chapter_table a.chico, .ch_raw a.chico, .listing a.chico');
    rows.forEach(a => {
      const href = a.href;
      if (!href) return;
      const label = a.textContent.replace(/\s+/g, ' ').trim();
      out.push({ url: href, label });
    });
    // Also try the "Start Reading" link on the cover (single-chapter manga)
    if (out.length === 0) {
      const start = document.querySelector('a.content-h1-btn');
      if (start) out.push({ url: start.href, label: 'Ch.1' });
    }
    return out;
  });

  // Dedup by URL
  const seen = new Set();
  const unique = [];
  for (const c of chapters) {
    if (seen.has(c.url)) continue;
    seen.add(c.url);
    unique.push(c);
  }
  // Reverse so oldest is first
  unique.reverse();
  log(`Found ${unique.length} chapters`);
  return unique;
}

// ---------- chapter image extraction ----------
// Strategy:
//   1. Visit the chapter URL (OLD or NEW format).
//   2. If OLD format (read-manga/.../pg-N/), extract the embedded NEW format URL
//      (mangago.zone/chapter/<mid>/<cid>/) from the rendered HTML — that page
//      renders ALL pages of the chapter in one shot.
//   3. Navigate to NEW URL, collect all <img> inside #pic_container.
//   4. Fallback: iterate pg-1..pg-N and dedup if NEW URL not found.
async function chapterImages(chapterUrl, page) {
  // Step 1: visit the chapter URL
  await page.goto(chapterUrl, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);

  // Step 2: extract NEW format URL if present (OLD format embeds it as the
  // "Start Reading" / chapter list link)
  const newUrl = await page.evaluate(() => {
    const html = document.documentElement.outerHTML;
    const m = html.match(/mangago\.zone\/chapter\/\d+\/\d+/);
    return m ? `https://www.${m[0]}/` : null;
  });

  let targetUrl = chapterUrl;
  if (newUrl && newUrl !== chapterUrl) {
    log(`  ℹ converting OLD→NEW: ${newUrl}`);
    targetUrl = newUrl;
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2500);
  }

  // Step 3: collect images from #pic_container
  let imgs = await page.evaluate(() => {
    const c = document.querySelector('#pic_container');
    if (!c) return [];
    return Array.from(c.querySelectorAll('img'))
      .map(img => img.src)
      .filter(s => s && s.includes('mangapicgallery.com/r/'));
  });

  // Step 4: fallback — iterate pg-N if we still have <3 images (OLD URL, no NEW ref)
  if (imgs.length < 3) {
    const total = await page.evaluate(() => {
      try { return typeof total_pages !== 'undefined' ? total_pages : 0; } catch(e) { return 0; }
    });
    if (total > 1 && chapterUrl.includes('/pg-1/')) {
      log(`  ℹ falling back to pg-1..pg-${total} iteration`);
      const seen = new Set(imgs);
      for (let pg = 2; pg <= total; pg++) {
        const pgUrl = chapterUrl.replace('/pg-1/', `/pg-${pg}/`);
        try {
          await page.goto(pgUrl, { waitUntil: 'networkidle', timeout: 60000 });
          await page.waitForTimeout(1500);
          const pgImgs = await page.evaluate(() =>
            Array.from(document.querySelectorAll('#pic_container img'))
              .map(i => i.src).filter(Boolean)
          );
          pgImgs.forEach(u => seen.add(u));
        } catch (e) {
          log(`  ⚠ pg-${pg} failed: ${e.message}`);
        }
      }
      imgs = [...seen];
    }
  }

  return imgs;
}

// ---------- image download ----------
function downloadImage(url, dest) {
  // curl is fastest; images don't need referer/cookies
  const r = spawnSync('curl', ['-sL', '-A', UA, '-o', dest, url], { timeout: 60000 });
  if (r.status !== 0) throw new Error(`curl failed: ${r.stderr?.toString() || 'unknown'}`);
  if (!fs.existsSync(dest) || fs.statSync(dest).size < 1024) {
    throw new Error(`Image too small or missing: ${dest}`);
  }
}

// ---------- main ----------
(async () => {
  const args = parseArgs(process.argv);
  const slug = slugFromInput(args.manga);
  const infoUrl = mangaInfoUrl(slug);
  const outDir = path.join(args.out, slug);
  fs.mkdirSync(outDir, { recursive: true });

  log(`Manga slug: ${slug}`);
  log(`Output dir: ${outDir}`);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    userAgent: UA,
    viewport: { width: 1366, height: 900 },
    javaScriptEnabled: true,
  });
  const page = await ctx.newPage();

  // Step 1: list chapters
  let chapters = await listChapters(infoUrl, page);
  if (chapters.length === 0) {
    log('No chapter list found — trying direct chapter URL');
    // User might have given a direct chapter URL
    if (args.manga.includes('/chapter/')) {
      chapters = [{ url: args.manga, label: 'Ch.1' }];
    } else {
      log('ERROR: No chapters found for slug:', slug);
      await browser.close();
      process.exit(1);
    }
  }

  // Apply --start / --max-chapters
  const start = Math.max(0, args.start);
  let end = chapters.length;
  if (args.maxChapters) end = Math.min(end, start + args.maxChapters);
  chapters = chapters.slice(start, end);
  log(`Scraping chapters ${start}..${end - 1} (${chapters.length} total)`);

  let ok = 0, fail = 0;
  for (let i = 0; i < chapters.length; i++) {
    const ch = chapters[i];
    const chNum = String(start + i + 1).padStart(2, '0');
    const zipPath = path.join(outDir, `${slug}_ch${chNum}.zip`);
    if (fs.existsSync(zipPath) && fs.statSync(zipPath).size > 5000) {
      log(`[${i + 1}/${chapters.length}] SKIP ${ch.label} (already exists: ${path.basename(zipPath)})`);
      ok++;
      continue;
    }
    log(`[${i + 1}/${chapters.length}] ${ch.label} (${ch.url})`);
    try {
      const imgs = await chapterImages(ch.url, page);
      if (imgs.length === 0) throw new Error('No image URLs extracted');
      log(`  → ${imgs.length} pages`);

      const tmpDir = path.join(outDir, `.tmp_ch${chNum}`);
      fs.rmSync(tmpDir, { recursive: true, force: true });
      fs.mkdirSync(tmpDir, { recursive: true });

      for (let p = 0; p < imgs.length; p++) {
        const dest = path.join(tmpDir, `page_${String(p + 1).padStart(3, '0')}.jpg`);
        downloadImage(imgs[p], dest);
        if (p % 5 === 0) process.stdout.write(`  ${(p + 1)}/${imgs.length}\r`);
      }
      process.stdout.write('                                       \r');

      // Zip it (compatible with manga_uploader.py — expects a ZIP of images)
      const zip = new AdmZip();
      for (let p = 0; p < imgs.length; p++) {
        const src = path.join(tmpDir, `page_${String(p + 1).padStart(3, '0')}.jpg`);
        zip.addLocalFile(src);
      }
      zip.writeZip(zipPath);
      fs.rmSync(tmpDir, { recursive: true, force: true });
      log(`  ✓ ${path.basename(zipPath)} (${imgs.length} pages)`);
      ok++;
    } catch (e) {
      log(`  ✗ FAILED: ${e.message}`);
      fail++;
    }
  }

  await browser.close();
  log(`\nDone. ${ok} ok, ${fail} failed. Output: ${outDir}`);
  process.exit(fail > 0 ? 2 : 0);
})().catch(e => { console.error('FATAL:', e); process.exit(1); });
