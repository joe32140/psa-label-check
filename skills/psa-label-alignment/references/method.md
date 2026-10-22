# Method: label text-layout alignment

This is the algorithm used by `scripts/psa_label_check.py`.

## 1. Rectify the label

The red outer frame of the label is segmented in HSV. The mask is red hue
(H < 10 or H > 168) with S and V above a sequence of fallback thresholds.
The largest red quadrilateral with an aspect ratio between 2.2 and 8 is taken
as the frame. The ratio is allowed that wide because oblique photos foreshorten
the label. A candidate is accepted only if, once rectified, at least 35% of its
interior is bright and unsaturated (the white label card). This rejects orange
wood tables and red playmats of a plausible shape.

Its four corners are warped to a canonical 960 × 291 px label, in both the PSA
reference and the test photo. If detection fails, give the corners manually.

## 2. Measure every glyph

- The reference label is binarised with adaptive thresholding. These regions
  are masked out: the red frame, the barcode (bottom left) and the PSA
  hologram logo (bottom centre).
- Each remaining connected component is treated as one glyph or digit.
- Each glyph patch is located in the test label by normalised
  cross-correlation, searching within ±30 px. The peak is refined to
  sub-pixel accuracy with a parabolic fit.
- The result is one displacement `(dx, dy)` per glyph.

## 3. Remove global distortion

One RANSAC homography is fitted from all glyph matches. It absorbs perspective
error and frame-corner error. The test label is warped by it, and the glyphs
are measured again.

A single homography is smooth, so it cannot create opposite shifts in two
neighbouring lines. A re-typeset label therefore still stands out after this
step.

## 4. Score

- Glyphs are grouped into text lines by their y position.
- For each pair of adjacent lines:
  - Each line's `dx(x)` curve is smoothed with a median of 3, including at
    the line ends. This stops one glyph matched to an identical neighbour
    letter ("EEVEE") from deciding the verdict; a re-typeset shifts whole runs
    of glyphs.
  - The two curves are interpolated over the x range they share.
  - The maximum absolute difference between them is recorded.
- The verdict uses the worst pair:
  - **≤ 4 px**: `CONSISTENT`.
  - **≥ 8 px**: `MISMATCH`.
  - Otherwise: `INCONCLUSIVE`.
- The result is also `INCONCLUSIVE` if fewer than 40 glyphs match, or the
  median correlation is below 0.70.

## 5. References of another cert or grade (`--description-only`)

A reference does not have to be the same cert. With `--description-only`:

- the cert-number row (y ≥ 205 on the canonical label) is dropped, and
- each line is cut at its first gap wider than 70 px right of x = 300. What
  follows is the right column (card number, grade such as "GEM MT 10" or
  "MINT 9", cert), which differs between slabs.

What remains is the left description block, which PSA prints from the same
typesetting for every slab of that card within a printing era.

## 6. Several references and voting

`--ref` takes several images. Each is compared on its own, and:

- `CONSISTENT` if the test matches **any** usable reference;
- `MISMATCH` if it matches **none**, with at least two usable references
  (or the only reference given);
- otherwise `INCONCLUSIVE`.

"Any" rather than "majority" is deliberate. PSA has re-typeset the same
card's label between printing eras. For Kanazawa's Pikachu, certs around
60–63 million print "S – P" with spaces, while 77 million and later print
"S-P". For Leafeon VMAX (S6a 089/069), certs around 63–66 million print
"HEROES – HYPER" and 83 million and later "HEROES-HYPER"; a genuine
63-million slab matched one older reference at 0.30 px and differed from six
newer ones by 18–25 px. A genuine slab can therefore disagree with a genuine reference from
another era, but a re-typeset counterfeit should disagree with all of them.
Fetching 8 references usually covers both eras and leaves enough usable photos
after a few are rejected (stickers over the label, glare, frame not found).

## Calibration (canonical pixels; label width = 960)

