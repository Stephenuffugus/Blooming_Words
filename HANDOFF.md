# Blooming Words — Handoff for Lucid Winds

Everything needed to put **Blooming Words** live and playable on the Lucid Winds
site. Read time: ~5 minutes. There is **no backend, no build step, no database,
no API keys, and no currency integration** — it is a fully self-contained static
web game.

---

## TL;DR

- The game is **one folder of static files**. Serve it over HTTPS and it runs.
- It is **already live** at: **https://stephenuffugus.github.io/Blooming_Words/**
- **Fastest path:** drop in an `<iframe>` pointing at that URL (snippet below).
- **Best path (recommended):** host the files on a Lucid Winds domain/subdomain
  so player progress saves reliably. Just copy the files — paths are relative.
- The in-game currency (**pollen**) is internal to the game. Nothing to wire up,
  no wallet, no accounts, no payments.

---

## What the game is

- A single `index.html` (~140 KB) containing all markup, CSS, JS, the level data
  (**142 gardens**), and the dictionary (**9,612 words**). No external fonts,
  images, trackers, or network calls at runtime.
- A small `assets/` folder (icons + social image), a PWA `manifest.webmanifest`,
  and an offline `sw.js` service worker.
- Saves progress to the browser's `localStorage`. Installable as a PWA. Plays
  offline after first load.

### File manifest (this is the whole deployable site)

```
index.html               the entire game
manifest.webmanifest     PWA metadata (installable app)
sw.js                    offline service worker
assets/favicon.svg
assets/favicon-32.png
assets/apple-touch-icon.png
assets/icon-192.png
assets/icon-512.png
assets/icon-maskable-512.png
assets/og.png            1200×630 social/share image
```

Everything else in the repo (`test/`, `tools/`, `*.md`, `.github/`) is for
development and **does not need to be deployed**.

---

## Option A — Embed via iframe (fastest, ~2 minutes)

Paste this where you want the game on a Lucid Winds page:

```html
<iframe
  src="https://stephenuffugus.github.io/Blooming_Words/"
  title="Blooming Words"
  style="width:100%; height:100dvh; max-height:900px; border:0; display:block;"
  allow="fullscreen"
  loading="lazy"></iframe>
```

- The game is portrait-first and responsive; give the iframe a **tall** height
  (a full-viewport container works best). On a mixed page, `min-height: 700px`
  is a sensible floor.
- ⚠️ **Storage caveat:** some browsers partition or block `localStorage` for
  third-party iframes. The game still plays perfectly, but **progress may not
  persist** across sessions when embedded cross-origin. If you want reliable
  saving, use Option B.

## Option B — Host on a Lucid Winds domain (recommended)

Because all internal paths are **relative** and `start_url` is `"."`, the game
runs from any origin or subpath with no edits.

1. Copy the files in the manifest above to your web root or a subfolder
   (e.g. `https://play.lucidwinds.com/` or `https://lucidwinds.com/bloom/`).
2. Serve over **HTTPS** (required for the service worker + PWA install).
3. Done — it works immediately.

Any static host works: Netlify, Vercel, Cloudflare Pages, S3+CloudFront, GitHub
Pages, or a plain Nginx/Apache directory. No server-side runtime is needed.

### Optional polish when self-hosting

- **Link previews:** the `<link rel="canonical">` and the `og:image` /
  `twitter:image` tags in `index.html` currently point at the GitHub Pages URL.
  If you host elsewhere and want share cards to show your domain, update those
  four absolute URLs in the `<head>` to your domain. (Purely cosmetic — the game
  works either way. The `og.png` file itself is already correct.)
- **MIME types:** make sure the host serves `.webmanifest` as
  `application/manifest+json` and `.js` as `application/javascript`. Most hosts
  do this automatically; GitHub Pages does.

---

## Requirements & guarantees

- **HTTPS** — needed for the service worker and PWA install. (Plain HTTP still
  plays; it just won't register the offline worker or install.)
- **No backend, no env vars, no secrets, no cookies, no third-party requests.**
- **No accounts / no payments.** Pollen is an in-game score only; there is
  nothing to integrate, bill, or reconcile.
- Works on modern mobile + desktop browsers. Touch (swipe-to-trace) and keyboard
  input both supported. Respects `prefers-reduced-motion`.

---

## Verifying it works

Open the page and you should see the intro card ("Blooming Words — a botanical
word garden") then Garden 01 · Tulip. Quick checks:

- Trace or type `TULIP` → it plants and pays pollen.
- Refresh (when hosted same-origin) → progress is still there.
- Add to Home Screen (mobile) → installs as an app icon.

---

## Updating the game later

The canonical source lives in the GitHub repo
`Stephenuffugus/Blooming_Words`. **Every push to `main` auto-deploys** to the
GitHub Pages URL via GitHub Actions (`.github/workflows/deploy.yml`), and the CI
test suite runs on every push. If you self-host (Option B), re-copy the files
after an update, or point your host at the same repo.

To add more gardens or expand the dictionary, see `README.md` and
`tools/gen_levels.py` (Python + `wordfreq`); it regenerates and re-validates all
content, then injects it into `index.html`.

---

## Contact / notes for integration

- If Lucid Winds wants a **completion signal** (e.g. to award site-side points
  when a player finishes a garden), that can be added as a `postMessage` from the
  game to the parent frame — but per direction, the game's own pollen economy
  stays entirely inside the game. Flag it if you want that hook and it can be
  wired on request.
- No analytics are included. If you want privacy-respecting analytics, add your
  snippet to the `<head>` of `index.html`.

That's everything. Serve the folder over HTTPS (or drop in the iframe) and
Blooming Words is live. 🌸
