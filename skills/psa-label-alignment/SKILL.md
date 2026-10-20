---
name: psa-label-alignment
description: Check whether a PSA-graded card slab in a seller's photo has a genuine PSA label by comparing the label's text layout, glyph by glyph, against PSA's official cert image. Use when someone asks if a PSA slab (Pokémon, sports, any TCG) on Mercari, Rakuma, eBay, Yahoo Auctions etc. is real or fake, or wants a slab photo compared with the PSA cert page.
---

# PSA label alignment check / PSA 標籤字距比對

Counterfeit PSA slabs usually copy a **real** cert number, QR code and PSA's
official photo, so "the cert number looks up fine" proves nothing. What fakers
rarely get right is PSA's exact typesetting. This skill measures it.

**Principle.** A photo of the *same printed label* can differ from PSA's image
only by one smooth, whole-label distortion (camera angle, lens). Every text
line shifts together. A re-typeset label shows **line-specific** shifts:
neighbouring lines drift in opposite directions at the same x position.

**原理：** 同一張印刷標籤翻拍，只會整體平滑變形，四行字一起移動；重新排版印的假標籤，相鄰兩行會在同一位置往不同方向偏。

## Workflow

1. **Get the two front images.**
   - **Reference:** PSA's image for the cert, from `https://www.psacard.com/cert/<cert>`. The site is often behind a bot check, so if you cannot load it, ask the user to save the front image and send it. A PSA image of a *different* cert of the same card also works with `--ignore-cert-line`, because PSA typesets identical description lines identically.
   - **Test:** the seller's own photo of the slab front at full resolution, with the label at least ~300 px wide. Download the original file rather than taking a screenshot of the listing page.
     - Mercari: `https://static.mercdn.net/item/detail/orig/photos/<item_id>_<n>.jpg`
     - Rakuma: `https://img.fril.jp/img/<id>/l/<id>.jpg`
     - If the shell cannot reach the image host, open the image in a browser and export it with a canvas, as described in `references/method.md`.
   - **First check that the test photo is not just PSA's own image.** PSA's image has a flat grey studio background, perfectly frontal framing and no glare. A seller who only posts PSA's images has proven nothing; tell the user that and ask for a real photo.
2. **Run** (Python 3, `pip install -r requirements.txt`):
   ```bash
   python skills/psa-label-alignment/scripts/psa_label_check.py \
       --ref psa_front.png --test listing_front.jpg \
       [--test-back listing_back.jpg --cert 123456789] [--ignore-cert-line] \
       --out out/
   ```
   - If the red label frame isn't found (exit 3), pass `--ref-corners` / `--test-corners "x,y;x,y;x,y;x,y"`, with the corners of the red frame given as top-left, top-right, bottom-right, bottom-left.
3. **Read `out/report.json`** and look at `out/displacement.png` and `out/overlay.png`. In the overlay, magenta is PSA, green is the test photo, and grey/black means they overlap.

   | verdict | max adjacent-line disagreement | meaning |
   |---|---|---|
   | `CONSISTENT` | ≤ 4 px | Text layout matches PSA. The label is very likely a genuine PSA print. |
   | `MISMATCH` | ≥ 8 px | Lines are typeset differently from PSA. This indicates a reprinted or counterfeit label. |
   | `INCONCLUSIVE` | between 4 and 8, or too few glyphs matched | Ask for a sharper, more frontal photo. |

   The thresholds are provisional. They were calibrated on the bundled examples, where the genuine slab measured 0.27 px and the fake 30.75 px.
4. **Report in the user's language.** Include:
   - the verdict and the key number;
   - one of the images;
   - the limits below;
   - how this result fits with the other evidence: seller history, price versus market, listing category, and photo quality.

## Limits (always tell the user) / 限制

- The check only covers the **label**. It cannot detect a genuine slab that was cracked open and had a different card put inside. For that, compare the card's position and print details against PSA's image.
- A `CONSISTENT` result plus a valid QR code shows that the photographed slab matches the cert. It does not guarantee that the seller will ship that slab.
- It needs a real, reasonably sharp photo. Heavy glare or blur over the text gives `INCONCLUSIVE`.
- It measures horizontal layout only, and is built for the standard red-bordered PSA label.

## Files

- `scripts/psa_label_check.py`: the CLI. Exit codes: 0 consistent, 1 mismatch, 2 inconclusive, 3 error.
- `references/method.md` / `references/method.zh-TW.md`: the algorithm, calibration data, image-acquisition tips and other physical checks.
- `../../examples/`: two worked cases, a suspected fake and a genuine control, with their outputs.

## 中文速查

1. 準備兩張正面圖：PSA 官網證書頁的圖，以及賣家自己拍的原圖。標籤寬度最好有 300px 以上。
2. 執行上面的指令。
3. 判讀：
   - `CONSISTENT`（≤4px）：字距跟 PSA 官方一致。
   - `MISMATCH`（≥8px）：排版不同，假標籤的機率很高。
   - `INCONCLUSIVE`：請賣家補一張更正面、更清楚的照片。
4. 回報時說明：只驗證標籤，抓不到換卡。QR code 有效不代表是真的。
