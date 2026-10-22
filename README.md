# PSA Label Alignment Check

[中文說明 →](README.zh-TW.md)

An agent skill and command-line tool that checks whether a **PSA-graded slab in a
seller's photo carries a genuine PSA label**. It compares the label's text
layout, glyph by glyph, against photos of genuine slabs of the same card. By
default these come from [SNKRDUNK](https://snkrdunk.com), which authenticates
every sale and, unlike PSA's cert page, is reachable by agents. PSA's own cert
image works too, when you have it.

Counterfeit slabs copy a real cert number, a working QR code, and often PSA's own
photo, so "the cert looks up fine" proves nothing. What counterfeiters rarely
reproduce is PSA's exact typesetting.

![genuine vs fake](docs/control_vs_suspect_en.png)

## How it works

0. **Get references.** `snkrdunk_refs.py` finds the card on SNKRDUNK and
   downloads front photos of up to 8 PSA-graded copies, preferring sales that
   have passed SNKRDUNK's authentication.
1. **Rectify the labels.** The tool finds the red label frame in both images
   and warps each label to a canonical 960 × 291 px rectangle.
2. **Measure the glyphs.** Every glyph and digit from PSA's label is located in
   the seller's label by normalised cross-correlation, with sub-pixel
   refinement.
3. **Remove global distortion.** One global homography absorbs camera angle
   and lens distortion, and the glyphs are measured again.
4. **Score.** Two adjacent text lines are compared at the same horizontal
   positions:
   - A re-photograph of the *same* printed label moves every line together.
     The disagreement is below 1 px.
   - A re-typeset label shows lines drifting in different directions, by tens
     of pixels.
5. **Vote across references.** With `--description-only`, only the left
   description block is compared, so references of any cert and grade work.
   The test is `CONSISTENT` if it matches any genuine reference, and
   `MISMATCH` only if it matches none. PSA has re-typeset some labels between
   printing eras, so one reference from another era may legitimately differ.

| verdict | worst adjacent-line disagreement | meaning |
|---|---|---|
| `CONSISTENT` | ≤ 4 px | Text layout matches PSA. The label is very likely a genuine PSA print. |
| `MISMATCH` | ≥ 8 px | Text is typeset differently from every genuine reference. This indicates a reprinted or counterfeit label. |
| `INCONCLUSIVE` | 4–8 px, too few glyphs matched, or too few usable references | Get a sharper, more frontal photo, or more references, and run again. |

Calibration so far, with the label 960 px wide:

| case | vs PSA cert image | vs SNKRDUNK photos (`--description-only`) |
|---|---|---|
| Genuine Kanazawa's Pikachu PSA 10 | **0.34 px** | **0.24 px** (3/3 references match) |
| Suspected fake Kanazawa's Pikachu PSA 10 | **30.75 px** | **22.06 px** (0/3 match) |
| Genuine Leafeon VMAX PSA 9 | – | **0.19 px** (4/4 match) |

The full table is in [`references/method.md`](skills/psa-label-alignment/references/method.md).

## Quick start

```bash
pip install -r requirements.txt
S=skills/psa-label-alignment/scripts

# 1. find the card on SNKRDUNK (card number or Japanese name), then fetch references
python $S/snkrdunk_refs.py --search "089/069"
python $S/snkrdunk_refs.py --apparel-id 93023 --out refs/

# 2. compare the seller's photo against them
python $S/psa_label_check.py --ref refs/ref_*.jpg --description-only \
    --test listing_front.jpg --test-back listing_back.jpg --cert 153427845 --out out/
# -> {"verdict": "CONSISTENT", "max_adjacent_line_disagreement_px": 0.18, ...}
#    Text layout matches 3 of 8 genuine reference label(s).
```

Offline, with the bundled references:

```bash
python $S/psa_label_check.py --ref examples/snkrdunk_refs/kanazawa-pikachu-psa10/ref_*.jpg \
    --description-only --test examples/01-reprinted-label-suspect/listing_front.jpg --out out/
# -> {"verdict": "MISMATCH", "max_adjacent_line_disagreement_px": 22.06, ...}
```

If you have PSA's cert image for the exact cert, pass it as the single `--ref`
without `--description-only`; then the cert-number row is compared too.

The tool writes these files to the output folder:

- `report.json`, with `per_reference` results when several references are given
- `overlay.png`: magenta is the reference, green is the seller photo
- `displacement.png`: per-line shift curves
- the two rectified labels

With several references, the images are in `out/ref_N/`, and `report.json`
names the best-matching one.

| exit code | meaning |
|---|---|
| 0 | consistent |
| 1 | mismatch |
| 2 | inconclusive |
| 3 | error |

Useful flags:

- `--description-only`: compare only the left description block, skipping the
  card number, grade and cert column. Use it for references of a different
  cert or grade, such as SNKRDUNK photos.
- `--ignore-cert-line`: skip only the cert-number row. Use it for a reference
  of a different cert but the same grade.
- `--ref-corners` / `--test-corners "x,y;x,y;x,y;x,y"`: set the red-frame
  corners by hand if automatic detection fails. Give them in the order
  top-left, top-right, bottom-right, bottom-left. `--ref-corners` needs a
  single `--ref`.
- `snkrdunk_refs.py --grade PSA10`: only references of one grade (default: any
  PSA grade). `--n`: number of references (default 8). `--exclude-listing`:
  skip a listing, e.g. the one being tested.

## Use it as an agent skill

The skill lives in [`skills/psa-label-alignment/`](skills/psa-label-alignment/SKILL.md)
and uses the open **Agent Skills** format: a `SKILL.md` with YAML front matter,
plus `scripts/` and `references/`.

| Agent | How to install |
|---|---|
| Claude Code | Copy `skills/psa-label-alignment` to `~/.claude/skills/` (all projects) or `<project>/.claude/skills/` (one project). |
| Claude apps | Zip the `psa-label-alignment` folder and upload it as a custom skill. |
| Codex, Cursor, Gemini CLI, and other agents | Add this repo to the workspace. They read [`AGENTS.md`](AGENTS.md), which points to the skill. |
| Any other agent | It only needs to run one Python command and read a JSON report, so any agent that can run a shell can use it. |

Then ask your agent, for example: *"Is this PSA 10 on Mercari real?
https://jp.mercari.com/item/m…"*

## Examples

| | case | verdict |
|---|---|---|
| [01-reprinted-label-suspect](examples/01-reprinted-label-suspect/) | A 0-rating marketplace listing at about 70% of market price, filed under the wrong category | **MISMATCH**, 30.75 px |
| [02-genuine-control](examples/02-genuine-control/) | A long-standing seller with 1,000+ ratings, priced at market | **CONSISTENT**, 0.34 px |
| [03-snkrdunk-reference](examples/03-snkrdunk-reference/) | A self-submitted PSA 9 from a seller with 94 ratings, priced at market; checked against SNKRDUNK references only | **CONSISTENT**, 0.19 px (4/4) |

Examples 01 and 02 are also checked against the bundled SNKRDUNK references in
[`examples/snkrdunk_refs/`](examples/snkrdunk_refs/). Run everything with
`python tests/test_examples.py`; it works offline.

## Limits

- The tool checks the **label only**. It cannot detect a genuine slab that was
  opened and had a different card put inside.
- It needs a real photo of the label. If a seller only shows PSA's own images,
  that proves nothing.
- With SNKRDUNK references, the cert-number row is not compared. Check the cert
  number separately, e.g. with the QR code on the back (`--test-back --cert`).
- A label reprinted from a scan of a genuine label would pass.
- SNKRDUNK references are photos of other sellers' slabs. They are preferred
  once SNKRDUNK has authenticated them, but use several and look at
  `per_reference`.
- Its thresholds are provisional, because they were calibrated on a handful of slabs.
  Pull requests with more labelled examples are welcome.
- It is built for the standard red-bordered PSA label, and measures horizontal
  layout only.
- It is a screening aid, not an authentication service. For valuable cards,
  also use the marketplace's authentication option or a professional.

## License

The code is under the MIT license. The example images, including the
SNKRDUNK reference photos, are third-party photographs, included only to
demonstrate and test the method. Seller identities have been removed.
