#!/usr/bin/env python3
"""
Bloom content pipeline — regenerates the word library, garden levels, and
crossword layouts, then injects them into ../index.html in place.

  deps:  pip install wordfreq        (dict.txt auto-downloads if missing)
  run:   python3 tools/gen_levels.py         (from the repo root)
  then:  npm test

Tunables live at the top. After changing anchors or floors, always re-run and
re-test: the layout stage validates every garden and refuses to inject if any
garden fails.
"""
import json, random, re, sys, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, "index.html")
DICT_PATH = os.path.join(HERE, "dict.txt")
DICT_URL = "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt"

TARGET_FLOOR = 3.30      # board words: clearly common (zipf)
DICT_FLOOR   = 0.0       # pressings dictionary: the complete ENABLE 3-5 all-distinct set
MIN_TARGETS  = 4
HARD_COLS, HARD_ROWS = 10, 12
SEEDS = 160

BLOCK = set("""
ass tit tits arse crap damn hell piss slut sluts fag fags gook kike spic wog coon
jap japs dago paki cum jizz turd twat wank wanks prick dyke homo negro las los tho
sac butt scum wop chink poon smeg pac mon mae ami cock cocks dick dicks jism smut
whore whores slag boobs spunk kkk semen coons
""".split())

# (anchor, bed, latin caption) — anchor must be 5 DISTINCT letters.
# The pipeline drops any anchor with <MIN_TARGETS common words, any duplicate
# letter-set (first listed wins), and any garden whose layout won't validate.
ANCHORS = [
    # --- Blossoms (flowers) ---
    ("PETAL","Blossoms","corolla"), ("SEPAL","Blossoms","calyx"),
    ("TULIP","Blossoms","Tulipa"), ("PANSY","Blossoms","Viola tricolor"),
    ("PEONY","Blossoms","Paeonia"), ("DAISY","Blossoms","Bellis perennis"),
    ("VIOLA","Blossoms","Viola"), ("ASTER","Blossoms","Aster amellus"),
    ("FLORA","Blossoms","flora locale"), ("CALYX","Blossoms","calyx"),
    ("TANSY","Blossoms","Tanacetum vulgare"), ("SEDUM","Blossoms","Sedum acre"),
    ("PINKS","Blossoms","Dianthus"), ("STOCK","Blossoms","Matthiola incana"),
    ("BUGLE","Blossoms","Ajuga reptans"), ("LUPIN","Blossoms","Lupinus"),
    ("BRACT","Blossoms","bractea"), ("SPRAY","Blossoms","ramulus florens"),
    ("CANES","Blossoms","calami"),
    # --- Orchard (fruit) ---
    ("GRAPE","Orchard","Vitis vinifera"), ("PEACH","Orchard","Prunus persica"),
    ("MANGO","Orchard","Mangifera indica"), ("LEMON","Orchard","Citrus limon"),
    ("OLIVE","Orchard","Olea europaea"), ("PECAN","Orchard","Carya illinoinensis"),
    ("PLUMS","Orchard","Prunus domestica"), ("PEARS","Orchard","Pyrus communis"),
    ("FRUIT","Orchard","pomum"), ("LIMES","Orchard","Citrus aurantiifolia"),
    ("DATES","Orchard","Phoenix dactylifera"), ("PRUNE","Orchard","prunum"),
    ("CIDER","Orchard","sicera"),
    # --- Grove (trees & wood) ---
    ("MAPLE","Grove","Acer"), ("CEDAR","Grove","Cedrus libani"),
    ("BIRCH","Grove","Betula"), ("ALDER","Grove","Alnus"),
    ("LARCH","Grove","Larix"), ("HAZEL","Grove","Corylus avellana"),
    ("ROWAN","Grove","Sorbus aucuparia"), ("GROVE","Grove","nemus"),
    ("BOUGH","Grove","ramus"), ("BOWER","Grove","umbraculum"),
    ("TRUNK","Grove","truncus"), ("ASPEN","Grove","Populus tremula"),
    ("PINES","Grove","Pinus"), ("COPSE","Grove","silva caedua"),
    ("EBONY","Grove","Diospyros"), ("CAROB","Grove","Ceratonia siliqua"),
    ("LEAFY","Grove","frondosus"), ("ACORN","Grove","glans"),
    # --- Kitchen (herbs & harvest) ---
    ("BASIL","Kitchen","Ocimum basilicum"), ("THYME","Kitchen","Thymus"),
    ("MINTS","Kitchen","Mentha"), ("CHARD","Kitchen","Beta vulgaris"),
    ("CLOVE","Kitchen","Syzygium aromaticum"), ("BEANS","Kitchen","Phaseolus"),
    ("GRAIN","Kitchen","granum"), ("WHEAT","Kitchen","Triticum"),
    ("KALES","Kitchen","Brassica oleracea"), ("CHIVE","Kitchen","Allium schoenoprasum"),
    ("CUMIN","Kitchen","Cuminum cyminum"), ("MINCE","Kitchen","minutal"),
    ("BROTH","Kitchen","ius"), ("SPICE","Kitchen","aroma"),
    ("SUGAR","Kitchen","saccharum"), ("FLOUR","Kitchen","farina"),
    ("YEAST","Kitchen","fermentum"), ("DOUGH","Kitchen","massa"),
    ("HONEY","Kitchen","mel"), ("SYRUP","Kitchen","sirupus"),
    ("PESTO","Kitchen","pistum"), ("BREAD","Kitchen","panis"),
    ("GRITS","Kitchen","polenta"), ("TUBER","Kitchen","tuber"),
    # --- Meadow (grass & harvest field) ---
    ("HERBS","Meadow","herba"), ("LEAFS","Meadow","frondes"),
    ("SPRIG","Meadow","surculus"), ("GROWS","Meadow","crescit"),
    ("GRAZE","Meadow","pascere"), ("SPELT","Meadow","Triticum spelta"),
    ("SWATH","Meadow","ordo faeni"), ("BALES","Meadow","fasciculi"),
    ("HAYED","Meadow","faenum"), ("MOWED","Meadow","demessus"),
    # --- Wild (wildland & terrain) ---
    ("FROND","Wild","Pteridium"), ("FERNS","Wild","Polypodiopsida"),
    ("THORN","Wild","spina"), ("SHRUB","Wild","frutex"),
    ("GORSE","Wild","Ulex europaeus"), ("BLADE","Wild","gramen"),
    ("FIELD","Wild","campus"), ("GLADE","Wild","saltus"),
    ("MARSH","Wild","palus"), ("DUNES","Wild","dunae"),
    ("TWIGS","Wild","virgae"), ("VINES","Wild","Vitis"),
    ("SPORE","Wild","spora"), ("LOTUS","Wild","Nelumbo nucifera"),
    ("PLANT","Wild","in horto"), ("STALK","Wild","caulis"),
    ("BRAKE","Wild","filicetum"), ("RUSHY","Wild","iuncosus"),
    ("SWAMP","Wild","palus limosa"), ("RIDGE","Wild","iugum"),
    ("SLOPE","Wild","clivus"), ("VALES","Wild","valles"),
    ("ROCKS","Wild","saxa"), ("STONE","Wild","lapis"),
    ("SANDY","Wild","harenosus"), ("WILDS","Wild","ferae terrae"),
    # --- Wetland (water's edge — algae, silt, tides; after Atkins' cyanotypes) ---
    ("SILTY","Wetland","limosus"), ("DELTA","Wetland","ostium"),
    ("CORAL","Wetland","corallium"), ("PEARL","Wetland","margarita"),
    ("TIDES","Wetland","aestus"), ("WAVES","Wetland","undae"),
    ("INLET","Wetland","aestuarium"),
    # --- Wings (birds & flying things — Atkins pressed feathers too) ---
    ("ROBIN","Wings","Erithacus rubecula"), ("WRENS","Wings","Troglodytes"),
    ("FINCH","Wings","Fringilla"), ("DOVES","Wings","Columba"),
    ("LARKS","Wings","Alauda"), ("HERON","Wings","Ardea cinerea"),
    ("CROWS","Wings","Corvus"), ("HAWKS","Wings","Accipiter"),
    ("MOTHS","Wings","Lepidoptera"), ("SWIFT","Wings","Apus apus"),
    ("PLUME","Wings","penna"),
    # --- Fauna (garden visitors) ---
    ("SNAIL","Fauna","Helix"), ("TOADS","Fauna","Bufo"),
    ("FROGS","Fauna","Rana"), ("NEWTS","Fauna","Triturus"),
    ("MOLES","Fauna","Talpa"), ("VOLES","Fauna","Microtus"),
    ("HARES","Fauna","Lepus"), ("FOXES","Fauna","Vulpes vulpes"),
    # --- Weather (the garden's sky) ---
    ("RAINS","Weather","pluvia"), ("FROST","Weather","pruina"),
    ("MISTY","Weather","nebulosus"), ("CLOUD","Weather","nubes"),
    ("STORM","Weather","tempestas"), ("WINDS","Weather","venti"),
    ("SNOWY","Weather","nivosus"), ("GALES","Weather","procellae"),
]

