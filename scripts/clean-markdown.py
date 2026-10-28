r"""清洗转换产物：删除等价重复 md, 还原目录与标题层级, 自动展开 HTML 表, URL 产物先本地化图片, 校验后覆盖 full.md 并删除转换中间 JSON。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
TOC_LINE_RE = re.compile(r"^(.+?)\.{2,}\s*(\d+)\s*$")
NUMBER_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*(.*)$")
NOTE_LABELS = {"注", "注意", "警告", "提示", "说明"}
DUP_PREFIX = "MinerU_markdown_"
JSON_PATTERNS = (
    "content_list.json",
    "*_content_list.json",
    "*_content_list_v2.json",
    "*_model.json",
    "block_list.json",
    "layout.json",
)
LOCALIZE_TIMEOUT = 30.0
TABLE_RE = re.compile(r"(?s)<table([^>]*)>(.*?)</table>")
TR_RE = re.compile(r"(?s)<tr([^>]*)>(.*?)</tr>")
CELL_RE = re.compile(r"(?s)<t([dh])([^>]*)>(.*?)</t\1>")
UNSUPPORTED_TABLE_RE = re.compile(r"(?i)<(thead|tbody|tfoot|caption|colgroup|col|table)\b")
TABLE_INDENT = "  "

_localizer: object | None = None


def localizer() -> object:
    """加载同目录的 localize-images.py 模块（文件名带连字符，无法直接 import）."""
    global _localizer
    if _localizer is None:
        path = Path(__file__).with_name("localize-images.py")
        spec = importlib.util.spec_from_file_location("localize_images", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _localizer = module
    return _localizer


def collect_json_files(product: Path) -> list[Path]:
    """产物目录下待删除的转换中间 JSON（content_list/版面/块/模型）."""
    found: list[Path] = []
    for pattern in JSON_PATTERNS:
        for path in sorted(product.glob(pattern)):
            if path not in found:
                found.append(path)
    return found


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


def format_table_lines(table_html: str) -> list[str] | None:
    """把单张 HTML 表展开为 2 空格缩进的多行; 结构不支持时返回 None（保持原样）."""
    match = TABLE_RE.fullmatch(table_html)
    if not match:
        return None
    attrs, inner = match.group(1), match.group(2)
    if UNSUPPORTED_TABLE_RE.search(inner):
        return None
    rows = TR_RE.findall(inner)
    if not rows or TR_RE.sub("", inner).strip():
        return None
    lines: list[str] = [f"<table{attrs}>"]
    for tr_attrs, row_inner in rows:
        cells = CELL_RE.findall(row_inner)
        if not cells or CELL_RE.sub("", row_inner).strip():
            return None
        lines.append(f"{TABLE_INDENT}<tr{tr_attrs}>")
        for tag, cell_attrs, content in cells:
            lines.append(f"{TABLE_INDENT * 2}<t{tag}{cell_attrs}>{content.strip()}</t{tag}>")
        lines.append(f"{TABLE_INDENT}</tr>")
    lines.append("</table>")
    return lines


def format_html_tables(text: str) -> tuple[str, int]:
    """把正文（代码围栏外）的 HTML 表展开为缩进多行; 返回 (文本, 格式化张数)."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    out: list[str] = []
    formatted = 0
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            index += 1
            continue
        if in_fence or "<table" not in line:
            out.append(line)
            index += 1
            continue
        block = line
        while "</table>" not in block and index + 1 < len(lines):
            index += 1
            block += newline + lines[index]

        def replace(match: re.Match[str]) -> str:
            nonlocal formatted
            candidate = format_table_lines(match.group(0))
            if candidate is None:
                return match.group(0)
            if candidate != match.group(0).splitlines():
                formatted += 1
            return "\n".join(candidate)

        out.extend(TABLE_RE.sub(replace, block).split("\n"))
        index += 1
    result = newline.join(out)
    if text.endswith(("\n", "\r\n")):
        result += newline
    return result, formatted


