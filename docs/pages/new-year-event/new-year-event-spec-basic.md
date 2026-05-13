# 元旦跨年活動 需求規格書

## 一、修改紀錄
| 日期 | 修改人 | 內容 |
|------|--------|------|
| 2026-05-14 | 產品企劃 | 初版企劃輸出，涵蓋倒數、煙火、限時加碼、紅包雨、好運轉盤五大子機制 |

## 二、相關文件
| 檔案 | 說明 | 狀態 |
|------|------|------|
| docs/tech-spec.md | 技術規格文件（API、資料表、後台） | 待補 |
| docs/bdd.feature | BDD 行為驗證情境 | 待補 |
| docs/resources.md | 美術音效資源清單 | 待補 |
| docs/scrum.md | SCRUM 工時拆解 | 待補 |

## 三、概要
- **是什麼**：12/31-1/2 限時跨年主題活動：整合倒數計時、煙火特效、限時儲值加碼、紅包雨、新年好運轉盤五大子機制，營造跨年儀式感，刺激跨年期間活躍與儲值。
- **為什麼**：跨年是全年儲值意願最高的窗口之一，玩家有「儀式感消費」與「博好彩頭」雙重動機；對營運方而言，可在 72 小時內把 ARPPU 與 DAU 同步推到全年高峰。所有獎勵以平台儲值返利包裝，代理商分潤線維持原比例不被吃。
- **目標族群**：已儲值過至少一次的活躍玩家（核心），以及 12 月最後兩週回流的休眠玩家（次要）；以中高額儲值玩家為氪金驅動主力。

