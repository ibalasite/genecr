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

**只允許**從以下表選用 wf-* class。每個 primitive 對應一個 HTML element 或 UI pattern，class 名稱字串必須與 docs.html.tmpl 的 CSS rule 完全對應（沒對到 = 沒樣式）。

### 3.0 子排版規則（最重要）

- **`.wf-panel` 預設兒童垂直 stack**（flex column gap 8px）。需要橫排請包進 `.wf-row`。
- **`.wf-skeleton-{line,pill,block}` 是「空白占位」**，**禁止塞文字內容**。要文字行用 `.wf-line`；要段落用 `.wf-text`。違反此規則 reviewer R9 會擋。
- `<span>` 子元素直接放 panel 不會自動橫排，必須包 `.wf-row`（reviewer R10 會擋）。
- **Sandbox 原則**：所有 wireframe 永遠是「螢幕示意 sandbox」，**有最大寬度上限**，不應隨頁面寬度自適應：
  - `.wf-mobile` = 360px 寬（手機畫面）
  - `.wf-modal` = 300px 寬（彈窗）
  - `.wf-frame` = max 720px（通用螢幕外框，居中）
  - `.wf-desktop` = max 960px（後台/桌面畫面，居中）
  - 若要表達「100% 自適應 / fluid」，在 sandbox 內示意即可（如 `<div class="wf-mobile"><div style="width:100%">…</div></div>`），絕不可讓 wireframe 本身吃滿頁寬。

### 3.1 Container 結構（外框 + Mobile 容器 + Modal）

| Class | 用途 | 視覺 |
|---|---|---|
| `.wf-scope` | wireframe 最外層包裹（border-box 重置） | 必有 |
| `.wf-frame` | 通用外框容器 | 2px solid --ink，圓角 20px |
| `.wf-panel` | 白底卡片（默認垂直 stack） | 1.8px --line，圓角 12px，padding 12px |
| `.wf-mobile` | 手機外框（375px wide） | 含 statusbar/appbar/...組合 |
| `.wf-desktop` | 桌面外框 | 2px solid --ink，全寬 |
| `.wf-statusbar / .wf-appbar / .wf-banner / .wf-marquee / .wf-stage / .wf-info / .wf-actionbar / .wf-shortcuts / .wf-bottomnav` | Mobile 內部各區塊（依 2.2 樹狀順序） | 各有預定 layout |
| `.wf-sidebar / .wf-sidenav-item` | Desktop 左側導覽 + 項目 | aside 240px |
| `.wf-modal` | 彈窗外框 | 300px，2px --ink |
| `.wf-modal-icon / .wf-modal-title / .wf-modal-body / .wf-modal-meta / .wf-modal-actions` | 彈窗五件套 | 由上而下 |
| `.wf-empty` | 空狀態 | 居中 muted 文字 |

### 3.2 排版 / 列表 / 表格

| Class | HTML 對應 | 用途 |
|---|---|---|
| `.wf-row` | flex row container | **顯式橫排容器**，包多個 inline items |
| `.wf-list` | `<ul>/<ol>` | **列表容器**（flex column gap） |
| `.wf-line` | `<li>` / list item | **文字行 item**（裝文字的單行條目） |
| `.wf-text` | `<p>` | **純文字段落** |
| `.wf-link` | `<a>` | 連結樣式文字 |
| `.wf-table` | `<table>` | 表格容器 |
| `.wf-tr` | `<tr>` | 表格列 |
| `.wf-td` | `<td>` | 表格儲存格 |
| `.wf-divider` | `<hr>` | 分隔線 |
| `.wf-section-title` | `<h3>` | 區塊標題（800 weight 14-18px） |

### 3.3 Form 元件（對標 HTML form inputs）

| Class | HTML 對應 | 視覺 |
|---|---|---|
| `.wf-input` | `<input type="text/number/email">` | 圓角 8px，min-h 36px |
| `.wf-input-date` | `<input type="date/time">` | input + 月曆 icon ▢ |
| `.wf-select` | `<select>` | input + 下拉箭 ▾ |
| `.wf-textarea` | `<textarea>` | 多行 input，min-h 80px |
| `.wf-check` | `<input type="checkbox">` | 18×18 方框 ✓ |
| `.wf-radio` | `<input type="radio">` | 18×18 圓圈 ● |
| `.wf-switch` | toggle / switch | 36×20 軌道 + 圓鈕 |

### 3.4 按鈕 + 標籤 + 角標

| Class | 用途 | 視覺 |
|---|---|---|
| `.wf-btn` | 一般按鈕 | min-h 34px，圓角 999px，1.8px --line |
| `.wf-btn-primary` | 主按鈕 | 邊框 --ink + 700 weight + 底 --soft |
| `.wf-pill` | 標籤/狀態膠囊 | 圓角 999px，1.5px --line |
| `.wf-pill.is-active` | 強調膠囊 | 邊框 --ink，font-weight 700 |
| `.wf-badge` | 數字 / 角標 / 短標籤 | 圓角 999px，可文字撐寬 |
| `.wf-dot` | 圓點 | 18×18，1.8px --ink |
| `.wf-required` | 必填星號 | 紅色 *（唯一允許的非黑灰） |
| `.wf-helper` | 輔助文字 | --muted，12px |
| `.wf-countdown` | 倒數計時數字 | monospace，24px 800 weight |
| `.wf-icon-slot` | 圖示占位 | 虛線方框，placeholder「IMG」 |

