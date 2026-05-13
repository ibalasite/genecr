# Mermaid Sanitize Test

測試 sequenceDiagram 內含 `<`、`>`、`<=`、`>=` 是否會破圖。

## Case 1: 正常箭頭（應渲染）

```mermaid
sequenceDiagram
  participant C as Client
  participant S as Server
  C->>S: GET /info
  S-->>C: 200 OK
```

## Case 2: 含 `<` `>` `>=` 在 message label（修復前破圖；修復後應顯示真正的 < >）

```mermaid
sequenceDiagram
  participant C as Client
  participant S as Server
  participant R as Redis
  C->>S: POST /grab
  S->>R: GET pool
  R-->>S: remaining >= 0
  S->>R: check endTs < now
  R-->>S: count > limit
  S-->>C: 200 {ok}
```

## Case 3: 含 `<=`

```mermaid
sequenceDiagram
  participant A as A
  participant B as B
  A->>B: x <= 100 ?
  B-->>A: yes (count <= max)
```

## 驗證

1. 用瀏覽器開生成的 html
2. 三張圖都應正常渲染（不是白框 / 不是文字）
3. Case 2、3 的 message 文字應出現真實的 `<`、`>`、`>=`、`<=` 字元
