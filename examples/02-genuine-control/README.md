# Example 02: genuine control / 範例 02：真品對照組

**Card:** 2020 Pokémon Japanese S-P #144 Kanazawa's Pikachu, PSA 10. Cert number 161870798.

## Listing context / 商品背景

**English**

- The listing is on Mercari, priced at ¥59,999. That is within the market range for this card.
- The seller has more than 1,000 ratings, has verified their identity, and is at seller level 9.
- The seller openly discloses a light surface scratch on the card.
- The photo is a real photo, taken at an oblique angle on a wooden table. The label is only about 420 px wide, which makes this a deliberately harder test.

**中文**

- Mercari 上的商品，售價 ¥59,999，在這張卡的行情範圍內。
- 賣家有 1,000 多個評價，已做身分驗證，出品者等級 9。
- 賣家主動說明卡面有一道輕微刮痕。
- 照片是在木頭桌面上斜著拍的實拍，標籤只有大約 420px 寬，等於刻意用比較難的條件來測試。

## Command / 指令

```bash
python skills/psa-label-alignment/scripts/psa_label_check.py \
  --ref examples/02-genuine-control/psa_front.png \
  --test examples/02-genuine-control/listing_front.jpg \
  --test-back examples/02-genuine-control/listing_back.jpg --cert 161870798 \
  --out examples/02-genuine-control/output
```

## Result / 結果

**English**

- **`CONSISTENT`.** The worst adjacent-line disagreement is **0.34 px**. 71 glyphs were matched, with a median correlation of 0.94.
- Before the global correction, the four lines followed the same smooth U-shaped curve, which is ordinary lens distortion. After it, every line sits within ±0.3 px.
- The back QR code could not be decoded from this oblique photo. That does not affect the label check.
- Cross-check: comparing this photo against PSA's image of a *different* cert of the same card (`--ignore-cert-line`) also gives `CONSISTENT`, at 0.21 px. PSA typesets the same description identically.
- Against SNKRDUNK references instead (3 authenticated PSA 10 photos in [`../snkrdunk_refs/kanazawa-pikachu-psa10/`](../snkrdunk_refs/kanazawa-pikachu-psa10/), `--description-only`): **`CONSISTENT`**, matching all 3 at 0.24–0.49 px.

**中文**

- **結果：一致（`CONSISTENT`）。** 相鄰兩行最大差距 **0.34px**，比對到 71 個字，相關係數中位數 0.94。
- 做整體校正之前，四行字的位移落在同一條平滑的 U 形曲線上，這是一般的鏡頭變形。校正之後，每一行都在 ±0.3px 以內。
- 這張是斜拍，背面的 QR code 解不出來，但不影響標籤的判斷。
- 交叉驗證：拿同一款卡、另一張證書的 PSA 官方圖來比，加上 `--ignore-cert-line`，結果也是一致，差距 0.21px。PSA 對同一張卡的說明文字排版完全一樣。
- 改用 SNKRDUNK 參考圖（[`../snkrdunk_refs/kanazawa-pikachu-psa10/`](../snkrdunk_refs/kanazawa-pikachu-psa10/) 裡 3 張已鑑定的 PSA10，加 `--description-only`）：**一致**，3 張都一致，0.24–0.49px。
