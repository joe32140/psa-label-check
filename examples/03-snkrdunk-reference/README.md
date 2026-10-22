# Example 03: genuine PSA 9, checked against SNKRDUNK references / 範例 03：用 SNKRDUNK 參考圖驗證的真品 PSA9

**Card:** 2021 Pokémon Japanese SWSH #089 FA/Leafeon VMAX (Eevee Heroes, HR), PSA 9. Cert number 153427845.

This example uses **no PSA cert image**. The references are photos of other PSA-graded copies of the same card, sold through SNKRDUNK and authenticated there. They are bundled in [`../snkrdunk_refs/leafeon-vmax-hr/`](../snkrdunk_refs/leafeon-vmax-hr/), and `refs.json` lists their listing URLs.

本範例**完全不用 PSA 官網圖**，參考圖是同一張卡、其他在 SNKRDUNK 成交並經過鑑定的 PSA 卡殼照片，放在 [`../snkrdunk_refs/leafeon-vmax-hr/`](../snkrdunk_refs/leafeon-vmax-hr/)，來源網址記在 `refs.json`。

## Listing context / 商品背景

**English**

- The listing is on Mercari, priced at ¥52,222. SNKRDUNK's recent PSA 9 sales were ¥49,800–60,000.
- The seller has 94 ratings and has verified their identity. They say they submitted the card to PSA themselves.
- The photos are real photos on an Eevee playmat, showing the front and the back.

**中文**

- Mercari 上的商品，售價 ¥52,222。SNKRDUNK 近期 PSA9 成交價是 ¥49,800–60,000。
- 賣家 94 個評價，已做身分驗證，說明是自己送 PSA 鑑定的。
- 照片是在伊布桌墊上拍的實拍，有正反面。

## Command / 指令

```bash
# how the references were fetched (live data changes over time)
python skills/psa-label-alignment/scripts/snkrdunk_refs.py --search "089/069"
python skills/psa-label-alignment/scripts/snkrdunk_refs.py --apparel-id 93023 --out refs/

# the bundled run
python skills/psa-label-alignment/scripts/psa_label_check.py \
  --ref examples/snkrdunk_refs/leafeon-vmax-hr/ref_*.jpg --description-only \
  --test examples/03-snkrdunk-reference/listing_front.jpg \
  --test-back examples/03-snkrdunk-reference/listing_back.jpg --cert 153427845 \
  --out examples/03-snkrdunk-reference/output
```

`output/report.json` has the combined result and `per_reference`. Full images are kept for the best-matching reference (`output/ref_3/`); the others keep only `displacement.png`.

## Result / 結果

**English**

- **`CONSISTENT`.** The label matches all 4 references: 0.19, 0.38, 0.52 and 0.63 px. Three are PSA 9 and one is PSA 10; `--description-only` makes the grade column irrelevant.
- The back QR code decodes to `https://www.psacard.com/cert/153427845/`, which matches the cert on the label.
- Without `--description-only`, the PSA 10 reference gives `MISMATCH` (27 px), entirely from the grade column ("MINT 9" vs "GEM MT 10"). This is why the flag is needed for references of another grade.
- With 8 fresh SNKRDUNK references fetched on 2026-10-22, the result was also `CONSISTENT` (3 usable references matched at 0.18–0.63 px; 3 photos were unusable).
- **Conclusion:** the label is very likely a genuine PSA print. The price and seller history fit.

**中文**

- **結果：一致（`CONSISTENT`）。** 跟 4 張參考圖都一致：0.19、0.38、0.52、0.63px。其中三張是 PSA9、一張是 PSA10；加了 `--description-only` 就不受等級那一欄影響。
- 背面 QR code 解出 `https://www.psacard.com/cert/153427845/`，跟標籤上的編號一致。
- 如果不加 `--description-only`，PSA10 的參考圖會判成不符（27px），差異全部來自等級那一欄（"MINT 9" 對 "GEM MT 10"）。所以參考圖等級不同時一定要加這個參數。
- 2026-10-22 重新抓 8 張 SNKRDUNK 參考圖再跑一次，結果也是一致（3 張可用的參考圖都一致，0.18–0.63px；另有 3 張照片無法使用）。
- **結論：** 很可能是 PSA 原廠標籤，價格和賣家紀錄也都正常。
