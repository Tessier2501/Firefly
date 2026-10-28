r"""清洗 MinerU 转换产物：删除等价重复 md, 还原目录与标题层级, HTML 表转 Markdown 管道表, 校验后覆盖 full.md。"""

from __future__ import annotations

import argparse
import html
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
TOC_LINE_RE = re.compile(r"^(.+?)\.{2,}\s*(\d+)\s*$")
NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*(.*)$")
NOTE_LABELS = {"注", "注意", "警告", "提示", "说明"}
DUP_PREFIX = "MinerU_markdown_"
TABLE_RE = re.compile(r"(?s)<table>.*?</table>")
ROW_RE = re.compile(r"(?s)<tr[^>]*>(.*?)</tr>")
CELL_RE = re.compile(r"(?s)<t([dh])([^>]*)>(.*?)</t\1>")
CELL_ATTR_RE = re.compile(r"(colspan|rowspan)\s*=\s*\"?(\d+)", re.IGNORECASE)
IMAGE_RE = re.compile(r"(?s)<img[^>]*src=\"([^\"]+)\"[^>]*>")
TAG_RE = re.compile(r"(?s)<[^>]+>")
BREAK_RE = re.compile(r"(?i)<br\s*/?>")
ROW_SPLIT_RE = re.compile(r"(?<!\\)\|")
SEPARATOR_CELL_RE = re.compile(r":?-{3,}:?")


def heading_level(number: str) -> int:
    """编号 1 -> H2, 1.1 -> H3, 1.2.3 -> H4."""
    return min(2 + number.count("."), 6)


def same_title(left: str, right: str) -> bool:
    """目录标题与正文章节标题是否指向同一节."""
    normalize = lambda text: re.sub(r"[\s.．。:：、]+", "", text).lower()
    a, b = normalize(left), normalize(right)
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a)


def parse_toc(text: str) -> dict[str, str]:
    """解析目录块，返回 章节号 -> 标题."""
    toc: dict[str, str] = {}
    in_toc = False
    for line in text.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            in_toc = heading.group(2).strip().replace(" ", "") == "目录"
            continue
        if not in_toc:
            continue
        entry = TOC_LINE_RE.match(line.strip())
        if not entry:
            continue
        numbered = NUMBER_RE.match(entry.group(1).strip())
        if numbered:
            toc[numbered.group(1)] = numbered.group(2).strip()
    return toc


def toc_lines(text: str) -> set[str]:
    """目录块中以点线+页码结尾的行（原文形式）."""
    lines: set[str] = set()
    in_toc = False
    for line in text.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            in_toc = heading.group(2).strip().replace(" ", "") == "目录"
            continue
        if in_toc and TOC_LINE_RE.match(line.strip()):
            lines.add(line.strip())
    return lines


def clean_text(text: str) -> tuple[str, dict[str, int]]:
    """返回清洗后的文本与统计 (toc/renumbered/notes/demoted)."""
    newline = "\r\n" if "\r\n" in text else "\n"
    toc = parse_toc(text)
    stats = {"toc": 0, "renumbered": 0, "notes": 0, "demoted": 0}
    out: list[str] = []
    in_toc = False
    current_level: int | None = None
    for line in text.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            hashes, title = heading.group(1), heading.group(2).strip()
            in_toc = title.replace(" ", "") == "目录"
            if len(hashes) == 1 or in_toc:
                out.append(("#" * len(hashes)) + " " + title)
                continue
            numbered = NUMBER_RE.match(title)
            if numbered and numbered.group(1) in toc and same_title(toc[numbered.group(1)], numbered.group(2)):
                level = heading_level(numbered.group(1))
                current_level = level
                out.append("#" * level + " " + title)
                if level != len(hashes):
                    stats["renumbered"] += 1
                continue
            if current_level is None:
                out.append("#" * len(hashes) + " " + title)
                continue
            if title in NOTE_LABELS:
                out.append(f"**{title}**")
                stats["notes"] += 1
                continue
            level = min(current_level + 1, 6)
            out.append("#" * level + " " + title)
            stats["demoted"] += 1
            continue
        if in_toc:
            entry = TOC_LINE_RE.match(line.strip())
            if entry:
                title = entry.group(1).strip()
                indent = ""
                numbered = NUMBER_RE.match(title)
                if numbered:
                    indent = "  " * numbered.group(1).count(".")
                out.append(f"{indent}- {title}")
                stats["toc"] += 1
                continue
        out.append(line)
    cleaned = newline.join(out)
    if text.endswith(("\n", "\r\n")):
        cleaned += newline
    return cleaned, stats


