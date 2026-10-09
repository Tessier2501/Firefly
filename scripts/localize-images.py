r"""把 URL 转换产物中的远程图片下载到 images/, 并把引用改写为本地路径.

URL 产物 (MinerU 客户端) 由 full.md, main.html, content_list.json 组成, 图片是远程 URL.
本脚本下载这些图片到产物目录的 images/, 并把三个文件中的引用改写为 images/<hash>.<ext>,
使 URL 产物与 PDF 转换产物的读取方式一致.

用法:
    python localize-images.py <产物目录或上级目录> [...]
    python localize-images.py --dry-run docs\hardware\CUAV
    python localize-images.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff", ".ico"}
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*(https?://[^)\s]+)")
HTML_IMG_RE = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"', re.IGNORECASE)


def is_url_product(path: Path) -> bool:
    """URL 转换产物: 同时含 full.md, main.html, content_list.json."""
    return all((path / name).is_file() for name in ("full.md", "main.html", "content_list.json"))


def find_products(paths: list[Path]) -> list[Path]:
    """把参数展开为 URL 产物目录: 自身是产物就用自身, 否则递归查找."""
    found: list[Path] = []
    for path in paths:
        candidates = [path] if is_url_product(path) else sorted(
            item for item in path.rglob("*") if item.is_dir() and is_url_product(item)
        )
        for candidate in candidates:
            if candidate not in found:
                found.append(candidate)
    return found


def collect_urls(product: Path) -> list[str]:
    """收集产物三个文件里的远程图片 URL."""
    urls: set[str] = set()
    for match in MD_IMG_RE.finditer((product / "full.md").read_text(encoding="utf-8")):
        urls.add(match.group(1))
    for match in HTML_IMG_RE.finditer((product / "main.html").read_text(encoding="utf-8")):
        url = match.group(1).strip()
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith(("http://", "https://")):
            urls.add(url)
    data = json.loads((product / "content_list.json").read_text(encoding="utf-8"))

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "url" and isinstance(value, str) and value.startswith(("http://", "https://")):
                    urls.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return sorted(urls)


def url_ext(url: str) -> str:
    """从 URL 路径取允许的图片扩展名, 取不到返回空串."""
    ext = Path(urlparse(url).path).suffix.lower()
    return ext if ext in ALLOWED_EXT else ""


def sniff_ext(data: bytes) -> str:
    """按文件头判断图片扩展名."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF8"):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    if data.lstrip()[:4].lower() == b"<svg":
        return ".svg"
    if data.startswith(b"BM"):
        return ".bmp"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return ".tif"
    return ".png"


def fetch(url: str, timeout: float) -> bytes:
    """下载一个 URL, 失败时抛出异常."""
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Firefly localize-images)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def rewrite_refs(product: Path, mapping: dict[str, str], dry_run: bool) -> list[str]:
    """把三个文件里的远程 URL 替换为本地路径, 返回被改写的文件名."""
    changed: list[str] = []
    for name in ("full.md", "main.html", "content_list.json"):
        path = product / name
        text = path.read_text(encoding="utf-8")
        new_text = text
        for url, local in mapping.items():
            new_text = new_text.replace(url, local)
        if new_text != text:
            changed.append(name)
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")
    if not dry_run:
        files = [(product / name).read_text(encoding="utf-8") for name in ("full.md", "main.html", "content_list.json")]
        leftover = [url for url in mapping if any(url in text for text in files)]
        if leftover:
            raise RuntimeError("仍有未改写的远程引用: " + ", ".join(leftover[:3]))
    return changed


