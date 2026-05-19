"""Unit tests for history loader pure logic (no tkinter)."""
import json
import os
import time
from pathlib import Path
import tempfile
import unittest


def scan_history(root: Path) -> tuple[list[str], dict[str, Path]]:
    """Scan root/**/feature.json, return (names_sorted_by_mtime_desc, name->run_dir)."""
    entries: list[tuple[float, str, Path]] = []
    if not root.exists():
        return [], {}
    for fj in root.rglob("feature.json"):
        try:
            data = json.loads(fj.read_text(encoding="utf-8"))
            name = data.get("name") or ""
            if not name:
                continue
            brief_path = fj.parent / "brief.txt"
            if not brief_path.exists():
                continue
            mtime = fj.stat().st_mtime
            entries.append((mtime, name, fj.parent))
        except Exception:
            continue
    entries.sort(key=lambda x: x[0], reverse=True)
    # Dedup names keeping newest
    seen: dict[str, Path] = {}
    order: list[str] = []
    for _, n, d in entries:
        if n not in seen:
            seen[n] = d
            order.append(n)
    return order, seen


class TestHistoryLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _mk(self, sub: str, slug: str, name: str, with_brief=True, mtime: float | None = None):
        d = self.root / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "feature.json").write_text(json.dumps({"slug": slug, "name": name}), encoding="utf-8")
        if with_brief:
            (d / "brief.txt").write_text("brief", encoding="utf-8")
        if mtime is not None:
            os.utime(d / "feature.json", (mtime, mtime))
        return d

    def test_empty_dir(self):
        names, m = scan_history(self.root)
        self.assertEqual(names, [])
        self.assertEqual(m, {})

    def test_missing_dir(self):
        names, m = scan_history(self.root / "nope")
        self.assertEqual(names, [])

    def test_basic_sort_mtime_desc(self):
        a = self._mk("a", "a", "A", mtime=100)
        b = self._mk("b", "b", "B", mtime=200)
        c = self._mk("c", "c", "C", mtime=150)
        names, m = scan_history(self.root)
        self.assertEqual(names, ["B", "C", "A"])
        self.assertEqual(m["A"], a)
        self.assertEqual(m["B"], b)
        self.assertEqual(m["C"], c)

    def test_skip_without_brief(self):
        self._mk("a", "a", "A", with_brief=False)
        self._mk("b", "b", "B")
        names, _ = scan_history(self.root)
        self.assertEqual(names, ["B"])

    def test_skip_no_name(self):
        d = self.root / "x"
        d.mkdir()
        (d / "feature.json").write_text(json.dumps({"slug": "x"}), encoding="utf-8")
        (d / "brief.txt").write_text("b", encoding="utf-8")
        names, _ = scan_history(self.root)
        self.assertEqual(names, [])

    def test_dedup_name_keep_newest(self):
        self._mk("old", "x", "Same", mtime=100)
        new = self._mk("new", "x", "Same", mtime=200)
        names, m = scan_history(self.root)
        self.assertEqual(names, ["Same"])
        self.assertEqual(m["Same"], new)


if __name__ == "__main__":
    unittest.main()