def verify_preserved(original: str, cleaned: str) -> list[str]:
    """校验清洗没有丢正文：行数不变，非标题正文行保留，标题文本保留."""
    problems: list[str] = []
    original_lines = original.splitlines()
    cleaned_lines = cleaned.splitlines()
    if len(original_lines) != len(cleaned_lines):
        problems.append(f"行数由 {len(original_lines)} 变为 {len(cleaned_lines)}")
    removed_toc = toc_lines(original)
    cleaned_set = {line.strip() for line in cleaned_lines}
    missing = [
        line.strip() for line in original_lines
        if line.strip() and not HEADING_RE.match(line) and line.strip() not in removed_toc
        and line.strip() not in cleaned_set
    ]
    if missing:
        problems.append(f"正文行缺失 {len(missing)} 行, 例如: {missing[:2]}")
    missing_titles = [
        HEADING_RE.match(line).group(2).strip() for line in original_lines
        if HEADING_RE.match(line) and not any(HEADING_RE.match(line).group(2).strip() in text for text in cleaned_lines)
    ]
    if missing_titles:
        problems.append(f"标题缺失 {len(missing_titles)} 个, 例如: {missing_titles[:2]}")
    return problems


def normalize(text: str) -> str:
    """去掉所有空白与反斜杠转义，用于判断副本是否等价."""
    return re.sub(r"\s+", "", text).replace("\\", "")


def cell_text(fragment: str) -> str:
    """HTML 单元格内容转 Markdown 行内文本."""
    text = BREAK_RE.sub(" ", fragment)
    text = IMAGE_RE.sub(lambda match: f"![]({match.group(1)})", text)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("|", r"\|")


def table_to_markdown(table_html: str) -> list[str]:
    """单张 HTML 表转 GFM 管道表行, 合并单元格用空单元格占位; 无行时原样返回."""
    grid: list[list[str]] = []
    covered: list[list[bool]] = []

    def ensure(row: int) -> None:
        while len(grid) <= row:
            grid.append([])
            covered.append([])

    for row_index, inner in enumerate(ROW_RE.findall(table_html)):
        ensure(row_index)
        column = 0
        for _tag, attrs, content in CELL_RE.findall(inner):
            while column < len(covered[row_index]) and covered[row_index][column]:
                column += 1
            spans = {key.lower(): int(value) for key, value in CELL_ATTR_RE.findall(attrs)}
            colspan = max(1, spans.get("colspan", 1))
            rowspan = max(1, spans.get("rowspan", 1))
            for offset in range(rowspan):
                ensure(row_index + offset)
                while len(grid[row_index + offset]) < column + colspan:
                    grid[row_index + offset].append("")
                    covered[row_index + offset].append(False)
            grid[row_index][column] = cell_text(content)
            for offset in range(rowspan):
                for step in range(colspan):
                    covered[row_index + offset][column + step] = True
            column += colspan
    if not grid:
        return [table_html]
    width = max(len(row) for row in grid)
    lines: list[str] = []
    for index, row in enumerate(grid):
        cells = row + [""] * (width - len(row))
        lines.append("| " + " | ".join(cells) + " |")
        if index == 0:
            lines.append("| " + " | ".join(["---"] * width) + " |")
    return lines