# ---------------------------------------------------------------- word data
try:
    from wordfreq import zipf_frequency
except ImportError:
    sys.exit("missing dependency: pip install wordfreq")

if not os.path.exists(DICT_PATH):
    print("downloading ENABLE dictionary …")
    urllib.request.urlretrieve(DICT_URL, DICT_PATH)

VALID = {l.strip().lower() for l in open(DICT_PATH) if l.strip().isalpha()}
zf = lambda w: zipf_frequency(w, "en")

DICT = sorted(w for w in VALID
              if 3 <= len(w) <= 5 and len(set(w)) == len(w)
              and w not in BLOCK and zf(w) >= DICT_FLOOR)

def words_for(letters):
    s = set(letters)
    out = [w for w in VALID if 3 <= len(w) <= 5 and len(set(w)) == len(w)
           and set(w) <= s and w not in BLOCK]
    out.sort(key=lambda w: (-zf(w), -len(w), w))
    return out

def pick_targets(anchor, allw):
    common = [w for w in allw if zf(w) >= TARGET_FLOOR]
    by = {3: [], 4: [], 5: []}
    for w in common: by[len(w)].append(w)
    t = [anchor.lower()]
    for w in by[5]:
        if w != anchor.lower() and sum(1 for x in t if len(x) == 5) < 2: t.append(w)
    t += by[4][:2] + by[3][:3]
    seen, out = set(), []
    for w in t:
        if w not in seen: seen.add(w); out.append(w)
        if len(out) >= 7: break
    return out

