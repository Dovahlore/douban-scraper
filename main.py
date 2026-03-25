"""
豆瓣信息爬虫 — 交互式命令行界面
支持单次查询、批量查询（逐行读取 txt）、以及 JSON 输出
"""

import argparse
import json
import sys
from pathlib import Path

from douban_spider import search_douban, CAT_MAP


# ─────────────────────────────────────────────
#  Pretty Printer
# ─────────────────────────────────────────────

def print_result(data: dict, json_mode: bool = False) -> None:
    if json_mode:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if not data["success"]:
        print(f"  ✗ 失败：{data['error']}")
        return

    sep = "─" * 44
    print(sep)
    print(f"  标题      : {data['title']}")
    if data["original_title"] and data["original_title"] != data["title"]:
        print(f"  原名      : {data['original_title']}")
    print(f"  年份      : {data['year']}   上映: {data['date']}")
    print(f"  类型      : {'  '.join(data['genres'])}")
    if data["aliases"]:
        print(f"  又名      : {' / '.join(data['aliases'])}")
    if data["poster_url"]:
        print(f"  海报      : {data['poster_url']}")
    print(sep)


# ─────────────────────────────────────────────
#  交互式 REPL 模式
# ─────────────────────────────────────────────

def interactive_mode(cat: str, json_mode: bool) -> None:
    print("豆瓣爬虫 — 交互模式")
    print("输入电影 / 书名 / 专辑名称，直接回车查询；输入 q 退出\n")

    while True:
        try:
            keyword = input("🔍 搜索 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not keyword:
            continue
        if keyword.lower() in ("q", "quit", "exit"):
            print("再见！")
            break

        print(f"  正在查询「{keyword}」…")
        result = search_douban(keyword, cat=cat)
        print_result(result, json_mode)
        print()


# ─────────────────────────────────────────────
#  批量模式（从文件读取关键词）
# ─────────────────────────────────────────────

def batch_mode(filepath: str, cat: str, json_mode: bool, output: str | None) -> None:
    keywords = Path(filepath).read_text(encoding="utf-8").splitlines()
    keywords = [k.strip() for k in keywords if k.strip()]

    print(f"批量查询 {len(keywords)} 个关键词…\n")
    results = []

    for i, kw in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] 查询: {kw}")
        result = search_douban(kw, cat=cat)
        result["keyword"] = kw
        results.append(result)
        print_result(result, json_mode=False)
        print()

    if output:
        Path(output).write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✓ 结果已保存到 {output}")
    elif json_mode:
        print(json.dumps(results, ensure_ascii=False, indent=2))


# ─────────────────────────────────────────────
#  CLI 入口
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="douban",
        description="豆瓣电影 / 书籍 / 音乐信息爬虫（自动处理 sec 验证）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                          # 进入交互模式
  python main.py -k "星际穿越"           # 单次查询
  python main.py -k "Dune" --json         # JSON 输出
  python main.py -b keywords.txt -o out.json   # 批量查询并保存
  python main.py -k "解忧杂货店" -c book  # 搜索书籍
        """,
    )
    parser.add_argument("-k", "--keyword", help="搜索关键词（省略则进入交互模式）")
    parser.add_argument(
        "-c", "--cat",
        default="movie",
        choices=list(CAT_MAP.keys()),
        help="搜索类别（默认: movie）",
    )
    parser.add_argument("-b", "--batch", metavar="FILE", help="批量模式：从文本文件逐行读取关键词")
    parser.add_argument("-o", "--output", metavar="FILE", help="批量模式结果保存为 JSON 文件")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="以 JSON 格式输出结果")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cat_code = CAT_MAP.get(args.cat, "1002")

    # 批量模式
    if args.batch:
        batch_mode(args.batch, cat=cat_code, json_mode=args.json_mode, output=args.output)
        return

    # 单次查询
    if args.keyword:
        print(f"正在查询「{args.keyword}」…")
        result = search_douban(args.keyword, cat=cat_code)
        print_result(result, json_mode=args.json_mode)
        return

    # 无参数 → 交互模式
    interactive_mode(cat=cat_code, json_mode=args.json_mode)


if __name__ == "__main__":
    main()