def verify_formatting(source: str, formatted: str) -> list[str]:
    """校验 HTML 表格式化只改了空白: 归一化文本一致, 表数一致, 表内无空行."""
    problems: list[str] = []
    if normalize(source) != normalize(formatted):
        problems.append("格式化改动了正文内容（去空白后不一致）")
    source_tables = len(TABLE_RE.findall(source))
    formatted_tables = len(TABLE_RE.findall(formatted))
    if source_tables != formatted_tables:
        problems.append(f"表格数量不一致: 原文 {source_tables}, 格式化后 {formatted_tables}")
    in_table = False
    for line in formatted.splitlines():
        stripped = line.strip()
        if stripped.startswith("<table"):
            in_table = True
            continue
        if in_table and stripped.startswith("</table>"):
            in_table = False
            continue
        if in_table and not stripped:
            problems.append("格式化后的表格内部出现空行")
            break
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
    """处理一个产物：清洗正文并展开 HTML 表，URL 产物先本地化图片，再覆盖 full.md、删等价副本与中间 JSON. 校验失败抛 RuntimeError."""
    full_path = product / "full.md"
    original = full_path.read_text(encoding="utf-8")
    cleaned, stats = clean_text(original)
    problems = verify_preserved(original, cleaned)
    if problems:
        raise RuntimeError("正文丢失校验未通过，未改动任何文件：" + "; ".join(problems))
    stats["tables"] = 0
    if "<table" in cleaned:
        formatted, table_count = format_html_tables(cleaned)
        problems = verify_formatting(cleaned, formatted)
        if problems:
            raise RuntimeError("HTML 表格式化校验未通过，未改动任何文件：" + "; ".join(problems))
        cleaned = formatted
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
    module = localizer()
    url_product = module.is_url_product(product)
    pending_urls = module.collect_urls(product) if url_product else []
    json_files = collect_json_files(product)
    localized = len(pending_urls) if dry_run else 0
    if not dry_run:
        for duplicate in removable:
            duplicate.unlink()
        if changed:
            full_path.write_text(cleaned, encoding="utf-8", newline="")
        if url_product:
            downloaded, reused, errors = module.localize(product, LOCALIZE_TIMEOUT, dry_run=False)
            if errors:
                raise RuntimeError("图片本地化失败，未删除转换 JSON：" + "; ".join(errors[:3]))
            localized = downloaded + reused
        for path in json_files:
            path.unlink()
    return {
        "stats": stats,
        "changed": changed,
        "pruned": len(removable),
        "localized": localized,
        "json": len(json_files),
        "warnings": warnings,
    }


