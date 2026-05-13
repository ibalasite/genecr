# 儲值刮刮樂幸運券 需求規格書

## 一、修改紀錄
| 日期 | 修改人 | 內容 |
|------|--------|------|
| 2026-05-13 | 產品企劃 | 初版規格：每儲值1000送1張刮刮券、遊戲掉券、20-5000倍大獎、未中獎券參與週抽幸運號 |

## 二、相關文件
| 檔案 | 說明 | 狀態 |
|------|------|------|
| docs/PRD-recharge-scratch.md | 產品需求文件 | 進行中 |
| docs/EDD-scratch-engine.md | 刮獎引擎與RTP配置技術設計 | 待補 |
| docs/OPS-agent-cost.md | 代理商成本分攤與保護機制 | 待補 |

## 三、概要
- **是什麼**：老玩家儲值每滿1000送1張刮刮券，遊戲過程也會隨機掉券，券面可刮出20x-5000x大獎；未中獎券附幸運代號，每週開獎抽出幸運兒。
- **為什麼**：提升老玩家儲值動機與留存（儲值=立即獎勵+週抽期待），同時透過RTP與成本上限保護代理商不被掏空。
- **目標族群**：30日內有儲值紀錄的老玩家（VIP1+），尤其是中高儲值族群與每日活躍場次玩家。