## 四、競業分析摘要
### 1. Pragmatic Play - Drops & Wins (New Year Edition) （哥斯大黎加 / LATAM / 全球）
- **核心機制**：於指定 slot 下注觸發隨機掉落獎金 + 每日/每週排行榜瓜分獎池
- **RTP / 倍率**：基礎遊戲 RTP 96.5%，活動額外掉落獎金不影響 base RTP
- **獎勵結構**：單筆獎金 USD 5-10,000，週累積獎池 USD 2,000,000+，跨年版加碼至 USD 3,500,000
- **玩家流程**：進活動頁 → 選定參與 slot → 下注達門檻 → 隨機觸發掉落獎金 → 自動入帳
- **差異化亮點**：跨營運商共享獎池，量體大、行銷話題足
- **可改進處**：全靠 slot 下注觸發，缺乏「跨年儀式感」UI；無倒數與煙火氛圍營造
- **參考連結**：[https://www.pragmaticplay.com/promotions/drops-and-wins/](https://www.pragmaticplay.com/promotions/drops-and-wins/)

### 2. PG Soft - Lunar / Year-End Festival （東南亞 / 大中華）
- **核心機制**：指定主題 slot 任務（累積下注/連勝/特定符號）完成可解鎖紅包
- **RTP / 倍率**：主題 slot RTP 96.7%，活動紅包額外發放（平台補貼）
- **獎勵結構**：紅包 1-888 元等差設計，最高鯉魚躍龍門紅包 8,888 元
- **玩家流程**：進活動頁 → 選任務 → 玩指定 slot 完成條件 → 領紅包 → 分享得加碼
- **差異化亮點**：任務即玩法，東南亞春節包裝精緻
- **可改進處**：任務門檻偏高，輕度玩家完成率低；無倒數煙火等即時感
- **參考連結**：[https://www.pgsoft.com/](https://www.pgsoft.com/)

### 3. TaDa Gaming - 紅包派對 （亞洲 / 台灣 / 東南亞）
- **核心機制**：下注金額累積成抽獎券，定時開獎雨打式發放紅包
- **RTP / 倍率**：活動本身屬補貼性質，不影響遊戲 RTP
- **獎勵結構**：單包 NT$10-10,000，每場最高池 NT$500,000
- **玩家流程**：下注 → 累積點數 → 進入紅包雨房間 → 點擊飛落紅包 → 自動結算
- **差異化亮點**：紅包雨即時互動感強，玩家點擊參與
- **可改進處**：無分時段／角色加碼設計，玩家拿到金額隨機性高、預期管理差
- **參考連結**：[https://www.tada.games/](https://www.tada.games/)

### 4. JDB Gaming - 新年轉盤 （亞洲 / 台灣 / 菲律賓）
- **核心機制**：轉盤 12 格獎項，VIP 等級越高越能解鎖高倍格
- **RTP / 倍率**：轉盤期望值固定，依等級設不同 EV 曲線
- **獎勵結構**：普通格 5-50 點，金格最高 8,888 點，連續 7 日登入額外大獎
- **玩家流程**：登入 → 進活動 → 點轉盤 → 動畫結算 → 領獎
- **差異化亮點**：VIP 綁定強，留存效果佳
- **可改進處**：無儲值連動，刺激儲值力道弱；UI 偏舊
- **參考連結**：[https://www.jdbgaming.com/](https://www.jdbgaming.com/)

### 5. IGT - New Year's Mega Multiplier （北美 / 歐洲）
- **核心機制**：指定時刻全平台同步進入 Mega Multiplier 狀態 60 分鐘
- **RTP / 倍率**：活動時段 EV 提升至 102-105%（補貼）
- **獎勵結構**：中獎時自動套用 2-10x 倍率，最高單注獎金 USD 50,000
- **玩家流程**：接近跨年 → 推播倒數 → 0:00 自動觸發 → 玩家下注享倍率 → 結算
- **差異化亮點**：全平台同步儀式感極強
- **可改進處**：僅 60 分鐘窗口太短，未跨年的玩家完全 miss 不到體驗
- **參考連結**：[https://www.igt.com/](https://www.igt.com/)

### 6. KA Gaming - 跨年煙火夜 （亞洲 / 台灣 / 越南）
- **核心機制**：指定時間段內所有中獎觸發煙火動畫 + 額外 1.5x 倍率
- **RTP / 倍率**：活動時段補貼後綜合 RTP 97.8%
- **獎勵結構**：煙火加碼上限 NT$30,000/注
- **玩家流程**：進 slot → 活動時段中獎 → 煙火動畫 + 倍率 → 結算
- **差異化亮點**：氛圍感強，沉浸感佳
- **可改進處**：無倒數與紅包雨等多元玩法，整體單一
- **參考連結**：[https://www.kagaming.com/](https://www.kagaming.com/)

### 7. Light & Wonder - Holiday Hot Drop Jackpots （北美）
- **核心機制**：三層 jackpot 計時器，到時必觸發給某玩家
- **RTP / 倍率**：jackpot 計入 base RTP 96.4%
- **獎勵結構**：小時池 USD 1,000、日池 USD 25,000、Super 池 USD 500,000
- **玩家流程**：下注 → 看倒數 → 倒數歸零必中 → 自動派彩
- **差異化亮點**：必掉機制讓玩家黏在桌前
- **可改進處**：獎落單人，多數玩家空跑；跨年主題包裝弱
- **參考連結**：[https://www.lnw.com/](https://www.lnw.com/)

### 8. Salsa Technology - LATAM Año Nuevo （哥斯大黎加 / 巴西 / LATAM）
- **核心機制**：指定主題 slot 累積消費換大獎抽獎券
- **RTP / 倍率**：主題 slot RTP 96.2%
- **獎勵結構**：頭獎 12 grapes（西語跨年習俗）對應 12 萬獎金
- **玩家流程**：消費累積 → 抽獎券 → 跨年夜抽 → 大獎名單公告
- **差異化亮點**：在地化跨年文化（12 顆葡萄）
- **可改進處**：純抽獎缺即時互動，氛圍營造度中等
- **參考連結**：[https://salsatechnology.com/](https://salsatechnology.com/)


### 功能對比
| 項目 | 我們 | Pragmatic Play | PG Soft | TaDa | JDB | IGT | KA Gaming | Light & Wonder | Salsa | 我們 |
|------|------|------|------|------|------|------|------|------|------|------|
| 跨年儀式感（倒數+煙火） | ✓ 5 大子機制整合 | 弱 | 中 | 中 | 弱 | 強（限 60 分） | 強（純動畫） | 弱 | 中 |
| 刺激儲值力道 | ✓ 限時儲值加碼分層+紅包雨綁儲值 | 強（獎池） | 中 | 中 | 弱 | 中 | 中 | 中 | 中 |
| 多時段參與設計 | ✓ 12/31-1/2 三天三段式 | 週期長 | 週期長 | 日刷新 | 日刷新 | 僅 1hr | 時段 | 必掉 | 跨年單點 |
| 代理分潤保護 | ✓ 所有獎金走平台補貼，不動代理抽成 | 平台池 | 平台補貼 | 平台補貼 | 平台補貼 | 平台補貼 | 平台補貼 | RTP 內 | 平台補貼 |
| 視覺氛圍 | ✓ 倒數+煙火+紅包雨三重 | 弱 | 中 | 強（紅包） | 弱 | 中 | 強（煙火） | 弱 | 中 |
| 防作弊 | ✓ 多帳號 IP/裝置/儲值來源檢核 | 強 | 中 | 中 | 弱 | 強 | 中 | 強 | 中 |

## 五、分類（多軸切割）
### 軸 1：子機制（玩法軸）
- **跨年倒數**：全站 banner + 跨年夜 23:00-00:00 倒數計時，0:00 觸發煙火
- **煙火特效**：0:00-00:30 全站煙火動畫，所有中獎額外 1.5x
- **限時儲值加碼**：12/31-1/2 三日，儲值金額分層加碼 6-18%
- **紅包雨**：每日 20:00/22:00/00:00 三場，點擊飛落紅包搶獎
- **好運轉盤**：每日免費一抽，儲值滿額額外 +3 抽，12 格獎項

### 軸 2：時段軸
- **12/31 跨年夜**：重頭戲：倒數+煙火+紅包雨大場+轉盤雙倍機率
- **1/1 新年首日**：轉盤 + 紅包雨 + 儲值加碼最高層級
- **1/2 收官日**：轉盤 + 紅包雨 + 加碼降至中層，沖刺收官

### 軸 3：玩家分層
- **VIP 1-3**：基礎加碼 6%，紅包池占比 20%
- **VIP 4-6**：加碼 10%，紅包池占比 50%，轉盤額外抽數
- **VIP 7+**：加碼 18%，紅包池占比 100%，專屬煙火彩蛋

## 六、功能對照表
日期 × 子機制 開放矩陣，標示開放/加碼倍數

| 日期 \ 子機制 | 倒數 | 煙火 | 儲值加碼 | 紅包雨 | 好運轉盤 | 時間軸 |
|---------|------|------|------|------|------|--------|
| 12/31 跨年夜 | ✓ 23:00 起 | ✓ 0:00-0:30 | ✓ 加碼層 高(18%) | ✓ 20/22/00 三場 | ✓ 雙倍機率 | 23:00-01:00 為高峰 |
| 1/1 新年首日 | -- | -- | ✓ 加碼層 高(18%) | ✓ 20/22 二場 | ✓ 一般機率+登入贈抽 | 全日 |
| 1/2 收官日 | -- | -- | ✓ 加碼層 中(10%) | ✓ 22 一場 | ✓ 一般機率 | 全日 至 23:59 |

`--` 代表不適用。

## 七、顯示欄位定義
- **event_id**：活動唯一 ID，格式 EVT-NY-YYYY（範例：`EVT-NY-2026`）- **player_vip_tier**：玩家 VIP 等級 1-9，決定加碼比例與紅包占比（範例：`5`）- **recharge_amount**：單筆儲值金額（活動視窗內累計），整數，最小 100（範例：`5000`）- **bonus_rate**：加碼比例，依 VIP 與時段查表，6%/10%/18%（範例：`0.18`）- **redpacket_pool_share**：該玩家可分得紅包池比例 0-1（範例：`0.5`）- **wheel_free_spins**：每日免費轉盤次數，預設 1（範例：`1`）- **wheel_paid_spins**：儲值贈送的轉盤次數，每滿 1000 +1，上限 10（範例：`3`）- **firework_window**：煙火時段時間戳，UTC+8（範例：`2025-12-31T16:00:00Z ~ 2025-12-31T16:30:00Z`）- **agent_commission_protected**：代理分潤是否保護（布林），所有獎金走平台補貼線時為 true（範例：`true`）
## 八、業務規則
- **觸發條件**：玩家於 2025-12-31 00:00 至 2026-01-02 23:59 期間登入 / 儲值 / 下注，依各子機制條件觸發。倒數與煙火為全站時間觸發，無需玩家動作。
- **資料處理**：每位玩家每日紅包雨點擊上限 30 次；轉盤每日免費 1 次，付費贈送上限 10 次；儲值加碼按單日累計分層計算，不重複領取；同 IP/同裝置/同代理下線同手機號視為同一玩家，獎勵僅發放一份。
- **排序 / 排名邏輯**：紅包雨大獎榜按單場拾取金額 desc，相同金額按拾取時間 asc；轉盤大獎榜按單抽倍數 desc，再按時間 asc。
- **防作弊考量**：1) 同 IP/同裝置指紋/同支付來源/同推薦代理綁定多帳號自動合併計算；2) 紅包雨點擊頻率 >10 次/秒視為腳本，封禁該場資格；3) 儲值後 5 分鐘內提現未消費，凍結加碼；4) 風控異常帳號獎勵延遲 24h 結算可回收。

## 九、用戶旅程 (User Journey)
1. **看到推播 / 大廳 banner** — 12/29 起接收『跨年三日狂歡』推播 + 大廳跑馬燈，顯示倒數天數
   - 情緒/動機：好奇、期待
2. **點進活動頁** — 看到五大子機制 tab、自己的 VIP 加碼比例、總獎池
   - 情緒/動機：被吸引、想參與
3. **首儲加碼** — 12/31 中午儲值 5000，看到 +18% 加碼自動入帳並彈窗慶祝
   - 情緒/動機：佔便宜感、滿足
4. **23:55 進入倒數頁** — 全屏倒數計時，背景跨年城市夜景，提示 0:00 煙火+紅包雨
   - 情緒/動機：儀式感、緊張期待
5. **0:00 煙火 + 紅包雨** — 煙火動畫綻放，紅包從天而降，瘋狂點擊搶獎
   - 情緒/動機：興奮、心流、爽感
6. **轉盤抽好運** — 用今日累積的 4 次抽獎機會，連抽轉盤，中 88 倍彩蛋
   - 情緒/動機：幸運、好兆頭
7. **1/2 收官回顧** — 活動結算頁顯示三日獲得：加碼 9000、紅包 12000、轉盤 8800
   - 情緒/動機：成就、滿足、想下次再來

## 十、介面說明
1. **全站頂部跑馬燈**：位於主導覽下方，顯示『距跨年還有 HH:MM:SS』+ 大獎播報，可點擊跳活動頁
2. **活動主頁 Hero 區**：頂部跨年夜城市背景 + 倒數計時 + 活動標題 + 自己的 VIP 加碼徽章
3. **五大子機制 Tab**：水平捲動 tab：倒數 / 煙火 / 儲值加碼 / 紅包雨 / 好運轉盤，預設停在當下進行中項目
4. **儲值加碼面板**：分層階梯圖：1000/3000/5000/10000，標示自己 VIP 對應加碼，CTA『立即儲值』
5. **紅包雨入口**：場次倒數 + 預估獎池 + 上場成績，開場前 5 分鐘按鈕亮起『進入會場』
6. **好運轉盤**：輪盤 + 剩餘抽數 + 抽獎歷史，0:00 後雙倍機率時顯示金色描邊
7. **排行榜側欄**：右側可收合，三日累積拾取金額前 50 名，附頭像與隱碼帳號
8. **領獎信箱**：右上信封圖示，紅點顯示未領數，含 7 日有效期

- **刷新機制**：活動頁每 30 秒輪詢倒數時間與獎池金額；紅包雨會場改 WebSocket 即時推送；轉盤抽獎結果即時刷新。
- **擴充性註記**：子機制以 plugin 化設計，農曆春節 / 中秋等下次活動可換主題包不需改架構；獎勵發放走統一獎勵中台。
- **錯誤與邊界狀態**：1) 斷網重連自動補拾紅包雨期間漏接 frame；2) VIP 升等於活動中即時生效，重新計算加碼；3) 風控凍結帳號顯示『獎勵審核中』而非彈錯誤；4) 跨時區玩家強制以伺服器 UTC+8 為準並提示。