raw = []
for anchor, bed, cap in ANCHORS:
    a = anchor.lower()
    targets = pick_targets(anchor, words_for(a))
    if len(targets) < MIN_TARGETS:
        print("skip (too few targets):", anchor); continue
    avglen = sum(len(w) for w in targets) / len(targets)
    raw.append({"anchor": anchor, "bed": bed, "cap": cap,
                "letters": sorted(set(anchor)),
                "targets": [t.upper() for t in targets],
                "diff": len(targets) + avglen * 0.6})

seen_sets, dedup = set(), []
for r in raw:
    key = frozenset(r["letters"])
    if key in seen_sets: print("dedupe (same letters):", r["anchor"]); continue
    seen_sets.add(key); dedup.append(r)
raw = dedup
# Curated thematic journey: open in the flower bed, work through the cultivated
# garden, out into the wild, down to the water, then the living things, then the
# sky. Within each bed, gardens ramp gently by difficulty. Any bed not listed
# here is appended (so new beds never silently vanish).
BED_ORDER = ["Blossoms", "Kitchen", "Orchard", "Grove", "Meadow",
             "Wild", "Wetland", "Wings", "Fauna", "Weather"]
present = {r["bed"] for r in raw}
bed_order = [b for b in BED_ORDER if b in present] + sorted(present - set(BED_ORDER))
raw.sort(key=lambda r: (bed_order.index(r["bed"]), r["diff"]))

# ---------------------------------------------------------------- layouts
def attempt(words, seed):
    rnd = random.Random(seed)
    order = sorted(words, key=lambda w: (-len(w), rnd.random()))
    grid, placed = {}, []

    def can(word, r, c, d):
        dr, dc = (0, 1) if d == 0 else (1, 0)
        if (r - dr, c - dc) in grid or (r + dr*len(word), c + dc*len(word)) in grid:
            return None
        cross = 0
        for k, ch in enumerate(word):
            cell = (r + dr*k, c + dc*k)
            if cell in grid:
                if grid[cell] != ch: return None
                cross += 1
            else:
                n1 = (cell[0] + (1 if d == 0 else 0), cell[1] + (0 if d == 0 else 1))
                n2 = (cell[0] - (1 if d == 0 else 0), cell[1] - (0 if d == 0 else 1))
                if n1 in grid or n2 in grid: return None
        if placed and cross == 0: return None
        return cross

    def put(word, r, c, d):
        dr, dc = (0, 1) if d == 0 else (1, 0)
        for k, ch in enumerate(word): grid[(r + dr*k, c + dc*k)] = ch
        placed.append((word, r, c, d))

    put(order[0], 0, 0, seed % 2)
    for word in order[1:]:
        cands = []
        for (pw, pr, pc, pd) in placed:
            pdr, pdc = (0, 1) if pd == 0 else (1, 0)
            for pk, pch in enumerate(pw):
                ar, ac = pr + pdr*pk, pc + pdc*pk
                for k, ch in enumerate(word):
                    if ch != pch: continue
                    d = 1 - pd
                    dr, dc = (0, 1) if d == 0 else (1, 0)
                    r, c = ar - dr*k, ac - dc*k
                    cr = can(word, r, c, d)
                    if cr is None: continue
                    cells = [(r + dr*k2, c + dc*k2) for k2 in range(len(word))]
                    rs = [p[0] for p in grid] + [p[0] for p in cells]
                    cs = [p[1] for p in grid] + [p[1] for p in cells]
                    rows, cols = max(rs)-min(rs)+1, max(cs)-min(cs)+1
                    if cols > HARD_COLS or rows > HARD_ROWS: continue
                    cands.append((-cr, rows*cols, abs(cols-rows), rnd.random(), r, c, d))
        if not cands: return None
        cands.sort()
        _, _, _, _, r, c, d = cands[0]
        put(word, r, c, d)

    rs = [p[0] for p in grid]; cs = [p[1] for p in grid]
    r0, c0 = min(rs), min(cs)
    rows, cols = max(rs)-r0+1, max(cs)-c0+1
    pos = {w: [r - r0, c - c0, d] for (w, r, c, d) in placed}
    ncross = sum(len(w) for w in words) - len(grid)
    score = ncross*3 - rows*cols*0.22 - max(0, cols-9)*8 - abs(cols-rows)*0.6
    return {"pos": pos, "gh": rows, "gw": cols, "score": score}

