# Bloom — a word garden

A botanical word game in a single self-contained HTML file. Five letters sit in
a ring; trace them to spell words. Board words grow an **interlocking crossword
bed**; any other real word you find is **pressed** into your journal for bonus
pollen. Grow all 54 gardens.

**Play it:** open `index.html`. No build step, no network, no assets — every
letter, layout, sound, and illustration is generated in the file.

## How it plays

- **Trace** letters on the ring (drag with finger or mouse), release to submit.
  Keyboard also works: type letters, `Enter` submits, `Backspace` deletes,
  `Esc` clears. A one-time intro card covers the basics on first launch.
- **Board words** fill the crossword. Crossing letters carry over — and if
  crossings (or hints) ever complete a word on their own, it blooms
  automatically and still pays.
- **Pressings** are real words from the five letters that aren't on the board
  (checked against a built-in 5,169-word library). Each pays bonus pollen and
  is kept in the journal (tap the "pressed n/m flowers" chip).
- **Hint** reveals one letter cell on the word closest to finishing.
- **Sun** (bottom right) is a once-a-day pollen gift. Consecutive days build a
  streak: +5 per day on top of the base 40, capped at 60. A countdown shows
  when it's spent.
- Tap the garden name (top left) for the index of 54 gardens in five beds —
  Blossoms, Grove, Kitchen, Wild, Orchard — ordered by difficulty. Finishing a
  garden unlocks the next. Sound toggle and a two-tap progress reset live at
  the bottom of that sheet.

## Economy (all tunables in `CONFIG.econ`)

| knob | meaning | default |
|---|---|---|
| `startingPollen` | first-run balance | 150 |
| `solvePerLetter` | board word = length × this | 2 |
| `bonusBase` / `bonusStep` | pressing = base + (len−3)·step | 6 / 4 |
| `levelClear` | one-time reward for completing a garden | 30 |
| `hintCost` | reveal one cell | 20 |
| `dailySun` | daily gift; streak adds +5/day, capped at 60 | 40 |

Rewards pay **once** (auto-bloomed words included), so nothing farms. All
pollen moves through the `Wallet` object — `Wallet.earn(n, reason)` /
`Wallet.spend(n, reason)` — which is the single integration point for a real
currency backend later.

## Persistence

`Store` saves a debounced JSON blob under key `bloom.save.v3`:

```json
{ "pollen": 208, "current": 1, "unlocked": 1, "lastSun": "2026-7-1", "sunStreak": 2,
  "sound": true, "seenIntro": true,
  "prog": [ { "solved": ["TULIP"], "bonus": ["LIT"], "rev": ["2,3"], "claimed": true } ] }
```

`rev` holds hint-revealed **cells** as `"row,col"` keys. In this build `Store`
uses the artifact key-value API when present and otherwise no-ops (the game
plays fine without saving). To ship: swap the two-line `_read`/`_write` bodies
for `localStorage` or your backend. If you change the schema, bump the key.

## Repository

```
index.html            the whole game (data embedded)
test/test.js          47-check jsdom suite      → npm i && npm test
.github/workflows/    CI: runs the suite on every push
tools/gen_levels.py   content pipeline: rebuilds words + crossword layouts
                      and injects them into index.html in place
CLAUDE.md             working notes for Claude Code
```

Regenerating content needs Python 3 with `wordfreq` (`pip install wordfreq`);
the ENABLE word list auto-downloads on first run. The pipeline machine-checks
every crossword layout (letter consistency, connectivity, no accidental words)
and refuses to inject if any garden fails.

## Design

Cyanotype botanical — Anna Atkins sun-prints. Deep Prussian blues, pale
"printed" letters, a procedurally drawn fern, and **one** gold accent reserved
strictly for reward: pollen, the swipe trail, blooms, hint cells, petal bursts.
Serif display type from the system stack; respects `prefers-reduced-motion`.

## Roadmap

Real-device visual QA pass · PWA manifest + offline worker · timed
"golden hour" mode · achievements · portal wallet + account sync.