### 線框圖

**1. 活動主頁** — 進入活動的入口頁，頂部倒數，下方五大子機制 tab 與儲值加碼階梯。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>09:41</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">跨年活動</span><span class="wf-pill">餘額 9,999</span></div><div class="wf-banner"><div class="wf-section-title">跨年城市夜景 Banner</div><div class="wf-countdown">02:11:45:30</div></div><div class="wf-marquee">★ 玩家 A 剛拿到 8,888 紅包 ★ 玩家 B 轉盤中 88 倍 ★</div><div class="wf-stage"><div class="wf-pill is-active">倒數</div><div class="wf-pill">煙火</div><div class="wf-pill">儲值加碼</div><div class="wf-pill">紅包雨</div><div class="wf-pill">轉盤</div><div class="wf-skeleton-block" style="width:100%;min-height:160px">當前子機制內容區</div><div class="wf-helper">VIP 5 加碼徽章 +10%</div></div><div class="wf-actionbar"><button class="wf-btn wf-btn-primary">立即儲值</button><button class="wf-btn">查看獎勵</button></div><div class="wf-bottomnav"><span class="wf-icon-slot">首</span><span class="wf-icon-slot">活</span><span class="wf-icon-slot">榜</span><span class="wf-icon-slot">我</span></div></div></div>