def convert_html_tables(text: str) -> tuple[str, int]:
    """把正文中的 HTML 表转换为管道表, 代码围栏内不处理; 返回 (文本, 转换张数)."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    out: list[str] = []
    converted = 0
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            index += 1
            continue
        if in_fence or "<table>" not in line:
            out.append(line)
            index += 1
            continue
        block = line
        while "</table>" not in block and index + 1 < len(lines):
            index += 1
            block += newline + lines[index]

        def replace(match: re.Match[str]) -> str:
            nonlocal converted
            markdown = table_to_markdown(match.group(0))
            if markdown != [match.group(0)]:
                converted += 1
            return "\n".join(markdown)

        out.extend(TABLE_RE.sub(replace, block).split("\n"))
        index += 1
    result = newline.join(out)
    if text.endswith(("\n", "\r\n")):
        result += newline
    return result, converted


def split_table_row(line: str) -> list[str]:
    """拆分管道表行, 跳过转义竖线."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [part.replace("\\|", "|").strip() for part in ROW_SPLIT_RE.split(body)]


def markdown_table_blocks(text: str) -> list[list[str]]:
    """提取连续的管道表行块, 代码围栏内不算."""
    blocks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        is_row = not in_fence and stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 1
        if is_row:
            current.append(stripped)
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def has_table_outside_fence(text: str) -> bool:
    """正文（代码围栏外）是否还有 HTML 表."""
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and "<table>" in line:
            return True
    return False


def block_cells(blocks: list[list[str]]) -> tuple[Counter[str], int]:
    """统计管道表块的非空单元格与行数（不含分隔行）."""
    cells: Counter[str] = Counter()
    rows = 0
    for block in blocks:
        for row in block:
            parts = split_table_row(row)
            if parts and all(SEPARATOR_CELL_RE.fullmatch(part) for part in parts):
                continue
            rows += 1
            for part in parts:
                if part:
                    cells[part] += 1
    return cells, rows


def verify_tables(source: str, converted: str) -> list[str]:
    """校验 HTML 表转换未丢内容: 表格数/行数/单元格文本/表格外行."""
    problems: list[str] = []
    if has_table_outside_fence(converted):
        problems.append("转换后仍有未处理的 HTML 表")
    source_tables = TABLE_RE.findall(source)
    blocks = markdown_table_blocks(converted)
    existing_blocks = markdown_table_blocks(source)
    if len(existing_blocks) + len(source_tables) != len(blocks):
        return problems + [f"表格数量不一致: 原文 {len(existing_blocks)}+{len(source_tables)}, 转换后 {len(blocks)}"]
    expected_cells, expected_rows = block_cells(existing_blocks)
    for table in source_tables:
        expected_rows += len(ROW_RE.findall(table))
        for _tag, _attrs, content in CELL_RE.findall(table):
            text = cell_text(content).replace("\\|", "|")
            if text:
                expected_cells[text] += 1
    actual_cells, actual_rows = block_cells(blocks)
    if expected_cells != actual_cells:
        missing = sum((expected_cells - actual_cells).values())
        extra = sum((actual_cells - expected_cells).values())
        problems.append(f"单元格文本不一致: 缺失 {missing} 处, 多出 {extra} 处")
    if expected_rows != actual_rows:
        problems.append(f"表格行数不一致: 原文 {expected_rows}, 转换后 {actual_rows}")

    def other_lines(text: str) -> Counter[str]:
        """表格标记之外的行（多行表整块跳过, 代码围栏内不动）."""
        kept: list[str] = []
        in_fence = False
        in_table = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                kept.append(line)
                continue
            if in_fence:
                kept.append(line)
                continue
            if in_table:
                if "</table>" in line:
                    in_table = False
                continue
            if "<table>" in line:
                if "</table>" not in line:
                    in_table = True
                continue
            if stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 1:
                continue
            kept.append(line)
        return Counter(kept)

    if other_lines(source) != other_lines(converted):
        problems.append("表格以外的行被改动")
    return problems


