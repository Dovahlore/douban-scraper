# 豆瓣爬虫 · douban-spider

自动绕过豆瓣 `sec.douban.com` PoW 验证，抓取电影 / 书籍 / 音乐信息。

---

## 功能

| 特性 | 说明 |
|------|------|
| PoW 自动求解 | SHA-512 工作量证明，完全模拟浏览器行为 |
| sec 验证绕过 | 自动跟随 301/302 跳转，完成验证后继续请求 |
| 交互式 REPL | 直接运行进入命令行交互模式 |
| 批量查询 | 从 txt 文件读取关键词，结果保存为 JSON |
| JSON 输出 | `--json` 标志，方便接入其他系统 |

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 交互模式（推荐体验）
python main.py

# 3. 单次查询
python main.py -k "星际穿越"

# 4. JSON 输出
python main.py -k "Dune" --json

# 5. 批量查询（keywords.txt 每行一个关键词）
python main.py -b keywords.txt -o results.json

# 6. 搜索书籍
python main.py -k "解忧杂货店" -c book
```

---

## 命令行参数

```
usage: douban [-h] [-k KEYWORD] [-c {movie,book,music,tv}]
              [-b FILE] [-o FILE] [--json]

  -k, --keyword   搜索关键词（省略则进入交互模式）
  -c, --cat       搜索类别：movie / book / music / tv（默认 movie）
  -b, --batch     批量模式：从 txt 文件逐行读取关键词
  -o, --output    批量结果保存路径（JSON）
  --json          以 JSON 格式输出结果
```

---

## 返回字段

```json
{
  "success": true,
  "title": "星际穿越",
  "original_title": "Interstellar",
  "year": "2014",
  "date": "2014-11",
  "genres": ["剧情", "科幻", "冒险"],
  "aliases": ["星际效应", "星际穿越"],
  "poster_url": "https://img9.doubanio.com/view/photo/m/..."
}
```

---

## 工作原理

1. 请求豆瓣搜索页，获取目标条目 ID
2. 请求详情页，若触发 `sec.douban.com` 验证：
   - 解析验证表单中的 `tok` / `cha` / `red` 字段
   - 本地计算 SHA-512 PoW（找满足前缀条件的 nonce）
   - POST 验证结果，Session 自动保留 Cookie
3. 解析详情页 HTML，提取结构化信息

---

## 免责声明

本项目仅供学习研究，请勿用于商业用途或大规模抓取。
使用前请阅读豆瓣[用户协议](https://www.douban.com/about/terms)。

---

## License

MIT