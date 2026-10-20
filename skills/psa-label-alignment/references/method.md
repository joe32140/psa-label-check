# Method: label text-layout alignment

This is the algorithm used by `scripts/psa_label_check.py`.

## 1. Rectify the label

The red outer frame of the label is segmented in HSV. The mask is red hue
(H < 10 or H > 168) with S and V above a sequence of fallback thresholds.
The largest red quadrilateral with an aspect ratio between 2.2 and 8 is taken
as the frame. The ratio is allowed that wide because oblique photos foreshorten
the label.

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
  - Each line's `dx(x)` curve is smoothed with a median of 3.
  - The two curves are interpolated over the x range they share.
  - The maximum absolute difference between them is recorded.
- The verdict uses the worst pair:
  - **≤ 4 px**: `CONSISTENT`.
  - **≥ 8 px**: `MISMATCH`.
  - Otherwise: `INCONCLUSIVE`.
- The result is also `INCONCLUSIVE` if fewer than 40 glyphs match, or the
  median correlation is below 0.70.

## Calibration (canonical pixels; label width = 960)

| comparison | worst adjacent-line disagreement | verdict |
|---|---|---|
| PSA image vs itself | 0.02 | CONSISTENT |
| genuine slab photo (cert 161870798) vs its PSA image | **0.27** | CONSISTENT |
| genuine slab photo (cert 161870798) vs PSA image of *another* cert (134699919), `--ignore-cert-line` | 0.22 | CONSISTENT |
| PSA image of cert 134699919 vs PSA image of cert 161870798, lines 1–3 only | 0.86 | CONSISTENT |
| suspect slab photo (cert 134699919) vs its PSA image | **30.75** | MISMATCH |
| suspect slab photo vs PSA image of another cert, `--ignore-cert-line` | 34.71 | MISMATCH |

Two genuine PSA labels for different certs of the same card have identical
description lines, within 1 px. This is why a reference image of another cert
works when the exact cert page is not reachable.

**Calibration status.** The thresholds come from one genuine slab and one
fake. Treat them as provisional, and add more labelled examples to
`examples/` to tighten them.

## Getting images

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
