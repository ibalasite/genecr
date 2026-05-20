你是一個 JSON 補完工具。以下 JSON 在 AI 生成時因 token limit 被截斷，前面的部分是完整且正確的。

請只輸出**從截斷點繼續補完的後段**，補到整個 JSON object 結束（最後一個 `}`）。

規則：
1. 不要重複已有的內容，只補缺少的部分
2. 若以下列出了還沒出現的欄位，必須補上：{missing_keys}
3. 輸出必須是合法的 JSON 片段，能和前段拼接後形成完整 JSON
4. 不要輸出任何 prose 或說明，只輸出 JSON 片段（不要包 ```json 等 fenced block）
5. 若截斷點在某個陣列或物件中間，先正確關閉當前結構，再補其餘欄位

Step 類型：{step_type}

截斷的 JSON 末段（從這裡接下去補）：
{truncated_raw}