**2. 跨年倒數全屏頁** — 23:55 起進入全屏倒數，0:00 自動切煙火+紅包雨。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>23:55</span><span>● ● ●</span></div><div class="wf-stage"><div class="wf-section-title">距離 2026 還剩</div><div class="wf-countdown" style="min-height:60px">00:04:23</div><div class="wf-skeleton-block" style="width:100%;min-height:180px">城市夜景 + 煙火預備動畫位</div><div class="wf-helper">0:00 自動觸發煙火 + 紅包雨</div></div><div class="wf-actionbar"><button class="wf-btn">預約紅包雨</button><button class="wf-btn wf-btn-primary">準備好了</button></div></div></div>

**3. 紅包雨會場** — 場內紅包飄落，玩家點擊搶獎，顯示本場池與剩餘秒數。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>00:00</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">跨年紅包雨</span><span class="wf-pill">池 888,888</span></div><div class="wf-info"><span class="wf-pill is-active">剩餘 02:30</span><span class="wf-pill">已拾 12 個</span></div><div class="wf-stage"><div class="wf-skeleton-block" style="width:100%;min-height:280px">紅包飄落區（多個紅包佔位）</div></div><div class="wf-actionbar"><button class="wf-btn wf-btn-primary">點擊搶紅包</button></div></div></div>

