# genecr — AI 文件生成 Pipeline

## 專案目標

輸入一段功能需求（brief），自動產出 7 份文件：
`spec-basic` → `spec-advanced` → `assets` → `bdd` → `scrum` → `prototype` → `docs`

每個 step = **AI 生成 input.json** → **schema 驗證** → **review_loop 審查/修正** → **render 產出 .md/.html**

---

## 資料流

```
brief.txt
  └─ pipeline.py
       ├─ call_ai()        → <step>.input.json   （AI 生，schema gate 守）
       ├─ review_loop.py   → 審查 / fixer 修正
       ├─ cross_check.py   → 跨 step 數量一致性
       └─ render.py        → .md / .html 產出
```

**SSOT**（同一數字只有一個來源）：
- 美術資源數量 → `spec-basic.dryrun.resource_counts`
- 技術規模估算 → `spec-basic.dryrun.tech_counts`
- 驗收條目數   → `spec-basic.dryrun.test_counts.acceptance_criteria`

---

## 目錄對應表（查問題直接開）

| 問題 | 檔案 |
|---|---|
| AI 生的內容方向錯、欄位漏 | `templates/prompts/<step>.prompt.md` |
| schema 驗證失敗 | `templates/schemas/<step>.schema.json` |
| reviewer 擋住 / 規則邏輯 | `templates/review/<step>.review.md` |
| 跨 step 數量不一致 | `tools/renderer/cross_check.py` |
| pipeline 流程 / step 順序 | `pipeline.json` + `tools/renderer/pipeline.py` |
| render HTML/MD 產出壞掉 | `tools/renderer/render.py` |
| wireframe DSL 用法 | `templates/wireframe-dsl.md` |
| review/fix loop 卡住 | `tools/renderer/review_loop.py` |
| 路徑 / env 設定 | `bin/genecr-env.sh`（GENECR_DIR SSOT） |

---

## AI 行為規則（必須遵守）

- 改任何規則 → prompt + schema + review 三邊同步，缺一邊不算完成
- 改 `tools/renderer/` → 必須先寫 test 跑紅，再實作到綠，不准跳過
- 跨文件數量一致性 → 程式 parse + count，不准 AI 自己數
- 修 bug → 先找同類所有案例的根因，不准 user 報一個修一個
- 不動 `tools/bin/` → 那是 build.sh deploy 的產物，直接編輯無效
- 不讀下游 → 任何 step 執行時，即使下游文件已存在也不能讀
- 沒有授權不動程式 → 討論時只分析，user 確認才動手

## 三層必須同步

任何規則改動必須三邊一起更新，缺一邊就是 bug：

```
templates/prompts/<step>.prompt.md   ← AI 生成時遵守
templates/schemas/<step>.schema.json ← 機器驗證
templates/review/<step>.review.md    ← reviewer 審查
```

---

## 開發流程

```bash
# 修改 tools/renderer/ 後：
cd tools/renderer && python -m pytest tests/ -q   # 跑測試
bash build.sh                                      # 部署到 tools/bin/
git add . && git commit && git push
# 然後在 Claude Code 執行 /genecr-upgrade
```

**禁區**：
- `tools/bin/` — 不要直接編輯，由 `build.sh` 從 `tools/renderer/` 複製
- `gui/`, `installer/` — 副產品，不影響主 pipeline
- step 隔離：每個 step 只能讀自己和上游，不能讀下游

---

## step 隔離規則

| step | 可讀上游 |
|---|---|
| spec-basic | （無）|
| spec-advanced | spec-basic |
| assets | spec-basic, spec-advanced |
| bdd | spec-basic, spec-advanced |
| scrum | spec-basic, spec-advanced, bdd |
| prototype | spec-basic, spec-advanced, bdd, scrum |
| docs | 全部 |

`cross_check.py` 和 `review_loop.py` 執行時只傳對應上游，不傳下游。
重跑某個 step 時，即使下游文件已存在，也絕對不能讀——否則等於用答案倒推，污染該 step 的獨立產出。
