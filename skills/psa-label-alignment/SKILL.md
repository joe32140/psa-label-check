---
name: psa-label-alignment
description: Check whether a PSA-graded card slab in a seller's photo has a genuine PSA label by comparing the label's text layout, glyph by glyph, against photos of genuine slabs of the same card from SNKRDUNK (default) or PSA's cert image. Use when someone asks if a PSA slab (Pokémon, sports, any TCG) on Mercari, Rakuma, eBay, Yahoo Auctions etc. is real or fake, or wants a slab photo compared with genuine ones.
---

# PSA label alignment check / PSA 標籤字距比對

Counterfeit PSA slabs usually copy a **real** cert number, QR code and PSA's
official photo, so "the cert number looks up fine" proves nothing. What fakers
rarely get right is PSA's exact typesetting. This skill measures it.

**Principle.** Two photos of labels printed from the *same typesetting* can
differ only by one smooth, whole-label distortion (camera angle, lens). Every
text line shifts together. A re-typeset label shows **line-specific** shifts:
neighbouring lines drift in opposite directions at the same x position.

**原理：** 同一份排版印出來的標籤，翻拍只會整體平滑變形，每一行一起移動；重新排版印的假標籤，相鄰兩行會在同一位置往不同方向偏。

## Workflow

1. **Get the seller's photo (test).** Use the seller's own photo of the slab front at full resolution, with the label at least ~300 px wide. Download the original file rather than taking a screenshot of the listing page.
   - Mercari: `https://static.mercdn.net/item/detail/orig/photos/<item_id>_<n>.jpg` (n = 1, 2, … until 403/404)
   - Rakuma: the `https://img.fril.jp/img/<a>/l/<b>.jpg` URLs in the item page HTML
   - If the shell cannot reach the image host, open the image in a browser and export it with a canvas, as described in `references/method.md`.
   - **Check that the test photo is not just PSA's own image.** PSA's image has a flat grey studio background, perfectly frontal framing and no glare. A seller who only posts PSA's images has proven nothing; tell the user that and ask for a real photo.
   - Note the card (set, number, name) and grade from the label.
2. **Get references from SNKRDUNK (default).** PSA's cert page is usually behind a bot check, so use photos of genuine slabs of the same card from SNKRDUNK instead. SNKRDUNK authenticates every sale, and its pages and JSON work over plain HTTP.
   ```bash
   # find the card's SNKRDUNK id: search by card number or Japanese name
   python skills/psa-label-alignment/scripts/snkrdunk_refs.py --search "089/069"
   # download 8 PSA-graded references (any grade), authenticated sales first
   python skills/psa-label-alignment/scripts/snkrdunk_refs.py --apparel-id 93023 --out refs/
   ```
   - Pick the search hit whose name matches the card exactly (set and number).
   - If the test listing is itself on SNKRDUNK, pass `--exclude-listing <id>`.
   - **Alternative:** if you or the user have PSA's cert image for this exact cert, use it as the single `--ref` and drop `--description-only`. That also compares the cert-number row.
3. **Run** (Python 3, `pip install -r requirements.txt`):
   ```bash
   python skills/psa-label-alignment/scripts/psa_label_check.py \
       --ref refs/ref_*.jpg --description-only \
       --test listing_front.jpg [--test-back listing_back.jpg --cert 123456789] \
       --out out/
   ```
   - `--description-only` compares only the left description block. It skips the card number, grade and cert column, so references of any cert and grade work.
   - With several `--ref`, each is compared on its own (`out/ref_N/`) and the results are combined. The test counts as `CONSISTENT` if it matches **any** usable reference, and as `MISMATCH` only if it matches **none** of at least two. This is because PSA has re-typeset some cards' labels between printing eras (e.g. "S-P" vs "S – P"), so one genuine reference from another era can disagree.
   - References whose photo is unusable (sticker over the label, frame not found) show up as `ERROR`/`INCONCLUSIVE` in `per_reference` and are ignored.
   - If the test label's red frame isn't found (exit 3), pass `--test-corners "x,y;x,y;x,y;x,y"` (top-left, top-right, bottom-right, bottom-left of the red frame, in pixels).