**4. 好運轉盤** — 輪盤 12 格，剩餘抽數與抽獎歷史。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>10:15</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">新年好運轉盤</span><span class="wf-pill">剩 4 抽</span></div><div class="wf-stage"><div class="wf-wheel"><div class="wf-wheel-pointer"></div><div class="wf-wheel-hub">GO</div></div><div class="wf-helper">跨年夜 0:00 雙倍機率</div></div><div class="wf-info"><span class="wf-skeleton-pill">歷史 1</span><span class="wf-skeleton-pill">歷史 2</span><span class="wf-skeleton-pill">歷史 3</span></div><div class="wf-actionbar"><button class="wf-btn">儲值贈抽</button><button class="wf-btn wf-btn-primary">立即抽獎</button></div></div></div>

**5. 儲值加碼階梯** — 分層儲值加碼面板，標出當前 VIP 對應加碼倍率。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>14:22</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">限時儲值加碼</span><span class="wf-pill">VIP 5</span></div><div class="wf-stage"><div class="wf-panel"><div class="wf-section-title">階梯 1：儲 1000</div><div class="wf-helper">+6% 加碼</div></div><div class="wf-panel"><div class="wf-section-title">階梯 2：儲 3000</div><div class="wf-helper">+10% 加碼（你的等級）</div></div><div class="wf-panel"><div class="wf-section-title">階梯 3：儲 10000</div><div class="wf-helper">+18% 加碼</div></div><div class="wf-countdown">剩 35:12:08</div></div><div class="wf-actionbar"><button class="wf-btn wf-btn-primary">立即儲值</button></div></div></div>