def selftest() -> int:
    """离线自测：校验器/覆盖逻辑/等价副本删除/HTML 表格式化/图片本地化/JSON 删除/dry-run 不落盘."""
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

    one_line_table = '<table><tr><td>名称</td><td>值</td></tr><tr><td>甲</td><td>1</td></tr></table>'
    formatted_table, formatted_count = format_html_tables("说明\n\n" + one_line_table + "\n\n正文\n")
    expected = "\n".join([
        "<table>",
        "  <tr>",
        "    <td>名称</td>",
        "    <td>值</td>",
        "  </tr>",
        "  <tr>",
        "    <td>甲</td>",
        "    <td>1</td>",
        "  </tr>",
        "</table>",
    ])
    checks.append(("HTML 表展开为缩进多行", formatted_count == 1 and expected in formatted_table and "<table><tr>" not in formatted_table))
    once, count_once = format_html_tables(one_line_table)
    twice, count_twice = format_html_tables(once)
    checks.append(("格式化幂等", count_once == 1 and count_twice == 0 and twice == once))
    with_attrs = '<table><tr><td colspan="2">a</td></tr><tr><td colspan="2" rowspan="1">b</td></tr></table>'
    attrs_formatted, _ = format_html_tables(with_attrs)
    checks.append(("保留标签属性", '<td colspan="2">a</td>' in attrs_formatted and '<td colspan="2" rowspan="1">b</td>' in attrs_formatted))
    fenced, fenced_count = format_html_tables("```\n" + one_line_table + "\n```\n")
    checks.append(("代码围栏内不处理", fenced_count == 0 and fenced == "```\n" + one_line_table + "\n```\n"))
    unsupported, unsupported_count = format_html_tables('<table><thead><tr><th>a</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table>')
    checks.append(("不支持的结构保持原样", unsupported_count == 0 and "<thead>" in unsupported))
    checks.append(("格式化通过校验", not verify_formatting(one_line_table + "\n", format_html_tables(one_line_table + "\n")[0])))
    checks.append(("校验器能发现内容改动", bool(verify_formatting(one_line_table + "\n", format_html_tables(one_line_table + "\n")[0].replace("甲", "乙")))))
    checks.append(("表格内不插入空行", "\n\n" not in format_html_tables(one_line_table)[0].strip()))

    with tempfile.TemporaryDirectory() as table_tmp:
        product = Path(table_tmp) / "带表"
        product.mkdir()
        (product / "full.md").write_text("# 手册\n\n正文\n\n" + one_line_table + "\n", encoding="utf-8")
        duplicate = product / (DUP_PREFIX + "dup.md")
        duplicate.write_text("# 手册\n\n正文\n\n" + one_line_table + "\n", encoding="utf-8")
        dry = process(product, dry_run=True)
        checks.append(("dry-run 报告表格数且不落盘", dry["stats"]["tables"] == 1 and dry["pruned"] == 1 and "<table><tr>" in (product / "full.md").read_text(encoding="utf-8")))
        process(product, dry_run=False)
        after = (product / "full.md").read_text(encoding="utf-8")
        checks.append(("写盘后表格已展开且副本已删", "  <tr>" in after and "<table><tr>" not in after and not duplicate.exists()))
        again = process(product, dry_run=True)
        checks.append(("重复运行无变化", not again["changed"] and again["stats"]["tables"] == 0))

    with tempfile.TemporaryDirectory() as json_tmp:
        product = Path(json_tmp) / "带JSON"
        product.mkdir()
        (product / "full.md").write_text("# 手册\n\n正文\n", encoding="utf-8")
        for name in ("abc_content_list.json", "abc_content_list_v2.json", "abc_model.json", "block_list.json", "layout.json"):
            (product / name).write_text("[]", encoding="utf-8")
        (product / "custom.json").write_text("[]", encoding="utf-8")
        (product / "abc_origin.pdf").write_bytes(b"%PDF-1.4")
        dry = process(product, dry_run=True)
        checks.append(("dry-run 报告 JSON 删除数且不落盘", dry["json"] == 5 and (product / "layout.json").exists()))
        result = process(product, dry_run=False)
        checks.append(("实跑删除转换 JSON", result["json"] == 5 and not any(
            (product / name).exists()
            for name in ("abc_content_list.json", "abc_content_list_v2.json", "abc_model.json", "block_list.json", "layout.json")
        )))
        checks.append(("JSON 之外的产物保留", (product / "custom.json").exists() and (product / "abc_origin.pdf").exists()))
        again = process(product, dry_run=True)
        checks.append(("删 JSON 后再次运行无变化", not again["changed"] and again["json"] == 0))

    with tempfile.TemporaryDirectory() as url_tmp:
        product = Path(url_tmp) / "URL产物"
        product.mkdir()
        (product / "full.md").write_text("![a](https://example.invalid/a.png)\n", encoding="utf-8")
        (product / "main.html").write_text('<img src="https://example.invalid/b.jpg">', encoding="utf-8")
        (product / "content_list.json").write_text(
            json.dumps([{"type": "image", "content": {"url": "https://example.invalid/c.webp"}}], ensure_ascii=False),
            encoding="utf-8",
        )
        module = localizer()
        original_fetch = module.fetch
        module.fetch = lambda url, timeout: b"\x89PNG\r\n\x1a\nfake"
        try:
            dry = process(product, dry_run=True)
            checks.append(("URL 产物 dry-run 报告本地化与 JSON 删除", dry["localized"] == 3 and dry["json"] == 1 and (product / "content_list.json").exists()))
            result = process(product, dry_run=False)
        finally:
            module.fetch = original_fetch
        after = (product / "full.md").read_text(encoding="utf-8")
        checks.append(("URL 产物先本地化再删 JSON", result["localized"] == 3 and result["json"] == 1 and "https://" not in after))
        checks.append(("本地化后 JSON 已删且 main.html 保留", not (product / "content_list.json").exists() and (product / "main.html").exists()))
        refs = re.findall(r"!\[[^\]]*\]\(images/([^)]+)\)", after)
        checks.append(("本地图片文件已生成", len(refs) == 1 and (product / "images" / refs[0]).is_file()))
    ok = True
    for name, passed in checks:
        print(f"  {'OK  ' if passed else 'FAIL'} {name}")
        ok = ok and passed
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    """命令行入口."""
    parser = argparse.ArgumentParser(description="清洗转换产物：还原标题层级、展开 HTML 表；URL 产物先本地化图片；校验后覆盖 full.md，删除等价副本与转换中间 JSON.")
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
        extras: list[str] = []
        if result["localized"]:
            extras.append(f"图片本地化 {result['localized']}")
        if result["json"]:
            extras.append(f"JSON 删除 {result['json']}")
        if not result["changed"] and not result["pruned"] and not extras:
            print(f"{product}: 无变化{suffix}")
        else:
            message = (
                f"{product}: 副本删除 {result['pruned']}, 目录行 {stats['toc']}, "
                f"标题重排 {stats['renumbered']}, 注标签 {stats['notes']}, 降级 {stats['demoted']}, "
                f"表格格式化 {stats['tables']}"
            )
            if extras:
                message += ", " + ", ".join(extras)
            print(message + suffix)
        for warning in result["warnings"]:
            print("警告：" + str(warning), file=sys.stderr)
    if failures:
        for failure in failures:
            print("失败：" + failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
