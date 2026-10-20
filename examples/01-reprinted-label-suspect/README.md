# Example 01: suspected reprinted label / 範例 01：疑似重印的假標籤

**Card:** 2020 Pokémon Japanese S-P #144 Kanazawa's Pikachu, PSA 10. Cert number 134699919.

## Listing context / 商品背景

**English**

- The listing is on Mercari, priced at ¥43,500.
- Recent PSA 10 sales of this card were about ¥56,000–68,000.
- The seller has 0 ratings and no identity verification.
- The item went up only hours earlier.
- It is filed under "pill cases", and the first line of the description talks about a pill case.
- The description does not give the cert number.
- The seller's photos are real photos on black cloth, so they are not PSA's images.

**中文**

- Mercari 上的商品，售價 ¥43,500。
- 這張卡的 PSA10 近期成交價大約 ¥56,000–68,000。
- 賣家 0 評價，沒有做身分驗證。
- 商品才剛上架幾個小時。
- 分類放在「ピルケース（藥盒）」，說明第一句也在寫藥盒。
- 說明裡沒有寫鑑定編號。
- 照片是黑布背景的實拍，不是 PSA 官網圖。

## Files / 檔案

| file | what |
|---|---|
| `psa_front.png`, `psa_back.png` | PSA official cert images / PSA 官方證書圖 |
| `listing_front.jpg`, `listing_back.jpg` | seller's photos, originals from the listing / 賣家原圖 |
| `output/` | result of the command below / 下方指令的輸出 |

```bash
python skills/psa-label-alignment/scripts/psa_label_check.py \
  --ref examples/01-reprinted-label-suspect/psa_front.png \
  --test examples/01-reprinted-label-suspect/listing_front.jpg \
  --test-back examples/01-reprinted-label-suspect/listing_back.jpg --cert 134699919 \
  --out examples/01-reprinted-label-suspect/output
```

## Result / 結果

**English**

- **`MISMATCH`.** The worst adjacent-line disagreement is **30.75 px**. 91 glyphs were matched, with a median correlation of 0.88.
- At x ≈ 300, line 2 ("KANAZAWA'S PIKACHU") is shifted about −15 px, while line 3 ("P.M. CNTR.KANAZAWA OPEN.") directly below it is shifted about +19 px. One smooth camera or lens distortion cannot do this, so the description lines were typeset differently from PSA's label.
- The QR code on the back decodes to `https://www.psacard.com/cert/134699919/`. That is expected even for a fake, because counterfeiters copy real QR codes.
- Secondary check: the card's position relative to the label differs from PSA's image by roughly 2 mm, on both the front and the back.
- **Conclusion:** this is very likely a counterfeit slab that reuses a real cert number.

**中文**

- **結果：不符（`MISMATCH`）。** 相鄰兩行最大差距 **30.75px**，比對到 91 個字，相關係數中位數 0.88。
- 在水平位置約 300 的地方，第 2 行往左偏約 15px，正下方的第 3 行卻往右偏約 19px。相機或鏡頭的整體變形做不出這種效果，代表說明文字的排版跟 PSA 原廠不同。
- 背面的 QR code 解得出來，也連到正確的證書頁。但這不能證明是真的，假卡殼通常直接複製真的 QR code。
- 輔助檢查：卡片在殼裡相對標籤的位置，跟 PSA 官方圖比偏了大約 2mm，正反兩面都一樣。
- **結論：** 很可能是套用真編號的假卡殼。