| comparison | worst adjacent-line disagreement | verdict |
|---|---|---|
| PSA image vs itself | 0.03 | CONSISTENT |
| genuine slab photo (cert 161870798) vs its PSA image | **0.34** | CONSISTENT |
| genuine slab photo (cert 161870798) vs PSA image of *another* cert (134699919), `--ignore-cert-line` | 0.21 | CONSISTENT |
| PSA image of cert 134699919 vs PSA image of cert 161870798, lines 1–3 only | 0.86 | CONSISTENT |
| suspect slab photo (cert 134699919) vs its PSA image | **30.75** | MISMATCH |
| suspect slab photo vs PSA image of another cert, `--ignore-cert-line` | 34.71 | MISMATCH |
| genuine slab photo (cert 161870798) vs 3 SNKRDUNK PSA 10 photos, `--description-only` | 0.24 (3/3 match) | CONSISTENT |
| suspect slab photo (cert 134699919) vs the same 3 SNKRDUNK photos, `--description-only` | 22.06 (0/3 match) | MISMATCH |
| genuine PSA 9 Leafeon VMAX (cert 153427845) vs 3 SNKRDUNK PSA 9 + 1 PSA 10 photos, `--description-only` | 0.19 (4/4 match) | CONSISTENT |
| same, but PSA 10 references *without* `--description-only` | 27–31 | MISMATCH (grade column differs) |

Two genuine PSA labels for different certs of the same card, printed in the
same era, have identical description lines, within 1 px. This is why
references of another cert work when the exact cert page is not reachable.
Labels from different eras can differ (section 6), which is why several
references are used.

**Calibration status.** The thresholds come from a handful of genuine slabs
and one fake. Treat them as provisional, and add more labelled examples to
`examples/` to tighten them.

## Getting images

- **SNKRDUNK (default references):** `scripts/snkrdunk_refs.py` does this.
  - Search: `https://snkrdunk.com/search?keywords=<words>`. The HTML is
    server-rendered and contains `/apparels/<id>` links. Card numbers such as
    `144 s-p` or `089/069` work better than names.
  - Listings of one card: `https://snkrdunk.com/v1/apparels/<id>/used?page=<n>&perPage=50`
    (JSON). Use `displayShortConditionTitle` (`PSA10`, `PSA9`, …),
    `status`/`statusText` and `primaryPhoto.imageUrl` (the front photo).
  - Statuses after SNKRDUNK's authentication: 4 取引完了 (completed),
    11 運営の発送待ち (authenticated, waiting to ship), 13 到着待ち (shipped).
    These are preferred. Status 0 is a live listing that has not been checked yet.
  - A single listing page `https://snkrdunk.com/apparels/<id>/used/<listing>`
    has `photos.trading_card_single_front` / `_back` in its embedded data.
- **PSA cert page:** `https://www.psacard.com/cert/<cert>`. It usually has
  front and back images for recent certs. The site often blocks automated
  browsers with a bot check; in that case ask the user to download the image
  or take a screenshot of it.
- **Mercari:** `https://static.mercdn.net/item/detail/orig/photos/<item_id>_<n>.jpg`,
  where `n` runs from 1 up to the number of photos.
- **Rakuma:** full-size photos are at `https://img.fril.jp/img/<a>/l/<b>.jpg`.
  Read the `img` tags on the item page.
- **When the sandbox cannot reach the image host** but a browser tool can:
  1. Open the image URL in the browser.
  2. Run JavaScript that draws the `<img>` onto a canvas.
  3. Return `canvas.toDataURL('image/jpeg', 0.95)` between marker strings,
     for example `B64START…B64END`.
  4. Base64-decode it on the shell side.

  On its own origin the image does not taint the canvas.
- Always use the seller's **original file**. Screenshots of the listing page
  are downscaled.

## Other checks to combine with this one

| Check | Notes |
|---|---|
| Is the seller photo just PSA's image? | PSA's image has a flat grey background, perfectly frontal framing and no glare. A seller who only posts PSA's images has proven nothing. |
| QR code on the back label | `--test-back` decodes it. A valid code that points at the right cert is necessary but **not** sufficient, because fakes copy QR codes. |
| Card position inside the slab | The card's offset relative to the label should match PSA's image. A mismatch of about 1–2 mm suggests a different slab or a swapped card. Front and back should agree. |
| Price versus market | A PSA 10 priced at a PSA 9 price, or at 20–30% of market, is a red flag. Several different PSA 10 cards all at one flat price is a strong red flag. |
| Seller | Watch for 0 ratings, no identity verification, a listing only hours old, a wrong category chosen to dodge card-specific checks or authentication options, and a description written for a different product. |
| Physical, after delivery | Under backlight, the label text should faintly show through. Check that the PSA hologram shifts colour, that the case seam is clean and that the case has no pry marks. |
