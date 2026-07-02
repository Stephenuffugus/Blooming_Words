# CLAUDE.md — working notes for Bloom

Bloom is a **single-file** botanical word game: everything lives in
`index.html` (markup, CSS, JS, generated level data, generated dictionary).
Keep it that way — no bundlers, no external assets, no runtime network calls.

## Run / test

- Play: open `index.html` in a browser.
- Test: `npm i && npm test` → runs `test/test.js` (jsdom), currently
  **47 checks**. Run it after *every* change. Add checks when you add behavior.
- The suite loads the real `index.html` and injects a `window.__test` hook
  before the `BOOT` banner at runtime — there is no separate test build.

## Map of index.html

One `<script>` with banner comments — jump by searching the banner name:

`CONFIG` (tunables) · `DATA` (generated `LEVELS` + `DICT` — never hand-edit,
see pipeline) · `STORE` (persistence) · `STATE` (game object,
serialize/hydrate) · `WALLET` (all pollen movement) · `SOUND` (WebAudio,
asset-free) + `buzz()` haptics · `HELPERS` · `RENDER` (`ui`: crossword grid,
paint, petal bursts) · `LAYOUT FIT` (`fit()`: sizes ring + `--cell` var) ·
`RING + INPUT` (pointer drag + keyboard) · `SUBMIT / SOLVE` (incl.
`checkAuto`) · `HINT` · `DAILY SUN` · `LEVEL COMPLETE` · `GARDENS` ·
`JOURNAL` · `NAV` · `SETTINGS` · `WIRE UP` · `BOOT`.

## Contracts and invariants

- **Wallet is the only currency path.** Never mutate `game.pollen` directly
  (exception: the reset button). To integrate a real backend, re-point
  `Wallet.earn/spend` and keep the signatures — `spend` returns `false` on
  insufficient funds.
- **Economy** lives in `CONFIG.econ` only. Rewards pay once per word/garden;
  auto-solved words pay the same as traced ones; a hint (20) always costs
  more than any single cell is worth — keep it that way. The sun streak
  bonus is capped at 60/day.
- **Data shape.** Each level: `letters` (exactly 5 distinct), `targets`
  (3–5 letters, no repeats, uppercase), `gw`/`gh` grid size, `pos[WORD] =
  [row, col, dir]` with dir `0`=across `1`=down. Layouts are machine-validated
  by the pipeline; the renderer trusts them.
- **DICT** is uppercased into a `Set` at boot. Pressings = in `DICT`, formable
  from the level's letters, not a target.
- **Save schema** (`bloom.save.v3`): see README — includes `sunStreak` and
  `seenIntro`. `prog[i].rev` stores
  hint-revealed cells as `"row,col"`. If you change the schema, bump the key
  and handle/discard old blobs deliberately.
- **Palette rule:** gold (`--sun`) marks *reward only* — pollen, trail,
  solves, hints, petals. Don't use it for chrome. Keep
  `prefers-reduced-motion` working.

## Content pipeline

```
pip install wordfreq
python3 tools/gen_levels.py      # from repo root
npm test
```

Rebuilds targets (zipf ≥ 3.30) and the open dictionary (zipf ≥ 2.50, ENABLE
list, profanity/fragment blocklist), computes an interlocking crossword layout
per garden (120 seeded attempts, best score), **independently validates**
every layout (letter consistency, connectivity, no stray adjacent words), and
regex-injects both `const LEVELS = […];` and the `DICT` string into
`index.html` in place. It exits nonzero rather than inject anything invalid.
To add content, extend `ANCHORS` (anchor must be 5 distinct letters) and
re-run.

## Common tasks

- **Tune difficulty/economy:** edit `CONFIG.econ`; the hint/auto-solve
  invariant above must hold. Tests pin exact totals — update them with intent.
- **Ship persistence:** in `STORE`, replace `_read`/`_write` bodies with
  `localStorage.getItem/setItem(KEY, …)` or backend calls. Everything else is
  already async-tolerant.
- **Portal wallet:** replace `Wallet.earn/spend` internals; keep them
  synchronous-looking (optimistic update + reconcile is fine).

## Gotchas

- `window.storage` (artifact KV) exists only in the Claude preview; the
  `Store` fallbacks and try/catch are load-bearing. Same for the guards around
  `scrollIntoView`, `element.animate`, and `navigator.vibrate` — jsdom and
  older browsers lack them. Don't remove guards.
- The ring uses **pointer capture** on `#ring`; don't switch to
  touch/mouse events (double-fire on mobile).
- Heights use `100dvh` with a `100vh` fallback for iOS toolbars; `fit()` also
  runs on resize/orientation. The board scrolls vertically on very short
  screens by design (`--cell` floors at 20px).
- `LEVELS`/`DICT` lines are regenerated wholesale — never hand-edit them; the
  injector's regex depends on their exact `const … = …;` shape.
