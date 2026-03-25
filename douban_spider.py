import requests
import re
import hashlib
from bs4 import BeautifulSoup


# ─────────────────────────────────────────────
#  PoW 求解（模拟豆瓣 JS 挑战）
# ─────────────────────────────────────────────

def calc_sol(cha: str, difficulty: int = 4) -> int:
    """SHA-512 工作量证明，找到使哈希前 difficulty 位为 0 的 nonce。"""
    target = "0" * difficulty
    nonce = 0
    while True:
        h = hashlib.sha512(f"{cha}{nonce}".encode()).hexdigest()
        if h.startswith(target):
            return nonce
        nonce += 1


# ─────────────────────────────────────────────
#  HTTP Session
# ─────────────────────────────────────────────

def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://movie.douban.com/",
    })
    return s


# ─────────────────────────────────────────────
#  sec.douban.com 验证处理
# ─────────────────────────────────────────────

def parse_sec_form(html: str) -> tuple[str, str, str]:
    """从 sec 验证页面解析 tok / cha / red 三个字段。"""
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", id="sec")
    if not form:
        raise RuntimeError("sec form not found — 页面结构可能已变更")
    tok = form.find("input", id="tok")["value"]
    cha = form.find("input", id="cha")["value"]
    red = form.find("input", id="red")["value"]
    return tok, cha, red


def fetch_with_sec(url: str, session: requests.Session | None = None) -> str:
    """
    请求目标 URL，自动处理豆瓣 sec 验证跳转。
    返回最终页面的 HTML 文本。
    """
    s = session or build_session()
    r = s.get(url, allow_redirects=False, timeout=15)

    if r.status_code == 200:
        return r.text

    if r.status_code in (301, 302):
        sec_url = r.headers.get("Location", "")
        if not sec_url.startswith("http"):
            sec_url = "https://sec.douban.com" + sec_url

        sec_page = s.get(sec_url, timeout=15)
        tok, cha, red = parse_sec_form(sec_page.text)

        print(f"  [sec] 正在计算 PoW（cha={cha[:12]}…）")
        sol = calc_sol(cha)
        print(f"  [sec] 验证通过，nonce={sol}")

        s.post("https://sec.douban.com/c", data={"tok": tok, "cha": cha, "sol": sol, "red": red}, timeout=15)
        final = s.get(red, timeout=15)
        return final.text

    raise RuntimeError(f"意外状态码: {r.status_code}")


# ─────────────────────────────────────────────
#  核心爬虫
# ─────────────────────────────────────────────

CAT_MAP = {
    "movie":  "1002",
    "book":   "1001",
    "music":  "1003",
    "tv":     "1002",  # 电视剧与电影同类目，靠关键词区分
}


def search_douban(keyword: str, cat: str = "1002") -> dict:
    """
    搜索豆瓣并返回第一条结果的详细信息。

    Parameters
    ----------
    keyword : str   搜索关键词
    cat     : str   豆瓣搜索类目代码，默认 1002（影视）

    Returns
    -------
    dict  包含 success / error / title / original_title /
          year / aliases / poster_url / genres / date
    """
    data: dict = {
        "success": False,
        "error": "",
        "title": "",
        "original_title": "",
        "year": "",
        "date": "",
        "aliases": [],
        "poster_url": "",
        "genres": [],
    }

    session = build_session()

    # ── 1. 搜索页 ──────────────────────────────
    search_url = "https://www.douban.com/search"
    resp = session.get(search_url, params={"cat": cat, "q": keyword}, timeout=15)

    if resp.status_code != 200:
        data["error"] = f"搜索页返回状态码 {resp.status_code}"
        return data

    soup = BeautifulSoup(resp.text, "html.parser")
    result_node = soup.select_one(".result-list .result") or soup.select_one(".result")
    if not result_node:
        data["error"] = "未找到相关条目"
        return data

    link_tag = result_node.select_one(".content .title a")
    if not link_tag:
        data["error"] = "搜索结果中找不到链接"
        return data

    raw_href = link_tag.get("href", "")
    id_match = re.search(r"subject(?:/|%2F)(\d+)", raw_href)
    if not id_match:
        data["error"] = "无法从链接中解析条目 ID"
        return data

    movie_id = id_match.group(1)
    detail_url = f"https://movie.douban.com/subject/{movie_id}/"
    print(f"  [spider] 条目 ID: {movie_id}  →  {detail_url}")

    # ── 2. 详情页（带 sec 处理）─────────────────
    html = fetch_with_sec(detail_url, session)
    soup_detail = BeautifulSoup(html, "html.parser")

    # 标题 / 原名
    h1_span = soup_detail.select_one('h1 span[property="v:itemreviewed"]')
    if h1_span:
        h1_text = h1_span.get_text(strip=True)
        parts = h1_text.split(" ", 1)
        data["title"] = parts[0]
        data["original_title"] = parts[1] if len(parts) > 1 else h1_text

    # 年份
    year_span = soup_detail.select_one(".year")
    if year_span:
        data["year"] = year_span.get_text(strip=True).strip("()")

    # 类型
    data["genres"] = [
        g.get_text(strip=True)
        for g in soup_detail.select('span[property="v:genre"]')
    ]

    # 又名
    info_div = soup_detail.select_one("#info")
    if info_div:
        for span in info_div.find_all("span", class_="pl"):
            if "又名" in span.get_text():
                raw = span.next_sibling
                if raw:
                    data["aliases"] = [x.strip() for x in str(raw).strip().split("/") if x.strip()]
                break

    # 海报
    main_pic = soup_detail.select_one("#mainpic img")
    if main_pic:
        low_url = main_pic.get("src", "")
        high_url = re.sub(r"/s_ratio_.*?/", "/m/", low_url)
        high_url = re.sub(r"\.jpg", ".webp", high_url)
        data["poster_url"] = high_url

    # 上映日期（取最早）
    release_dates = soup_detail.select('span[property="v:initialReleaseDate"]')
    if release_dates:
        dates = []
        for ds in release_dates:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", ds.get("content", ""))
            if m:
                dates.append(m.group(1))
        if dates:
            data["date"] = min(dates)[:7]

    data["success"] = True
    return data