## 四、競業分析摘要
### 1. TaDa Gaming - Scratch Mania （亞洲（菲律賓/越南））
- **核心機制**：儲值門檻贈刮卡，三同符號中獎，含特殊符號觸發加倍
- **RTP / 倍率**：RTP 92-94% / 最高 1000x 投注額
- **獎勵結構**：小獎2-10x佔70%、中獎50-200x佔25%、大獎500-1000x佔5%，無保底
- **玩家流程**：儲值→錢包收券→活動頁打開卡片→刮開三格→自動入帳
- **差異化亮點**：與儲值通道深度綁定，儲值成功立刻彈卡
- **可改進處**：缺乏未中獎二次機會，券一刮完就消失，留存力弱
- **參考連結**：[https://www.tadagaming.com/](https://www.tadagaming.com/)

### 2. JDB Lucky Scratch （亞洲（台灣/東南亞））
- **核心機制**：任一老虎機 spin 有萬分之一機率掉刮券，刮券走獨立 RTP
- **RTP / 倍率**：RTP 95% / 最高 2000x
- **獎勵結構**：6檔倍率：5x/20x/50x/200x/500x/2000x，含累積大獎池
- **玩家流程**：玩遊戲→中掉券提示→錢包→刮卡介面→領獎
- **差異化亮點**：與所有遊戲打通的掉券機制，覆蓋廣
- **可改進處**：沒有未中獎的延續體驗，玩家刮完空白券即流失
- **參考連結**：[https://www.jdb.cc/](https://www.jdb.cc/)

### 3. KA Gaming - Scratch Bonanza （亞洲（台灣））
- **核心機制**：分銅銀金三級卡，倍率區間不同，可花籌碼購買額外刮層
- **RTP / 倍率**：RTP 93-96% 依等級 / 最高 5000x
- **獎勵結構**：金卡含5000x大獎機率1/50000，銀卡最高500x，銅卡最高100x
- **玩家流程**：活動頁選等級→消耗券→刮三區→可加購額外刮→結算
- **差異化亮點**：卡片分級＋額外加購擴大ARPU
- **可改進處**：加購機制門檻高，新手覺得複雜
- **參考連結**：[https://www.kagaming.com/](https://www.kagaming.com/)

### 4. IGT Instant Win Scratchcards （北美（美國/加拿大））
- **核心機制**：傳統三符號刮卡，含累積州彩共享獎池
- **RTP / 倍率**：RTP 65-75%（州彩標準） / 最高 1,000,000x（極稀有）
- **獎勵結構**：金字塔型獎勵：80%小獎、15%中獎、5%大獎，含共享 jackpot
- **玩家流程**：購券→刮開符號→符合條件→大獎需經人工核獎→兌獎
- **差異化亮點**：州彩級信任度與超大累積獎
- **可改進處**：RTP低、刮券需付費購買，不適合贈券場景
- **參考連結**：[https://www.igt.com/](https://www.igt.com/)

### 5. Light & Wonder - Scratch & Match （北美）
- **核心機制**：刮開後進入Match-3小遊戲，三消觸發倍率
- **RTP / 倍率**：RTP 94% / 最高 2500x
- **獎勵結構**：基礎倍率5-50x，Match-3加成可達50x倍乘
- **玩家流程**：領券→刮開→Match-3→結算→領獎
- **差異化亮點**：二段式遊戲體驗，比單純刮卡有趣
- **可改進處**：開發成本高、教學成本高、不利快節奏發券場景
- **參考連結**：[https://www.lnw.com/](https://www.lnw.com/)

### 6. Pragmatic Play - Daily Drops & Wins （哥斯大黎加 / LATAM / 全球）
- **核心機制**：投注送幸運號入池，每日/週固定時點隨機抽號發獎
- **RTP / 倍率**：額外RTP約2-3%（網絡型促銷）
- **獎勵結構**：每日2萬美金、每週20萬美金，分100-500個獎位
- **玩家流程**：投注→自動獲幸運號→等候開獎→獎金自動入帳
- **差異化亮點**：全球網絡共享獎池，無需玩家主動操作
- **可改進處**：獎位需主動關注公告才知中獎，沉浸感較弱
- **參考連結**：[https://www.pragmaticplay.com/en/promotions/drops-and-wins/](https://www.pragmaticplay.com/en/promotions/drops-and-wins/)

### 7. PG Soft - Treasures of Aztec Scratch （東南亞（泰國/印尼））
- **核心機制**：老虎機免費旋轉中掉刮券，券與遊戲主題綁定
- **RTP / 倍率**：RTP 96% / 最高 1500x
- **獎勵結構**：5/10/50/200/1500x五階，含主題加倍符
- **玩家流程**：玩老虎機→隨機掉券→刮券→若中主題符再進加倍迷你關
- **差異化亮點**：與遊戲世界觀深度綁定，IP續航力強
- **可改進處**：僅限該系列遊戲產出券，覆蓋有限
- **參考連結**：[https://pgsoft.com/](https://pgsoft.com/)

### 8. Salsa Technology - Raspadinha （LATAM（巴西））
- **核心機制**：購券或贈券，三同圖即中，含即時開獎廣播
- **RTP / 倍率**：RTP 88-92% / 最高 3000x
- **獎勵結構**：高頻小獎為主，大獎用獎池滾動
- **玩家流程**：購券/領券→刮三格→中獎廣播→PIX秒到帳
- **差異化亮點**：即時到帳的多巴胺體驗+在地化
- **可改進處**：RTP偏低，未中獎完全無安慰機制
- **參考連結**：[https://salsatechnology.com/](https://salsatechnology.com/)


### 功能對比
| 項目 | 我們 | TaDa Scratch Mania | JDB Lucky Scratch | KA Scratch Bonanza | Pragmatic Daily Drops | Salsa Raspadinha |
|------|------|------|------|------|------|------|
| 取得方式 | 儲值每1000送1張 + 遊戲掉券雙通道 | 僅儲值贈卡 | 僅遊戲掉券 | 購買為主 | 投注自動入池 | 購買/贈券 |
| 最高倍率 | 5000x | 1000x | 2000x | 5000x | 視獎池 | 3000x |
| 未中獎機制 | 幸運代號參與週抽，零空券 | 無 | 無 | 無 | 無 | 無 |
| 代理商成本控制 | RTP上限+動態爆獎熔斷+週池封頂 | 無公開 | 無公開 | 加購補貼 | 網絡共擔 | 無公開 |
| 開獎透明度 | 每週直播+區塊鏈hash驗證 | 後台 | 後台 | 後台 | 公告 | 廣播 |

## 五、分類（多軸切割）
### 軸 1：獲券來源
- **儲值贈券**：每累計儲值滿1000贈1張，當日合併計算
- **遊戲掉券**：任一遊戲投注達門檻有機率掉券，與RTP無關

### 軸 2：刮獎結果
- **中獎券**：刮出三同符號，倍率20x-5000x
- **未中獎券**：附6位幸運代號自動入週抽池

### 軸 3：開獎節奏
- **即時刮獎**：領券後可立即刮
- **週抽**：每週日 21:00 直播開出幸運代號

## 六、功能對照表
獲券來源 × 刮獎結果交叉，定義每種來源券的處置流程與時間窗

| 獲券來源 \ 刮獎結果 | 中獎券 | 未中獎券 | 逾期未刮 | 時間軸 |
|---------|------|------|------|--------|
| 儲值贈券 | 立即派彩入錢包 | 代號入週抽池 | 自動視為未中獎進池 | 領取後 7 日內須刮 |
| 遊戲掉券 | 立即派彩入錢包 | 代號入週抽池 | 自動視為未中獎進池 | 領取後 3 日內須刮 |

`--` 代表不適用。

## 七、顯示欄位定義
- **ticket_id**：刮券唯一識別碼，UUIDv4（範例：`TKT-2026051300001`）- **source**：來源類型：recharge | game_drop（範例：`recharge`）- **lucky_code**：6位數字幸運代號，全域唯一（範例：`328-491`）- **prize_multiplier**：中獎倍率，未中為0；可選值 0/20/50/100/500/1000/5000（範例：`50`）- **base_amount**：計算倍率的基準額，固定為玩家儲值區段或預設值（如10）（範例：`10`）- **expire_at**：刮券過期時間戳（範例：`2026-05-20T23:59:59+08:00`）- **status**：unscratched | scratched_win | scratched_lose | expired | weekly_pending | weekly_won（範例：`unscratched`）- **agent_id**：歸屬代理商ID，用於成本攤分（範例：`AG-00231`）
## 八、業務規則
- **觸發條件**：儲值：玩家當日累計儲值每滿1000元贈1券（隔日歸零）；遊戲掉券：單局投注≥10元時有 p=0.5% 機率掉券，每帳號每日上限10張。
- **資料處理**：幸運代號全域唯一不重複；同帳號同日最多累積50張券；逾期券自動轉為未中獎並進入週抽池；中獎倍率依RTP表抽樣，總RTP上限92%。
- **排序 / 排名邏輯**：我的券列表預設依到期時間升序，次依取得時間；週抽結果依代號升序展示。
- **防作弊考量**：代號用 HMAC-SHA256 加鹽生成，後端發券時鎖定不可篡改；單裝置/IP/支付帳號交叉風控；異常儲值（撤單、爭議款）自動回收券；爆獎熔斷：當日代理商成本達上限後改派最低檔小獎。

## 九、用戶旅程 (User Journey)
1. **儲值1000** — 完成儲值後 Toast 提示『已獲 1 張刮刮券』，紅點掛上活動入口
   - 情緒/動機：驚喜：原本只是儲值，竟有額外獎勵
2. **進活動頁** — 看到券堆與『最高5000倍』大字，下方滾動播報剛中獎的玩家ID
   - 情緒/動機：期待：別人中了我也可能中
3. **刮券** — 手指刮開三格符號，含音效與震動回饋
   - 情緒/動機：緊張→爆發 或 緊張→失落
4. **未中獎看到代號** — 彈窗顯示『差一點！您的幸運代號 328-491 已進入本週開獎池』
   - 情緒/動機：安慰：沒白刮，還有週抽機會
5. **週日看開獎** — 21:00 直播間開出代號，自動比對推播
   - 情緒/動機：懸念：每週一次的儀式感

## 十、介面說明
1. **活動入口**：大廳首頁右上角浮標，顯示未刮券數量紅點，點擊進活動頁
2. **主舞台 - 券堆**：中央堆疊式券卡，可左右滑動切換，券面顯示來源與到期
3. **刮獎區**：進入單券後全螢幕刮獎，三格符號 + 倍率提示條
4. **幸運代號區**：刮完未中獎時顯示代號與週抽倒數時間
5. **歷史與週抽榜**：分頁顯示『我的歷史券』『本週幸運號池』『歷屆得主』
6. **規則與保護說明**：底部彈窗，含倍率表、RTP聲明、代理商保護條款連結

- **刷新機制**：領券即時推送（WebSocket），週抽結果於每週日 21:05 全量推播；活動頁進入時拉一次最新券列表。
- **擴充性註記**：倍率表與獎池上限走後台配置，可A/B不同RTP組；幸運代號可擴增至8位以支援更大池；可疊加節日加倍活動。
- **錯誤與邊界狀態**：斷網時刮獎動作本地暫存，重連後以後端結果為準；逾期券自動進週抽避免玩家損失感；同代號異常時取最早發券者；代理商熔斷觸發時前端維持正常UI但結果走保底。

### 線框圖

**1. 活動主畫面** — 進入活動的主頁，顯示券堆、最高倍率主視覺、滾動播報與主操作按鈕。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>09:41</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">刮刮券</span><span class="wf-pill">餘額 9,999</span></div><div class="wf-banner"><div class="wf-skeleton-block" style="width:100%;min-height:80px">主視覺：最高 5000x</div></div><div class="wf-marquee">★ ID***88 中 500x ★ ID***12 中 1000x</div><div class="wf-stage"><div class="wf-skeleton-block" style="width:100%;min-height:160px">券堆（可左右滑）</div><div class="wf-helper">未刮 5 張・到期最近 2 日內</div></div><div class="wf-info"><span class="wf-pill is-active">全部</span><span class="wf-pill">儲值</span><span class="wf-pill">遊戲</span></div><div class="wf-actionbar"><button class="wf-btn wf-btn-primary">立即刮獎</button></div><div class="wf-shortcuts"><span class="wf-icon-slot">歷史</span><span class="wf-icon-slot">週抽</span><span class="wf-icon-slot">規則</span></div><div class="wf-bottomnav"><span>大廳</span><span>活動</span><span>錢包</span><span>我的</span></div></div></div>

**2. 刮獎進行畫面** — 單張券打開後的全螢幕刮獎，三格符號可手指刮開，含倍率提示。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>09:41</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">刮獎中</span><span class="wf-pill">券 #00001</span></div><div class="wf-stage"><div class="wf-panel"><div class="wf-section-title">刮開三格符號</div><div class="wf-board"><div class="wf-skeleton-block" style="min-height:80px">?</div><div class="wf-skeleton-block" style="min-height:80px">?</div><div class="wf-skeleton-block" style="min-height:80px">?</div></div><div class="wf-helper">三同即中・倍率 20x ~ 5000x</div></div></div><div class="wf-info"><span class="wf-skeleton-pill">倍率表</span><span class="wf-skeleton-pill">說明</span></div><div class="wf-actionbar"><button class="wf-btn">一鍵全刮</button><button class="wf-btn wf-btn-primary">繼續</button></div></div></div>

**3. 中獎彈窗** — 刮中後彈出，顯示倍率、派彩金額與分享/繼續操作。

<div class="wf-scope"><div class="wf-modal"><div class="wf-modal-icon">🎉</div><div class="wf-modal-title">恭喜中獎</div><div class="wf-modal-body"><div class="wf-section-title">500x</div><div class="wf-helper">派彩金額 5,000・已入錢包</div></div><div class="wf-modal-meta">本獎已記錄至歷史，依規則即時到帳</div><div class="wf-modal-actions"><button class="wf-btn">分享</button><button class="wf-btn wf-btn-primary">繼續刮</button></div></div></div>

**4. 未中獎/幸運代號彈窗** — 未中獎時的安慰彈窗，揭示專屬幸運代號與週抽倒數，強化『不浪費』體感。

<div class="wf-scope"><div class="wf-modal"><div class="wf-modal-icon">CODE</div><div class="wf-modal-title">差一點！</div><div class="wf-modal-body"><div class="wf-section-title">328-491</div><div class="wf-helper">您的幸運代號已進入本週開獎池</div><div class="wf-countdown">03 : 12 : 45 : 09</div></div><div class="wf-modal-meta">每週日 21:00 直播開獎</div><div class="wf-modal-actions"><button class="wf-btn">查看週抽</button><button class="wf-btn wf-btn-primary">繼續刮</button></div></div></div>

**5. 週抽開獎頁** — 展示本週幸運代號池、倒數、歷屆得主清單，提供分享與規則入口。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>09:41</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">本週開獎</span><span class="wf-pill">直播</span></div><div class="wf-banner"><div class="wf-countdown">03 : 12 : 45 : 09</div></div><div class="wf-info"><span class="wf-pill is-active">我的代號</span><span class="wf-pill">全部池</span><span class="wf-pill">歷屆</span></div><div class="wf-stage"><div class="wf-panel"><div class="wf-skeleton-line">328-491</div><div class="wf-divider"></div><div class="wf-skeleton-line">102-883</div><div class="wf-divider"></div><div class="wf-skeleton-line">771-204</div></div><div class="wf-helper">本週共 12,348 張代號參與</div></div><div class="wf-actionbar"><button class="wf-btn">分享</button><button class="wf-btn wf-btn-primary">前往直播</button></div><div class="wf-bottomnav"><span>大廳</span><span>活動</span><span>錢包</span><span>我的</span></div></div></div>

**6. 空狀態** — 無券時的引導畫面，鼓勵玩家儲值或遊玩以獲得刮券。

<div class="wf-scope"><div class="wf-mobile"><div class="wf-statusbar"><span>09:41</span><span>● ● ●</span></div><div class="wf-appbar"><span class="wf-dot"></span><span class="wf-section-title">刮刮券</span><span class="wf-pill">餘額 9,999</span></div><div class="wf-stage"><div class="wf-empty"><div class="wf-modal-icon">EMPTY</div><div class="wf-section-title">目前沒有刮券</div><div class="wf-helper">儲值每滿 1000 送 1 張・玩遊戲也會掉券</div></div></div><div class="wf-actionbar"><button class="wf-btn">去玩遊戲</button><button class="wf-btn wf-btn-primary">去儲值</button></div><div class="wf-bottomnav"><span>大廳</span><span>活動</span><span>錢包</span><span>我的</span></div></div></div>


## 十一、文案對照表（多語）
| 中 | 英 | 西 |
|----|----|----|
| 刮刮券 | Scratch Ticket | Boleto Rasca |
| 幸運代號 | Lucky Code | Código de la Suerte |
| 本週開獎 | Weekly Draw | Sorteo Semanal |
| 最高 5000 倍 | Up to 5000x | Hasta 5000x |
| 差一點！代號已進入週抽 | So close! Your code is in the weekly pool | ¡Casi! Tu código está en el sorteo semanal |
| 立即刮獎 | Scratch Now | Rascar Ahora |

## 十二、說明頁（給玩家看）
**儲值送券、玩遊戲掉券，沒中也有週抽幸運號 —— 每一張券都不浪費！**

- 🎯 每儲值1000自動送1張刮刮券
- 💰 最高5000倍大獎，刮中即時入帳
- 🎁 沒中獎？幸運代號自動進週抽，每週日21:00開獎

**操作步驟**：
1. 儲值或玩遊戲取得刮刮券
2. 到活動頁打開券，刮開三格符號
3. 中獎即時派彩；未中獎代號自動進入本週開獎池等開獎

## 十三、建議上線時程
⚠️ 以下為建議，請企畫依實際團隊資源調整

| 階段 | 內容 | 建議時程 |
|------|------|---------|
| Phase 1 - MVP | 儲值贈券 + 基礎刮獎 + 倍率派彩 + 未中獎代號入池 + 週抽開獎 | 6 週 |
| Phase 2 - 擴充 | 遊戲掉券通道、滾動播報、歷屆得主榜、直播開獎介面 | 4 週 |
| Phase 3 - 優化 | A/B RTP 配置、代理商熔斷儀表板、節日加倍主題券 | 3 週 |

## 十四、資源需求概覽
- **美術資源**：約 25 件：券卡正面 3 款、刮獎符號 6 組、中獎/未中獎彈窗、入口浮標、活動主視覺、週抽直播背板
- **音效資源**：約 8 段：刮獎沙沙聲、中獎小/中/大三段、未中獎安慰、券獲取提示、週抽倒數、開獎揭曉
- **工程複雜度**：中：核心邏輯與RTP引擎可重用既有獎勵框架，但需新建幸運代號池+週抽排程+代理商成本熔斷，跨支付與遊戲事件整合工作量中等