### 3.5 進階 UI（Tab / Accordion / Stepper / Toast）

| Class | 用途 |
|---|---|
| `.wf-tabs` | tab 容器（橫排，底邊框分隔） |
| `.wf-tab` | 單一 tab，`.wf-tab.is-active` 加強 |
| `.wf-accordion` | 展開／收合容器（含 title + body） |
| `.wf-stepper` | 步驟條容器（橫排，含 N 個 .wf-step） |
| `.wf-step` | 單一步驟（圓點 + 標籤），`.wf-step.is-active` 強調 |
| `.wf-toast` | snackbar / toast 提示 |

### 3.6 進度 / 載入占位 / 圖表

| Class | 用途 | 注意 |
|---|---|---|
| `.wf-skeleton-pill` | 載入中膠囊占位 | **不可塞文字** |
| `.wf-skeleton-line` | 載入中行占位 | **不可塞文字** |
| `.wf-skeleton-block` | 載入中大塊占位 | **不可塞文字** |
| `.wf-bar` | progress / 直條圖長條 | 1.8px --ink，底 --soft |
| `.wf-chart` | 圖表外框容器 | |
| `.wf-chart-bars` | 圖表內 bar group | flex row baseline |
| `.wf-kpi` | KPI 卡片（數字 + 標籤） | |
| `.wf-kpi-grid` | KPI 卡片群（4 欄 grid） | |
| `.wf-card` | 通用卡片（介於 panel 與 frame） | |
| `.wf-list-line` | Desktop list 單行（dot + 文字 + skeleton） | （舊版 line-row 別名） |
| `.wf-line-row` | 同 `.wf-list-line` 別名（向後相容） | |

### 3.7 輪盤專屬 primitives（每日幸運輪 / 大轉盤類）

| Class | 用途 |
|---|---|
| `.wf-wheel` | 輪盤容器（外圓 1.8px --ink，內含 N 段 .wf-segment） |
| `.wf-wheel-pointer` | 固定指針三角形（純線稿） |
| `.wf-wheel-hub` | 中央 SPIN 按鈕（圓 + 內字） |
| `.wf-wheel-rim` | 輪盤外圈裝飾點（N 個 .wf-dot 圍繞） |
| `.wf-segment` | 輪盤 / 圓餅段 |
| `.wf-board` | 卡牌/格子棋盤（auto-fit grid） |

---

## 3.X HTML element → wf-* class 速查表（AI 必讀）

| 想畫的東西 | 用哪個 wf-* class |
|---|---|
| 標題文字 | `.wf-section-title`（區塊標題）/ `.wf-modal-title`（彈窗標題） |
| 一段內文 | `.wf-text` |
| 一條文字行（列表 item / 賣點 / FAQ 答案） | `.wf-line` |
| 一群文字行 | `.wf-list` > `.wf-line × N` |
| 連結 | `.wf-link` |
| 提示文字（次要） | `.wf-helper` |
| 輸入框（文字） | `.wf-input` |
| 日期輸入 | `.wf-input-date` |
| 下拉選單 | `.wf-select` |
| 多行輸入 | `.wf-textarea` |
| Checkbox | `.wf-check` |
| Radio | `.wf-radio` |
| Switch / Toggle | `.wf-switch` |
| 按鈕（主） | `.wf-btn.wf-btn-primary` |
| 按鈕（次） | `.wf-btn` |
| 表格 | `.wf-table` > `.wf-tr` > `.wf-td` |
| Tab 切換 | `.wf-tabs` > `.wf-tab × N` |
| 展開收合 | `.wf-accordion` |
| 步驟條 | `.wf-stepper` > `.wf-step × N` |
| Toast 提示 | `.wf-toast` |
| 標籤 / 狀態膠囊 | `.wf-pill` |
| 數字角標 / 短標籤 | `.wf-badge` |
| 必填星號 | `.wf-required` |
| 圖示位置 | `.wf-icon-slot` |
| 載入中骨架（空白） | `.wf-skeleton-{line,pill,block}` ← **不可塞文字** |
| 進度條 / 直條 | `.wf-bar` |
| 圖表 | `.wf-chart` > `.wf-chart-bars` > `.wf-bar × N` |
| KPI 卡片 | `.wf-kpi-grid` > `.wf-kpi × N` |
| **想橫排多元件** | 包進 `.wf-row` |
| **想直排多元件** | 用 `.wf-panel`（默認 column）或 `.wf-list`（細列表） |

---

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