def find_products(paths: list[Path]) -> list[Path]:
    """展开为含 full.md 的产物目录."""
    found: list[Path] = []
    for path in paths:
        candidates = [path] if (path / "full.md").is_file() else sorted(
            item for item in path.rglob("*") if item.is_dir() and (item / "full.md").is_file()
        )
        for candidate in candidates:
            if candidate not in found:
                found.append(candidate)
    return found


def process(product: Path, dry_run: bool) -> dict[str, object]:
    """处理一个产物：清洗正文（含 HTML 表转管道表）并校验，再删等价副本并覆盖 full.md. 校验失败抛 RuntimeError."""
    full_path = product / "full.md"
    original = full_path.read_text(encoding="utf-8")
    cleaned, stats = clean_text(original)
    problems = verify_preserved(original, cleaned)
    if problems:
        raise RuntimeError("正文丢失校验未通过，未改动任何文件：" + "; ".join(problems))
    stats["tables"] = 0
    if "<table>" in cleaned:
        converted, table_count = convert_html_tables(cleaned)
        problems = verify_tables(cleaned, converted)
        if problems:
            raise RuntimeError("HTML 表转换校验未通过，未改动任何文件：" + "; ".join(problems))
        cleaned = converted
        stats["tables"] = table_count
    base = normalize(original)
    removable: list[Path] = []
    warnings: list[str] = []
    for duplicate in sorted(product.glob(DUP_PREFIX + "*.md")):
        if normalize(duplicate.read_text(encoding="utf-8")) == base:
            removable.append(duplicate)
        else:
            warnings.append(f"{duplicate.name} 与 full.md 内容不等价, 保留")
    changed = cleaned != original
    if not dry_run:
        for duplicate in removable:
            duplicate.unlink()
        if changed:
            full_path.write_text(cleaned, encoding="utf-8", newline="")
    return {"stats": stats, "changed": changed, "pruned": len(removable), "warnings": warnings}