4. **Read `out/report.json`**: `verdict`, `max_adjacent_line_disagreement_px`, `message` and `per_reference`. Look at `displacement.png` and `overlay.png` for the best reference (its folder is in `out`). In the overlay, magenta is the reference, green is the test photo, and grey/black means they overlap.

   | verdict | max adjacent-line disagreement | meaning |
   |---|---|---|
   | `CONSISTENT` | ≤ 4 px | Text layout matches a genuine PSA label. The label is very likely a genuine PSA print. |
   | `MISMATCH` | ≥ 8 px | Lines are typeset differently from every genuine reference. This indicates a reprinted or counterfeit label. |
   | `INCONCLUSIVE` | between 4 and 8, too few glyphs, or too few usable references | Ask for a sharper, more frontal photo, or fetch more references. |

   **Before reporting `MISMATCH` against SNKRDUNK references,** open the test's `label_test.png` and a reference's `label_ref.png` and compare punctuation and spacing ("S-P" vs "S – P", "HEROES-HYPER" vs "HEROES – HYPER"). If the test looks like a different era from every reference, fetch more (`--n 20`) and run again. A genuine older slab only matches references from its own era.

   The thresholds are provisional. On the bundled examples, genuine slabs measure 0.2–0.6 px against SNKRDUNK references and the fake 22 px.
5. **Report in the user's language.** Include:
   - the verdict, the key number and how many references matched;
   - one of the images;
   - the limits below;
   - how this result fits with the other evidence: seller history, price versus market (SNKRDUNK prices are a good benchmark), listing category, photo quality, and whether the cert number or QR is hidden.

## Limits (always tell the user) / 限制

- The check only covers the **label**. It cannot detect a genuine slab that was cracked open and had a different card put inside. For that, compare the card's position and print details against reference photos.
- With SNKRDUNK references and `--description-only`, the cert-number row is not compared. Check the cert number separately (QR via `--test-back --cert`, or the PSA cert page). If the seller has hidden the cert number, say so.
- A label printed from a scan of a genuine label would also pass. A `CONSISTENT` result plus a valid QR code shows the photographed slab matches a genuine typesetting. It does not guarantee the seller will ship that slab.
- It needs a real, reasonably sharp photo. Heavy glare or blur over the text gives `INCONCLUSIVE`.
- It measures horizontal layout only, and is built for the standard red-bordered PSA label.

## Files

- `scripts/snkrdunk_refs.py`: finds the card on SNKRDUNK and downloads reference photos plus `refs.json` (listing URLs, grade, status).
- `scripts/psa_label_check.py`: the check. Exit codes: 0 consistent, 1 mismatch, 2 inconclusive, 3 error.
- `references/method.md` / `references/method.zh-TW.md`: the algorithm, calibration data, image-acquisition tips and other physical checks.
- `../../examples/`: three worked cases (a suspected fake, two genuine) and bundled SNKRDUNK references.

## 中文速查

1. 下載賣家自己拍的正面原圖，標籤寬度最好有 300px 以上。
2. 用 `snkrdunk_refs.py --search` 找到這張卡在 SNKRDUNK 的 ID，再下載 8 張已鑑定成交的 PSA 卡殼照片當參考圖。
3. 執行 `psa_label_check.py --ref refs/ref_*.jpg --description-only --test ...`。
4. 判讀：
   - `CONSISTENT`（≤4px）：跟至少一張真品參考圖的排版一致。
   - `MISMATCH`（≥8px）：跟所有可用的參考圖都不同，假標籤的機率很高。
   - `INCONCLUSIVE`：照片不夠清楚，或可用的參考圖太少。
5. 回報時說明：只驗證標籤，抓不到換卡；`--description-only` 不比對鑑定編號那一行；QR code 有效不代表是真的。
