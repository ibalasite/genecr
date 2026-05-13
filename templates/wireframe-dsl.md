# Wireframe DSL — genecr 低保真線框圖規範

> **必讀**：所有 `*-spec-basic.md`（企畫版）的「介面說明」章節都必須附 wireframe。
> 規則來源：`preview.html`。本檔為 single source of truth；不得自創 class / 色票。

---

## 1. 色票（CSS Custom Properties）

完全沿用 `preview.html`：

```css
:root {
  --ink:    #1f2937;   /* 主邊框、強調文字、active 狀態 */
  --muted:  #6b7280;   /* 次要文字、placeholder 標籤 */
  --line:   #c7cdd6;   /* 弱邊框、分隔線 */
  --soft:   #f6f7f9;   /* 弱背景、skeleton 條紋淺色 */
  --panel:  #ffffff;   /* 主容器底 */
}
```

**禁止**：彩色、品牌色、漸層、陰影 > 18px。線稿就是線稿。

---

## 2. 容器層級

### 2.1 Desktop / Admin 線稿（沿用 preview.html）

```
.wireframe                          外框（2px solid --ink + 圓角 20px）
  ├─ header                         頂部 logo + nav + action
  ├─ .layout (grid 240px | 1fr)
  │   ├─ aside                      左側導覽
  │   │   └─ .side-item[.active]
  │   └─ main                       主內容
  │       ├─ .title-row             標題 + skeleton-pill
  │       ├─ .kpi-row               KPI 卡片群
  │       ├─ .grid                  圖表 + 列表
  │       │   ├─ .chart > .bars > .bar
  │       │   └─ .card > .list-line > .dot + .line
  │       └─ .table-wrap > table
```

### 2.2 Mobile Game 線稿（**本檔新增**）

```
.wf-mobile                          手機外框（375 × 812 視覺）
  ├─ .wf-statusbar                  狀態列（時間、訊號、電量 placeholder）
  ├─ .wf-appbar                     遊戲頂部（返回、標題、餘額/設定）
  ├─ .wf-banner                     活動橫幅（可選）
  ├─ .wf-marquee                    滾動播報條
  ├─ .wf-stage                      主舞台（輪盤/老虎機/卡牌等）
  │   └─ .wf-wheel  /  .wf-slot  /  .wf-board
  ├─ .wf-actionbar                  主操作列（SPIN / 確定 / 領取）
  ├─ .wf-info                       資訊列（票券、倒數、計分）
  ├─ .wf-shortcuts                  快捷入口（簽到、任務、VIP）
  └─ .wf-bottomnav                  底部固定導覽（可選）
```

### 2.3 Modal / Popup 線稿

```
.wf-modal                           外框（2px solid --ink + 圓角 16px）
  ├─ .wf-modal-icon                 主圖示位置（虛線方框）
  ├─ .wf-modal-title
  ├─ .wf-modal-body
  ├─ .wf-modal-meta                 流水提示 / 條款（細字）
  └─ .wf-modal-actions              按鈕群
```

---

## 3. Primitives（DSL 元件）

每個 primitive 都是 1 個 class，**只允許**從這張表選用：

| Class | 用途 | 視覺 |
|-------|------|------|
| `.wf-frame` | 任何外框容器 | 2px solid --ink，圓角 16-20px |
| `.wf-panel` | 內層白底卡 | 1.8px solid --line，圓角 12px |
| `.wf-section-title` | 區塊標題 | 800 weight，14-18px |
| `.wf-pill` | 標籤/狀態膠囊 | 圓角 999px，1.5px --line，inline-block |
| `.wf-pill.is-active` | 強調膠囊 | 邊框換 --ink，font-weight 700 |
| `.wf-btn` | 一般按鈕 | min-h 34px，圓角 999px，1.8px --line |
| `.wf-btn-primary` | 主按鈕 | 邊框 --ink + 700 weight + 底 --soft |
| `.wf-input` | 輸入框 | 1.5px --line，圓角 8px，min-h 36px，內顯 placeholder |
| `.wf-skeleton-pill` | 載入中佔位 | 條紋背景（--soft / #fff repeating-linear-gradient 10px） |
| `.wf-skeleton-line` | 一條占位線 | h 16px，邊框 1.5px --line |
| `.wf-skeleton-block` | 塊狀占位 | --soft 底，1.8px --line，圓角 12px |
| `.wf-dot` | 圓點 | 18×18，1.8px --ink，圓 |
| `.wf-divider` | 分隔線 | 1.5px solid --line |
| `.wf-icon-slot` | 圖示占位 | 虛線 1.5px --line，正方形，placeholder 文字「IMG」 |
| `.wf-required` | 必填星號 | 紅色 *（唯一允許的非黑灰色） |
| `.wf-helper` | 輔助文字 | --muted，12px |
| `.wf-badge` | 數字 / 角標 | 圓 22×22，1.8px --ink，置中數字 |
| `.wf-segment` | 輪盤 / 圓餅段 | 1.8px --ink，內含 .wf-icon-slot + 文字 |
| `.wf-bar` | 直條圖長條 | 1.8px --ink，底 --soft，圓角頂 |
| `.wf-line-row` | 列表單行 | display:flex，含 .wf-dot + 文字 + .wf-skeleton-line |

---

