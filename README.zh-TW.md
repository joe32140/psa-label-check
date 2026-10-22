# PSA 標籤字距比對（PSA Label Alignment Check）

[English →](README.md)

這是一個 agent skill 加命令列工具，用來判斷**賣家照片裡的 PSA 卡殼標籤是不是 PSA 原廠印的**。做法是拿同一張卡的真品卡殼照片，逐字比對標籤的排版。參考圖預設來自 [SNKRDUNK（スニダン）](https://snkrdunk.com)：每筆交易都經過 SNKRDUNK 鑑定，而且 agent 抓得到，不像 PSA 官網常被機器人驗證擋住。手上有 PSA 官網證書圖的話也可以用。

假卡殼通常會照抄真的鑑定編號，QR code 也掃得到，賣家甚至直接拿 PSA 官網的照片來用。所以「編號查得到」什麼都證明不了。仿冒業者最難做到的，是跟 PSA 一模一樣的字距排版。

![真品 vs 假品](docs/control_vs_suspect_zh.png)

## 原理

0. **抓參考圖：** `snkrdunk_refs.py` 會在 SNKRDUNK 找到這張卡，下載最多 8 張 PSA 卡殼的正面照，優先選已通過 SNKRDUNK 鑑定的交易。
1. **把標籤拉正：** 找出兩張圖標籤的紅色外框，各自拉正成 960 × 291 px。
2. **逐字找位置：** 用正規化互相關，在賣家的標籤裡找出 PSA 標籤上每一個字的位置，精確到次像素。
3. **去除整體變形：** 用一個整體的單應性矩陣消除拍攝角度和鏡頭變形，然後再量一次。
4. **比較相鄰兩行：** 看相鄰兩行在同一個水平位置的位移有沒有差別。
   - 同一張標籤翻拍：每一行一起移動，差距不到 1px。
   - 重新排版印的假標籤：各行往不同方向偏，差距達到幾十 px。
5. **多張參考圖投票：** 加上 `--description-only` 只比對左邊的說明文字，所以任何證書、任何等級的參考圖都能用。只要跟任何一張真品參考圖一致就是一致；跟全部都不同才是不符。因為 PSA 在不同時期會重新排版同一張卡的標籤，跟某一張不同時期的參考圖不一致是正常的。

| 結果 | 相鄰兩行最大差距 | 代表 |
|---|---|---|
| `CONSISTENT` 一致 | ≤ 4px | 排版跟 PSA 一致，很可能是 PSA 原廠標籤 |
| `MISMATCH` 不符 | ≥ 8px | 排版跟所有真品參考圖都不同，可能是重新印的假標籤 |
| `INCONCLUSIVE` 無法判斷 | 4–8px、比對到的字太少，或可用的參考圖太少 | 請賣家補一張更正面、更清楚的照片，或多抓幾張參考圖 |

目前的校準結果：

| 比較的照片 | vs PSA 官方圖 | vs SNKRDUNK 照片（`--description-only`） |
|---|---|---|
| 真品金澤皮卡丘 PSA10 | **0.34px** | **0.24px**（3/3 張一致） |
| 可疑的金澤皮卡丘 PSA10 | **30.75px** | **22.06px**（0/3 張一致） |
| 真品葉伊布 VMAX PSA9 | – | **0.19px**（4/4 張一致） |

## 使用方式

```bash
pip install -r requirements.txt
S=skills/psa-label-alignment/scripts

# 1. 在 SNKRDUNK 找這張卡（用卡號或日文卡名），再下載參考圖
python $S/snkrdunk_refs.py --search "089/069"
python $S/snkrdunk_refs.py --apparel-id 93023 --out refs/

# 2. 拿賣家照片跟參考圖比
python $S/psa_label_check.py --ref refs/ref_*.jpg --description-only \
    --test 賣家正面照.jpg [--test-back 賣家背面照.jpg --cert 鑑定編號] --out out/
```

有這張證書的 PSA 官網圖的話，可以把它當成唯一的 `--ref`，不加 `--description-only`，這樣連鑑定編號那一行也會比對。

- **`--description-only`：** 只比對左邊的說明文字，不比卡號、等級和鑑定編號那一欄。參考圖是不同證書或不同等級時（例如 SNKRDUNK 的照片）要加。
- **`--ignore-cert-line`：** 只略過最下面那一行鑑定編號。參考圖是不同證書、但同一個等級時可以用。
- **偵測不到紅框時：** 用 `--ref-corners` 或 `--test-corners "x,y;x,y;x,y;x,y"` 手動指定紅框四個角，順序是左上、右上、右下、左下。

## 安裝成 agent skill

| Agent | 安裝方法 |
|---|---|
| Claude Code | 把 `skills/psa-label-alignment` 複製到 `~/.claude/skills/`，或專案裡的 `.claude/skills/` |
| Claude App | 把資料夾壓成 zip，上傳成自訂 skill |
| Codex、Cursor、Gemini CLI 等其他 agent | 把這個 repo 加進工作區，它們會讀 [`AGENTS.md`](AGENTS.md) |

只要能跑 Python 指令、讀 JSON，任何 agent 都可以用。

## 範例

| 範例 | 情況 | 結果 |
|---|---|---|
| [01-reprinted-label-suspect](examples/01-reprinted-label-suspect/) | 0 評價賣家，價格約行情七成，商品分類亂填 | **不符** 30.75px |
| [02-genuine-control](examples/02-genuine-control/) | 1,000 多個評價的賣家，價格在行情內 | **一致** 0.34px |
| [03-snkrdunk-reference](examples/03-snkrdunk-reference/) | 94 個評價的賣家自己送鑑的 PSA9，價格在行情內，只用 SNKRDUNK 參考圖 | **一致** 0.19px（4/4） |

範例 01、02 也會跟 [`examples/snkrdunk_refs/`](examples/snkrdunk_refs/) 裡附的 SNKRDUNK 參考圖比對。執行 `python tests/test_examples.py` 會全部跑一遍，不需要連網。

## 限制

- **只檢查標籤。** 如果是真的 PSA 卡殼被撬開、換了卡，這個工具抓不到。
- **需要賣家自己拍的照片。** 如果賣家只放 PSA 官網的圖，等於什麼都沒證明。
- **用 SNKRDUNK 參考圖時不比對鑑定編號那一行。** 鑑定編號要另外確認，例如用背面的 QR code（`--test-back --cert`）。
- 拿真標籤掃描後重印的假標籤，這個方法抓不到。
- SNKRDUNK 的參考圖是其他賣家的卡殼照片。工具會優先用已經過 SNKRDUNK 鑑定的，但還是要用多張，並看一下 `per_reference`。
- **閾值是暫定的。** 目前只用幾張卡校準，歡迎提供更多已知真假的案例。
- 只支援標準紅框的 PSA 標籤，也只量水平方向。
- 這是初步篩選的工具，不能取代正式鑑定。高價卡請使用平台的鑑定服務。