def localize(product: Path, timeout: float, dry_run: bool) -> tuple[int, int, list[str]]:
    """处理一个产物: 下载图片并改写引用. 返回 (新下载数, 复用数, 错误列表)."""
    urls = collect_urls(product)
    images = product / "images"
    mapping: dict[str, str] = {}
    downloaded = reused = 0
    errors: list[str] = []
    for url in urls:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        existing = sorted(images.glob(digest + ".*")) if images.is_dir() else []
        if existing:
            mapping[url] = f"images/{existing[0].name}"
            reused += 1
            continue
        if dry_run:
            mapping[url] = f"images/{digest}{url_ext(url)}"
            continue
        try:
            data = fetch(url, timeout)
        except Exception as exc:
            errors.append(f"{url} -> {type(exc).__name__}: {exc}")
            continue
        name = digest + (url_ext(url) or sniff_ext(data))
        images.mkdir(exist_ok=True)
        (images / name).write_bytes(data)
        mapping[url] = f"images/{name}"
        downloaded += 1
    rewrite_refs(product, mapping, dry_run)
    return downloaded, reused, errors


def selftest() -> int:
    """离线自测: 收集 URL, 命名与改写逻辑 (不联网)."""
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        product = Path(tmp) / "样例-0000"
        product.mkdir()
        (product / "full.md").write_text("![a](https://example.invalid/a.png)\n", encoding="utf-8")
        (product / "main.html").write_text('<img src="https://example.invalid/b.jpg">', encoding="utf-8")
        (product / "content_list.json").write_text(
            json.dumps([{"type": "image", "content": {"url": "https://example.invalid/c.webp", "alt": "c"}}], ensure_ascii=False),
            encoding="utf-8",
        )
        urls = collect_urls(product)
        checks.append(("收集 3 个 URL", len(urls) == 3))
        checks.append(("识别 URL 产物", is_url_product(product)))
        mapping = {url: f"images/{hashlib.sha256(url.encode()).hexdigest()}{url_ext(url)}" for url in urls}
        changed = rewrite_refs(product, mapping, dry_run=False)
        checks.append(("三个文件都被改写", set(changed) == {"full.md", "main.html", "content_list.json"}))
        checks.append(("full.md 无远程引用", "https://" not in (product / "full.md").read_text(encoding="utf-8")))
        checks.append(("main.html 无远程引用", "https://" not in (product / "main.html").read_text(encoding="utf-8")))
        parsed = json.loads((product / "content_list.json").read_text(encoding="utf-8"))
        checks.append(("content_list.json 合法且无远程引用", "https://" not in json.dumps(parsed)))
        checks.append(("扩展名解析", url_ext("https://x/y/z.PNG?q=1") == ".png" and sniff_ext(b"\x89PNG\r\n\x1a\n") == ".png"))
    ok = True
    for name, passed in checks:
        print(f"  {'OK  ' if passed else 'FAIL'} {name}")
        ok = ok and passed
    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    """命令行入口."""
    parser = argparse.ArgumentParser(description="把 URL 转换产物的远程图片下载到 images/ 并改写引用.")
    parser.add_argument("paths", nargs="*", help="URL 产物目录, 或包含产物的上级目录")
    parser.add_argument("--dry-run", action="store_true", help="只统计与预览, 不下载不写文件")
    parser.add_argument("--timeout", type=float, default=30.0, help="单张图片下载超时秒数")
    parser.add_argument("--selftest", action="store_true", help="离线自测, 不联网")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.paths:
        parser.error("需要产物目录 (或 --selftest)")
    products = find_products([Path(item) for item in args.paths])
    if not products:
        raise SystemExit("没有找到 URL 转换产物 (需同时含 full.md, main.html, content_list.json)")
    failures: list[str] = []
    for product in products:
        count = len(collect_urls(product))
        downloaded, reused, errors = localize(product, args.timeout, args.dry_run)
        print(f"{product}: 图片 {count} 个, 新下载 {downloaded}, 复用 {reused}")
        failures.extend(f"{product}: {error}" for error in errors)
    if failures:
        print("以下图片下载失败 (引用保持远程):", file=sys.stderr)
        for item in failures:
            print("  " + item, file=sys.stderr)
        return 1
    if args.dry_run:
        print("dry-run: 未写任何文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))