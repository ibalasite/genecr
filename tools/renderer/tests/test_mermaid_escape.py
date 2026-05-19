"""Test _escape_mermaid_semicolons — mermaid 區塊內箭頭行 `:` 後的 `;` 換 #59;。

病根：mermaid sequenceDiagram message label 含 `;` → parser 把 `;` 當 NL token
→ 後接 SQL keyword 不合法 → 整張圖變 Syntax error。
解：用 mermaid 官方 entity `#59;`，渲染後字面顯示為 `;`，圖正常。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from render import _escape_mermaid_semicolons as esc  # noqa: E402


def test_arrow_message_semicolon_replaced():
    src = "```mermaid\nsequenceDiagram\n  A->>B: BEGIN; SELECT x\n```"
    assert "A->>B: BEGIN#59; SELECT x" in esc(src)


def test_real_broken_case_round_start():
    src = """```mermaid
sequenceDiagram
  C->>S: POST /round/start {bet:50}
  S->>D: BEGIN; SELECT balance FROM users WHERE id=1001 FOR UPDATE
  S->>D: UPDATE users SET balance=9530; INSERT INTO rounds; COMMIT
```"""
    out = esc(src)
    # message text 段裡每個 `;` 都應該是 `#59;` 的一部分（用 entity 替換掉後不再有 `;`）
    after_begin = out.split("BEGIN", 1)[1].split("\n")[0]
    assert ";" not in after_begin.replace("#59;", ""), \
        f"BEGIN line still has raw `;` outside entity: {after_begin!r}"
    assert "#59;" in out


def test_participant_line_not_touched():
    src = "```mermaid\nsequenceDiagram\n  participant A as X; v2\n  A->>B: hi; world\n```"
    out = esc(src)
    assert "participant A as X; v2" in out      # 沒箭頭、不動
    assert "A->>B: hi#59; world" in out         # 箭頭行、動


def test_flowchart_not_touched():
    src = "```mermaid\nflowchart LR\n  A --> B; B --> C\n```"
    # flowchart 行有 -> 但沒 `:` text → pattern (:\s*)(.+) 不命中 → 不動
    # 但要注意：A --> B; B --> C 內含 `-->` 是箭頭，行內也沒 `:` → 不會誤動
    assert esc(src) == src


def test_non_mermaid_block_not_touched():
    src = "正文有 ;\n```python\nx = 1; y = 2\n```\n"
    assert esc(src) == src