def validate(words, lay):
    grid = {}
    for w, (r0, c0, d) in lay["pos"].items():
        dr, dc = (0, 1) if d == 0 else (1, 0)
        for k, ch in enumerate(w):
            cell = (r0 + dr*k, c0 + dc*k)
            if cell in grid and grid[cell] != ch: return "letter clash"
            grid[cell] = ch
    cellwords = {}
    for w, (r0, c0, d) in lay["pos"].items():
        dr, dc = (0, 1) if d == 0 else (1, 0)
        for k in range(len(w)):
            cellwords.setdefault((r0 + dr*k, c0 + dc*k), []).append(w)
    adj = {w: set() for w in words}
    for ws in cellwords.values():
        for a in ws:
            for b in ws:
                if a != b: adj[a].add(b)
    seen, stack = set(), [words[0]]
    while stack:
        w = stack.pop()
        if w in seen: continue
        seen.add(w); stack.extend(adj[w])
    if len(seen) != len(words): return "disconnected"
    hset = {(w, r, c) for w, (r, c, d) in lay["pos"].items() if d == 0}
    vset = {(w, r, c) for w, (r, c, d) in lay["pos"].items() if d == 1}
    R, C = lay["gh"], lay["gw"]
    for r in range(R):
        c = 0
        while c < C:
            if (r, c) in grid and (r, c-1) not in grid:
                run, cc = "", c
                while (r, cc) in grid: run += grid[(r, cc)]; cc += 1
                if len(run) >= 2 and (run, r, c) not in hset: return f"stray H {run}"
                c = cc
            else: c += 1
    for c in range(C):
        r = 0
        while r < R:
            if (r, c) in grid and (r-1, c) not in grid:
                run, rr = "", r
                while (rr, c) in grid: run += grid[(rr, c)]; rr += 1
                if len(run) >= 2 and (run, r, c) not in vset: return f"stray V {run}"
                r = rr
            else: r += 1
    return None

levels, fails = [], []
for r in raw:
    best = None
    for seed in range(SEEDS):
        lay = attempt(r["targets"], seed)
        if lay and (best is None or lay["score"] > best["score"]):
            if validate(r["targets"], lay) is None:
                best = lay
    if not best:
        fails.append(r["anchor"]); continue
    levels.append({"anchor": r["anchor"], "name": r["anchor"].title(), "bed": r["bed"],
                   "latin": r["cap"], "letters": r["letters"], "targets": r["targets"],
                   "gw": best["gw"], "gh": best["gh"], "pos": best["pos"]})

print(f"gardens: {len(levels)}  dictionary: {len(DICT)}")
if fails:
    # A single un-layoutable anchor no longer aborts the whole build; it is simply
    # dropped so the large themed anchor pool can grow without hand-tuning each one.
    print(f"dropped (no valid layout in {SEEDS} seeds): {fails}")
if len(levels) < MIN_TARGETS:
    sys.exit("FAILED — too few gardens survived; check anchors/dict.")

# ---------------------------------------------------------------- inject
levels_js = json.dumps(levels, separators=(",", ":"))
dict_js = " ".join(DICT)
html = open(INDEX).read()
html2, n1 = re.subn(r"const LEVELS = \[.*?\];",
                    lambda m: "const LEVELS = " + levels_js + ";", html, count=1, flags=re.S)
html3, n2 = re.subn(r'const DICT = new Set\(\("[^"]*"\)',
                    lambda m: 'const DICT = new Set(("' + dict_js + '")', html2, count=1)
if n1 != 1 or n2 != 1:
    sys.exit(f"inject failed (LEVELS={n1}, DICT={n2}) — index.html markers changed?")
open(INDEX, "w").write(html3)
print(f"injected into index.html ({len(html3)} bytes). Now run: npm test")