## 4. 輪盤專屬 primitives（每日幸運輪 / 大轉盤類功能）

| Class | 用途 |
|-------|------|
| `.wf-wheel` | 輪盤容器（外圓 1.8px --ink，內含 N 段 .wf-segment） |
| `.wf-wheel-pointer` | 固定指針三角形（純線稿，--ink 邊框） |
| `.wf-wheel-hub` | 中央 SPIN 按鈕（圓，--ink 邊框，內字 SPIN） |
| `.wf-wheel-rim` | 輪盤外圈裝飾點（可選，N 個 .wf-dot 圍繞） |

---

## 5. 必畫畫面清單

每個功能的 `spec-basic.md` 介面說明章節**至少**畫以下 4 張線稿：

1. **主畫面**（IDLE 狀態）— 進入頁就看到的畫面
2. **互動中**（LOADING / SPINNING / 動作觸發中）— 占位 + spinner skeleton
3. **結果彈窗**（中獎 / 完成 / 失敗）— modal 線稿
4. **無資料 / 倒數 / 邊界**（票券=0、活動未開始、帳號凍結）— 狀態切換

額外加分：
- 後台 CMS 線稿（如果功能有後台）
- 我的紀錄 / History 列表線稿

---

## 6. 圖文並排規則

**每個線稿旁邊必須有對應的功能說明**。建議用 2 欄表格：

```markdown
| 線稿 | 功能說明 |
|------|---------|
| (附 wf-frame HTML 區塊) | 1. **頂部 header**：返回 / 標題 / 餘額<br>2. **輪盤**：12 段，中央 SPIN<br>3. **資訊列**：票券、今日已轉、倒數 |
```

或在 `docs.html` 用 2 欄 grid layout。

---

## 7. 在 spec-basic.md 中嵌入線稿的兩種寫法

### 寫法 A：純 ASCII（最低標，給純文字環境用）

```
┌───────────────────────────────────────┐
│ ← 每日幸運輪    NT$ 1,234   ⚙        │
├───────────────────────────────────────┤
│  🎉 W***86 剛中得 NT$1,000 ・ 滾動中  │
├───────────────────────────────────────┤
│                                       │
│            ▼ pointer                  │
│          ╱─────────╲                  │
│         │  ┌─────┐  │                 │
│         │  │SPIN │  │   12 段輪盤    │
│         │  └─────┘  │                 │
│          ╲─────────╱                  │
│                                       │
├───────────────────────────────────────┤
│  🎫 票券：3   今日已轉：0   06:42:11  │
├───────────────────────────────────────┤
│ [📅 簽到 +1票] [✅ 任務 +1票] [💎VIP] │
└───────────────────────────────────────┘
```

### 寫法 B：HTML wireframe 區塊（**推薦**，docs.html 直接顯示）

```html
<div class="wf-frame wf-mobile" style="width:375px;margin:auto">
  <div class="wf-appbar">
    <span class="wf-pill">←</span>
    <span class="wf-section-title">每日幸運輪</span>
    <span class="wf-helper">NT$ 1,234</span>
  </div>
  <div class="wf-marquee"><span class="wf-skeleton-line"></span></div>
  <div class="wf-stage">
    <div class="wf-wheel">
      <!-- 12 段 -->
      <div class="wf-segment">10K</div>
      <!-- … -->
      <div class="wf-wheel-hub">SPIN</div>
      <div class="wf-wheel-pointer"></div>
    </div>
  </div>
  <div class="wf-info">
    <span class="wf-pill is-active">🎫 3</span>
    <span class="wf-pill">今日 0</span>
    <span class="wf-pill">06:42:11</span>
  </div>
  <div class="wf-shortcuts">
    <button class="wf-btn">📅 簽到 +1</button>
    <button class="wf-btn">✅ 任務 +1</button>
    <button class="wf-btn">💎 VIP</button>
  </div>
</div>
```

> 寫法 B 需要在 docs.html 內嵌 wireframe CSS（見 `wireframe-snippets.html` 第 1 節）。

---

## 8. 自我檢查（產出 spec-basic.md 前必過）

- [ ] 介面說明章節**至少 4 張線稿**（主畫面 / 互動中 / 結果彈窗 / 邊界）
- [ ] 每張線稿**只用本檔列出的 class**，沒有自創
- [ ] 色票**只有** --ink / --muted / --line / --soft / --panel + 紅色必填星號
- [ ] 圖文並排：每張線稿旁有條列功能說明
- [ ] `docs.html` 企畫版分頁**有同步顯示**（不要只在 .md，HTML 也要看得到）
- [ ] 線稿是低保真：**沒有彩色、沒有陰影、沒有 photographic asset**

---

## 9. 反例（不要這樣做）

❌ **不要**用彩色塊代替 placeholder（線稿就是線稿，要黑白）
❌ **不要**畫完整 hi-fi mockup（那是美術的事）
❌ **不要**用 emoji 取代 .wf-icon-slot（emoji 是占位內的標籤，不是圖示本體）
❌ **不要**在線稿裡寫真實 i18n 文案（用 `[Label]` 或 placeholder）
❌ **不要**自創 class（如 `.my-special-card`），所有元件都要從第 3 節挑

---

*Wireframe DSL v1.0 ｜ 由 GeneCR 維護 ｜ 對應 wireframe-snippets.html*