def selftest() -> int:
    """离线自测：校验器/覆盖逻辑/等价副本删除/不等价保留/dry-run 不落盘."""
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        product = Path(tmp) / "样例"
        product.mkdir()
        original = "\n".join([
            "# 手册",
            "",
            "## 目录",
            "",
            "1 概述....3",
            "1.1 细节....4",
            "2 参数....5",
            "",
            "## 1 概述",
            "",
            "正文内容",
            "",
            "## 1.1 细节",
            "",
            "## 注",
            "",
            "注解内容",
            "",
            "## 30 公里超视距控制",
            "",
            "## 2 参数",
            "",
        ]) + "\n"
        (product / "full.md").write_text(original, encoding="utf-8")
        equivalent = product / (DUP_PREFIX + "a.md")
        equivalent.write_text(original.replace("正文内容", "正文内容").replace("# 手册", "# 手册"), encoding="utf-8")
        different = product / (DUP_PREFIX + "b.md")
        different.write_text("# 完全不同的内容\n", encoding="utf-8")

        result = process(product, dry_run=True)
        checks.append(("dry-run 报告可删副本", result["pruned"] == 1))
        checks.append(("dry-run 不落盘", equivalent.exists() and (product / "full.md").read_text(encoding="utf-8") == original))

        cleaned, _ = clean_text(original)
        broken = cleaned.replace("正文内容", "另一段", 1)
        checks.append(("校验器能发现正文丢失", bool(verify_preserved(original, broken))))
        checks.append(("正常清洗通过校验", not verify_preserved(original, cleaned)))

        result = process(product, dry_run=False)
        after = (product / "full.md").read_text(encoding="utf-8")
        checks.append(("覆盖后目录点线消失", not any(re.search(r"\.{2,}\s*\d+", line) for line in after.splitlines())))
        checks.append(("覆盖后标题分级", "### 1.1 细节" in after and "#### 30 公里超视距控制" in after))
        checks.append(("覆盖后正文保留", "正文内容" in after and "注解内容" in after))
        checks.append(("等价副本已删除", not equivalent.exists()))
        checks.append(("不等价副本保留并警告", different.exists() and len(result["warnings"]) == 1))

    html_table = '<table><tr><td>名称</td><td>值</td></tr><tr><td>甲</td><td>1</td></tr></table>'
    converted, converted_count = convert_html_tables("说明\n\n" + html_table + "\n\n正文\n")
    checks.append(("HTML 表转管道表", converted_count == 1 and "| 名称 | 值 |" in converted and "| --- | --- |" in converted and "<table>" not in converted))
    merged, _ = convert_html_tables('<table><tr><td>a</td><td>b</td></tr><tr><td colspan="2">c</td></tr></table>')
    checks.append(("colspan 空单元格占位", "| c |  |" in merged))
    spanned, _ = convert_html_tables('<table><tr><td rowspan="2">a</td><td>b</td></tr><tr><td>c</td></tr></table>')
    checks.append(("rowspan 空单元格占位", "|  | c |" in spanned))
    escaped, _ = convert_html_tables('<table><tr><td>&lt;</td><td>a|b</td></tr><tr><td><img src="images/x.jpg"/></td><td>&amp;</td></tr></table>')
    checks.append(("实体/竖线/图片", "| < | a\\|b |" in escaped and "| ![](images/x.jpg) | & |" in escaped))
    fenced, fenced_count = convert_html_tables("```\n" + html_table + "\n```\n")
    checks.append(("代码围栏内不转换", fenced_count == 0 and "<table>" in fenced))
    checks.append(("正常转换通过表格校验", not verify_tables(html_table + "\n", convert_html_tables(html_table + "\n")[0])))
    damaged = convert_html_tables(html_table + "\n")[0].replace("甲", "", 1)
    checks.append(("校验器能发现单元格丢失", bool(verify_tables(html_table + "\n", damaged))))

    with tempfile.TemporaryDirectory() as table_tmp:
        product = Path(table_tmp) / "带表"
        product.mkdir()
        (product / "full.md").write_text("# 手册\n\n正文\n\n" + html_table + "\n", encoding="utf-8")
        dry = process(product, dry_run=True)
        checks.append(("dry-run 报告表格数且不落盘", dry["stats"]["tables"] == 1 and "<table>" in (product / "full.md").read_text(encoding="utf-8")))
        process(product, dry_run=False)
        after = (product / "full.md").read_text(encoding="utf-8")
        checks.append(("写盘后无 HTML 表", "<table>" not in after and "| 名称 | 值 |" in after))
        again = process(product, dry_run=True)
        checks.append(("重复运行无变化", not again["changed"] and again["stats"]["tables"] == 0))
    ok = True
    for name, passed in checks:
        print(f"  {'OK  ' if passed else 'FAIL'} {name}")
        ok = ok and passed
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    """命令行入口."""
    parser = argparse.ArgumentParser(description="清洗 MinerU 产物：删除等价重复 md, 还原标题层级, HTML 表转管道表, 校验后覆盖 full.md.")
    parser.add_argument("paths", nargs="*", help="产物目录，或包含产物的上级目录")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不删不改")
    parser.add_argument("--selftest", action="store_true", help="离线自测")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.paths:
        parser.error("需要产物目录（或 --selftest）")
    products = find_products([Path(item) for item in args.paths])
    if not products:
        raise SystemExit("没有找到含 full.md 的产物目录")
    failures: list[str] = []
    for product in products:
        try:
            result = process(product, args.dry_run)
        except RuntimeError as exc:
            failures.append(f"{product}: {exc}")
            continue
        stats = result["stats"]
        suffix = " (dry-run)" if args.dry_run else ""
        if not result["changed"] and not result["pruned"]:
            print(f"{product}: 无变化{suffix}")
        else:
            print(
                f"{product}: 副本删除 {result['pruned']}, 目录行 {stats['toc']}, "
                f"标题重排 {stats['renumbered']}, 注标签 {stats['notes']}, 降级 {stats['demoted']}, "
                f"表格转换 {stats['tables']}{suffix}"
            )
        for warning in result["warnings"]:
            print("警告：" + str(warning), file=sys.stderr)
    if failures:
        for failure in failures:
            print("失败：" + failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))