**6. 領獎彈窗** — 中獎後彈窗，顯示金額與條款，CTA 領取。

<div class="wf-scope"><div class="wf-modal"><div class="wf-modal-icon">🎆</div><div class="wf-modal-title">恭喜獲得跨年大獎</div><div class="wf-modal-body"><div class="wf-skeleton-line" style="width:80%"></div><div class="wf-skeleton-line" style="width:60%"></div><div class="wf-countdown">8,888</div></div><div class="wf-modal-meta">獎金 7 日內未領視為放棄；流水 1 倍</div><div class="wf-modal-actions"><button class="wf-btn">稍後</button><button class="wf-btn wf-btn-primary">立即領取</button></div></div></div>


## 十一、文案對照表（多語）
| 中 | 英 | 西 |
|----|----|----|
| 元旦跨年活動 | New Year Countdown Festival | Festival de Cuenta Regresiva de Año Nuevo |
| 跨年倒數 | Countdown to Midnight | Cuenta Regresiva |
| 煙火加碼 | Firework Bonus | Bono de Fuegos Artificiales |
| 限時儲值加碼 | Limited-Time Recharge Bonus | Bono de Recarga por Tiempo Limitado |
| 跨年紅包雨 | New Year Red Envelope Rain | Lluvia de Sobres Rojos |
| 新年好運轉盤 | Lucky New Year Wheel | Ruleta de la Suerte de Año Nuevo |
| 立即儲值 | Recharge Now | Recargar Ahora |
| 距離跨年還剩 | Time until New Year | Tiempo restante para Año Nuevo |
| 恭喜獲得 | Congratulations, you won | Felicidades, ganaste |
| 獎池 | Prize Pool | Bote de Premios |

## 十二、說明頁（給玩家看）
**三天三夜，跨年儀式感拉滿，紅包煙火轉盤一次擁有！**

- 🎆 跨年夜 0:00 全站煙火，所有中獎自動 1.5x
- 💰 儲值加碼最高 18%，越早儲越划算
- 🧧 每日三場紅包雨，動動手指搶現金
- 🎰 好運轉盤每日免費抽，跨年夜雙倍機率
- 🏆 三日排行榜瓜分百萬獎池

**操作步驟**：
1. 12/29 開放預熱頁，可預約跨年夜紅包雨入場
2. 12/31-1/2 期間登入即看到活動 banner
3. 選擇參與子機制：儲值加碼 / 紅包雨 / 轉盤
4. 跨年夜 23:55 進倒數頁，0:00 自動觸發煙火 + 紅包雨
5. 於信箱領取所有獎勵，7 日內未領視為放棄

## 十三、建議上線時程
⚠️ 以下為建議，請企畫依實際團隊資源調整

| 階段 | 內容 | 建議時程 |
|------|------|---------|
| Phase 0 - 預熱 | 大廳 banner、推播、預約紅包雨會場、客服 FAQ | 1 週 (12/22-12/28) |
| Phase 1 - MVP | 倒數 + 煙火 + 儲值加碼 + 紅包雨 + 轉盤 五大子機制上線，後台監控儀表板 | 3 週開發 + 1 週 QA |
| Phase 2 - 上線運行 | 12/31-1/2 三日，營運值班、即時調整獎池 | 3 天 |
| Phase 3 - 結算與覆盤 | 獎勵 7 日領獎窗口、ROI 報表、玩家滿意度問卷 | 1 週 (1/3-1/9) |

## 十四、資源需求概覽
- **美術資源**：約 40+ 件：跨年城市夜景 banner ×3、煙火動畫 spritesheet ×5、紅包 3D 模型 ×6、轉盤輪盤 ×1、按鈕/圖示 ×20、彈窗背板 ×5
- **音效資源**：約 12 件：跨年倒數 tick、0:00 煙火爆破 ×3、紅包拾取 ×3、轉盤旋轉/停止/中獎 ×3、背景跨年音樂 ×2
- **工程複雜度**：高：涉及全站時間同步、WebSocket 紅包雨會場、儲值加碼接金流、防作弊規則引擎、獎勵中台對接；建議 2 後端 + 2 前端 + 1 客戶端 + 1 QA，總工 8-10 週。
