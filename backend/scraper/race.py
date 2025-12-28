from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HTML_PATH = BASE_DIR.parent / "html.txt"
BASE_URL = "https://www.jra.go.jp"

# 更新中の時間帯ガード（火〜木 16時台は避ける）
BLOCKED_WEEKDAYS = {1, 2, 3}  # Tue, Wed, Thu
BLOCK_START_HOUR = 16
BLOCK_END_HOUR = 17  # exclusive


def make_absolute_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return BASE_URL.rstrip("/") + href
    return href


def parse_onclick_url(onclick: str) -> str:
    """
    onclick 例: onclick="return doAction('/JRADB/accessK.html', 'pw04kmk001158/EF');"
    上記から絶対URLを生成する。
    """
    if not onclick:
        return ""
    m = re.search(r"doAction\('([^']+)'\s*,\s*'([^']+)'", onclick)
    if not m:
        return ""
    path, code = m.group(1), m.group(2)
    base = BASE_URL.rstrip("/")
    if path.startswith("/"):
        path_part = path
    else:
        path_part = "/" + path
    # doAction() は hidden フォームに cname をセットして POST するが、GET でも参照できるためクエリで付与する
    return f"{base}{path_part}?cname={code}"


class AbortScrapeError(RuntimeError):
    pass


@dataclass
class Horse:
    num: str
    waku: str
    waku_color: str
    name: str
    serei: str
    weight: str
    jockey: str
    jockey_url: str
    trainer: str
    odds: str
    bataiju: str
    detail_url: str = ""
    father: str = ""
    mother: str = ""
    birthday: str = ""
    color: str = ""
    past_races: list = None

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "waku": self.waku,
            "waku_color": self.waku_color,
            "name": self.name,
            "serei": self.serei,
            "weight": self.weight,
            "jockey": self.jockey,
            "jockey_url": self.jockey_url,
            "trainer": self.trainer,
            "odds": self.odds,
            "bataiju": self.bataiju,
            "detail_url": self.detail_url,
            "father": self.father,
            "mother": self.mother,
            "birthday": self.birthday,
            "color": self.color,
            "pastRaces": self.past_races or [],
        }


@dataclass
class Race:
    race_id: str
    race_number: int
    start_time: str
    title: str
    course_distance: str
    surface: str
    horses: List[Horse]

    def to_dict(self) -> dict:
        return {
            "race_id": self.race_id,
            "race_number": self.race_number,
            "start_time": self.start_time,
            "title": self.title,
            "course_distance": self.course_distance,
            "surface": self.surface,
            "horses": [h.to_dict() for h in self.horses],
        }


def safe_text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_course(text: str) -> tuple[str, str]:
    distance = ""
    surface = ""
    m = re.search(r"([\d,]+)", text)
    if m:
        distance = m.group(1).replace(",", "")
    if "芝" in text:
        surface = "芝"
    elif "ダート" in text or "ﾀﾞｰﾄ" in text:
        surface = "ダート"
    return distance, surface or text


def parse_race_li(li) -> Race:
    num_match = re.search(r"syutsuba_(\d+)R", li.get("id", ""))
    race_number = int(num_match.group(1)) if num_match else 0
    header = li.select_one(".race_header")
    date_text = safe_text(header.select_one(".date_line .date"))
    start_time = safe_text(header.select_one(".date_line .time strong"))
    title = safe_text(li.select_one(".race_title .race_name"))
    course_text = safe_text(li.select_one(".race_title .type .course"))
    course_distance, surface = parse_course(course_text)

    venue = extract_venue_from_date(date_text) or "unknown"
    race_id = f"{venue}-{race_number:02d}" if race_number else venue

    horses: List[Horse] = []
    for row in li.select("tbody tr"):
        name = safe_text(row.select_one("td.horse"))
        if not name:
            continue
        serei_text = safe_text(row.select_one("td.age"))
        waku_text = safe_text(row.select_one("td.waku"))
        waku_color = ""
        if not waku_text:
            waku_alt = (row.select_one("td.waku img") or {}).get("alt", "")
            m = re.search(r"枠(\d+)(\D*)", waku_alt)
            if m:
                waku_text = m.group(1)
                waku_color = m.group(2).strip()
        else:
            waku_alt = (row.select_one("td.waku img") or {}).get("alt", "")
            m = re.search(r"枠(\d+)(\D*)", waku_alt)
            if m:
                waku_color = m.group(2).strip()
        horse_a = row.select_one("td.horse a")
        horse_href = (horse_a or {}).get("href", "") or ""
        if horse_href == "#":
            horse_href = ""
        detail_href = make_absolute_url(horse_href) or parse_onclick_url((horse_a or {}).get("onclick", ""))

        jockey_a = row.select_one("td.jockey a")
        jockey_href = (jockey_a or {}).get("href", "") or ""
        if jockey_href == "#":
            jockey_href = ""
        jockey_href = make_absolute_url(jockey_href) or parse_onclick_url((jockey_a or {}).get("onclick", ""))
        horses.append(
            Horse(
                num=safe_text(row.select_one("td.num")),
                waku=waku_text,
                waku_color=waku_color,
                name=name,
                serei=serei_text,
                weight=clean_kg(safe_text(row.select_one("td.weight"))),
                jockey=safe_text(row.select_one("td.jockey")),
                jockey_url=jockey_href,
                trainer=safe_text(row.select_one("td.trainer")),
                odds=safe_text(row.select_one("td.odds")),
                bataiju=clean_bataiju(safe_text(row.select_one("td.h_weight"))),
                detail_url=detail_href,
            )
        )

    return Race(
        race_id=race_id,
        race_number=race_number,
        start_time=start_time,
        title=title,
        course_distance=course_distance,
        surface=surface,
        horses=horses,
    )


def clean_kg(text: str) -> str:
    return text.replace("kg", "").replace("ＫＧ", "").strip()


def clean_bataiju(text: str) -> str:
    return text.strip()


def extract_venue_from_date(text: str) -> str:
    m = re.search(r"回(.+?)(\d+)日", text)
    return m.group(1) if m else ""


def extract_base_date(text: str) -> str:
    m = re.match(r"\s*(\d{4}年\d{1,2}月\d{1,2}日（[^）]+）)", text)
    return m.group(1) if m else text


def weekday_key(text: str) -> str:
    if "土" in text:
        return "saturday"
    if "日" in text:
        return "sunday"
    if "月" in text:
        return "monday"
    if "火" in text:
        return "tuesday"
    if "水" in text:
        return "wednesday"
    if "木" in text:
        return "thursday"
    if "金" in text:
        return "friday"
    return "unknown"


def parse_syutsuba_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    race_items = soup.select("ul.syutsuba_unit_list li[id^=syutsuba_]")
    if not race_items:
        raise AbortScrapeError("syutsuba_unit_list not found; page structure may have changed.")

    races: List[Race] = [parse_race_li(li) for li in race_items]

    first_header = race_items[0].select_one(".race_header")
    date_text = safe_text(first_header.select_one(".date_line .date"))
    base_date = extract_base_date(date_text)
    venue = extract_venue_from_date(date_text)
    day_key = weekday_key(date_text)

    venue_label = safe_text(first_header.select_one(".date_line")) or date_text
    venue_block = {"venue": venue, "venue_label": venue_label, "races": [r.to_dict() for r in races]}

    data = {
        "date": base_date,
        "days": {
            day_key: {
                "date": date_text,
                "venues": [venue_block],
            }
        },
        "venues": [
            {
                "name": venue,
                "session": venue_label or venue,
                "races": [
                    {
                        "id": race.race_id,
                        "raceNum": race.race_number,
                        "time": race.start_time,
                        "title": race.title,
                        "status": "upcoming",
                        "course_distance": race.course_distance,
                        "surface": race.surface,
                        "horses": [h.to_dict() for h in race.horses],
                    }
                    for race in races
                ],
            }
        ],
    }
    return data


def fetch_html_from_url(url: str, encoding: Optional[str] = None, timeout: int = 10) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    req = None
    # accessK.html などで cname が query に付いている場合は POST で送る
    if qs.get("cname") and parsed.path.startswith("/JRADB/accessK.html"):
        cname = qs["cname"][0]
        body = f"cname={cname}".encode("utf-8")
        # fallback: cname は query からも残しておく（サーバが GET パラメータを参照する可能性用）
        req = Request(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}?cname={cname}",
            data=body,
            headers={"User-Agent": "Mozilla/5.0"},
        )
    else:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            content = resp.read()
    except Exception as e:
        raise AbortScrapeError(f"Failed to fetch {url}: {e}")
    if encoding:
        return content.decode(encoding, errors="ignore")
    for enc in ("cp932", "shift_jis", "utf-8"):
        try:
            return content.decode(enc)
        except Exception:
            continue
    return content.decode("utf-8", errors="ignore")


def fetch_page_with_playwright(url: str, headless: bool = True, timeout: int = 15000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise AbortScrapeError(f"Playwright import failed: {e}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        raise AbortScrapeError(f"Playwright fetch failed: {e}")


def extract_labeled_value(soup, labels: List[str]) -> str:
    for label in labels:
        th = soup.find(lambda tag: tag.name in ["th", "dt"] and label in tag.get_text())
        if th:
            if th.name == "th":
                td = th.find_next("td")
                if td:
                    return td.get_text(strip=True)
            if th.name == "dt":
                dd = th.find_next("dd")
                if dd:
                    return dd.get_text(strip=True)
    return ""


def parse_horse_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    father = extract_labeled_value(soup, ["父", "父馬"])
    mother = extract_labeled_value(soup, ["母", "母馬"])
    trainer = extract_labeled_value(soup, ["調教師"])
    birthday = extract_labeled_value(soup, ["生年月日"])
    color = extract_labeled_value(soup, ["毛色"])
    serei = extract_labeled_value(soup, ["性齢", "性別・年齢"])

    past_races: List[dict] = []
    def find_idx(headers: List[str], keywords: List[str]) -> Optional[int]:
        for i, h in enumerate(headers):
            for kw in keywords:
                if kw in h:
                    return i
        return None

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            continue
        if any("年月日" in h or "レース名" in h or "距離" in h for h in headers):
            idx_date = find_idx(headers, ["年月日"])
            idx_venue = find_idx(headers, ["場"])
            idx_title = find_idx(headers, ["レース名"])
            idx_distance = find_idx(headers, ["距離"])
            idx_track = find_idx(headers, ["馬場"])
            idx_total = find_idx(headers, ["頭数"])
            idx_pop = find_idx(headers, ["人気"])
            idx_rank = find_idx(headers, ["着順"])
            idx_jockey = find_idx(headers, ["騎手"])
            idx_weight = find_idx(headers, ["負担"])
            idx_bataiju = find_idx(headers, ["馬体重"])
            idx_time = find_idx(headers, ["タイム"])
            idx_winner = find_idx(headers, ["1着", "１着", "着馬", "RT"])

            for row in table.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if not cols or (idx_date is not None and cols[0] == "年月日"):
                    continue
                past_races.append(
                    {
                        "date": cols[idx_date] if idx_date is not None and idx_date < len(cols) else "",
                        "venue": cols[idx_venue] if idx_venue is not None and idx_venue < len(cols) else "",
                        "title": cols[idx_title] if idx_title is not None and idx_title < len(cols) else "",
                        "distance": cols[idx_distance] if idx_distance is not None and idx_distance < len(cols) else "",
                        "track": cols[idx_track] if idx_track is not None and idx_track < len(cols) else "",
                        "total": cols[idx_total] if idx_total is not None and idx_total < len(cols) else "",
                        "popularity": cols[idx_pop] if idx_pop is not None and idx_pop < len(cols) else "",
                        "rank": cols[idx_rank] if idx_rank is not None and idx_rank < len(cols) else "",
                        "jockey": cols[idx_jockey] if idx_jockey is not None and idx_jockey < len(cols) else "",
                        "weight": cols[idx_weight] if idx_weight is not None and idx_weight < len(cols) else "",
                        "bataiju": cols[idx_bataiju] if idx_bataiju is not None and idx_bataiju < len(cols) else "",
                        "time": cols[idx_time] if idx_time is not None and idx_time < len(cols) else "",
                        "winner": cols[idx_winner] if idx_winner is not None and idx_winner < len(cols) else "",
                    }
                )
            break

    return {
        "father": father,
        "mother": mother,
        "trainer": trainer,
        "birthday": birthday,
        "color": color,
        "serei": serei,
        "pastRaces": past_races,
    }


def parse_jockey_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    birthday = extract_labeled_value(soup, ["生年月日", "生れ"])
    height = extract_labeled_value(soup, ["身長", "身長(cm)"])
    weight = extract_labeled_value(soup, ["体重", "体重(kg)"])
    first_license = extract_labeled_value(soup, ["初免許年", "初騎乗年", "免許年"])
    stats_current = {}
    stats_total = {}

    def parse_stats_table_by_id(table_id: str) -> Optional[dict]:
        tbl = soup.select_one(f"div#{table_id} table")
        if not tbl:
            return None
        # ヘッダーは thead のみを採用（行見出しは含めない）
        if tbl.thead:
            headers = [th.get_text(strip=True) for th in tbl.thead.find_all("th")]
        else:
            # thead が無い場合は最初の行の th をヘッダーとみなす
            first_tr = tbl.find("tr")
            headers = [th.get_text(strip=True) for th in first_tr.find_all("th")] if first_tr else []
        exclude = {"地方", "海外", "総合計"}
        headers = [h for h in headers if h not in exclude]
        rows = []
        row_candidates = tbl.tbody.find_all("tr") if tbl.tbody else tbl.find_all("tr")
        for tr in row_candidates:
            # tbody が無い場合、thead 行を拾わないようにガード
            if tr.find_parent("thead"):
                continue
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if not cells:
                continue
            # 先頭セルが除外対象ならスキップ
            if cells[0] in exclude:
                continue
            # 先頭セルが空（ヘッダー行が tbody に重複するケース）ならスキップ
            if cells[0] == "":
                continue
            # thead ヘッダーと同一の行が混入している場合はスキップ
            if headers and cells == headers:
                continue
            rows.append(cells)
        return {"headers": headers, "rows": rows}

    current_table = parse_stats_table_by_id("year_record")
    total_table = parse_stats_table_by_id("total_record")
    if current_table:
        stats_current = current_table
    if total_table:
        stats_total = total_table

    # フォールバック: ページ全文から拾う
    full_text = soup.get_text(" ", strip=True)
    if not birthday:
        m = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", full_text)
        if m:
            birthday = m.group(1)
    if not height:
        m = re.search(r"身長[:：]?\s*([0-9]+\.?[0-9]*)", full_text)
        if m:
            height = m.group(1)
    if not weight:
        m = re.search(r"体重[:：]?\s*([0-9]+\.?[0-9]*)", full_text)
        if m:
            weight = m.group(1)
    if not first_license:
        m = re.search(r"(初免許年|免許年|初騎乗年)[:：]?\s*([0-9]{4})", full_text)
        if m:
            first_license = m.group(2)
    if not stats_current:
        m = re.search(r"本年成績[:：]?\s*([^\s]+)", full_text)
        if m:
            stats_current = m.group(1)
    if not stats_total:
        m = re.search(r"(累計成績|通算成績)[:：]?\s*([^\s]+)", full_text)
        if m:
            stats_total = m.group(2)

    return {
        "birthday": birthday,
        "height": height,
        "weight": weight,
        "first_license": first_license,
        "stats_current": stats_current,
        "stats_total": stats_total,
    }


def fetch_syutsuba_with_playwright(venue_keyword: str, headless: bool = True, timeout: int = 15000) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise AbortScrapeError(f"Playwright import failed: {e}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto("https://www.jra.go.jp/", wait_until="domcontentloaded", timeout=timeout)

            page.get_by_role("link", name=re.compile("出馬表")).click(timeout=timeout)
            page.wait_for_load_state("domcontentloaded", timeout=timeout)

            page.get_by_role("link", name=re.compile(venue_keyword)).click(timeout=timeout)
            page.wait_for_load_state("domcontentloaded", timeout=timeout)

            page.get_by_role("link", name=re.compile("全てのレースを表示")).click(timeout=timeout)
            page.wait_for_selector("ul.syutsuba_unit_list", timeout=timeout)

            html = page.content()
            browser.close()
            return html
    except Exception as e:
        raise AbortScrapeError(f"Playwright navigation failed: {e}")


def fetch_all_syutsuba_with_playwright(headless: bool = True, timeout: int = 15000) -> List[tuple[str, str]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise AbortScrapeError(f"Playwright import failed: {e}")

    def is_target_link(text: str) -> bool:
        t = text.strip()
        return bool(re.search(r"\d+回.+?\d+日", t)) and ("WIN5" not in t) and ("重賞" not in t)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()

            page = context.new_page()
            page.goto("https://www.jra.go.jp/", wait_until="domcontentloaded", timeout=timeout)
            page.get_by_role("link", name=re.compile("出馬表")).click(timeout=timeout)
            page.wait_for_load_state("domcontentloaded", timeout=timeout)

            labels: List[str] = []
            for link in page.get_by_role("link").all():
                txt = (link.inner_text() or "").strip()
                if is_target_link(txt):
                    labels.append(txt)
            page.close()

            if not labels:
                browser.close()
                raise AbortScrapeError("No venue links found on 出馬表ページ。")

            results: List[tuple[str, str]] = []
            for venue_label in labels:
                pg = context.new_page()
                pg.goto("https://www.jra.go.jp/", wait_until="domcontentloaded", timeout=timeout)
                pg.get_by_role("link", name=re.compile("出馬表")).click(timeout=timeout)
                pg.wait_for_load_state("domcontentloaded", timeout=timeout)

                venue_pattern = re.escape(venue_label.split()[0])
                pg.get_by_role("link", name=re.compile(venue_pattern)).first.click(timeout=timeout * 2)
                pg.wait_for_load_state("domcontentloaded", timeout=timeout)

                pg.get_by_role("link", name=re.compile("全てのレースを表示")).click(timeout=timeout)
                pg.wait_for_selector("ul.syutsuba_unit_list", timeout=timeout)

                html = pg.content()
                results.append((venue_label, html))
                pg.close()

            browser.close()
            return results
    except Exception as e:
        raise AbortScrapeError(f"Playwright navigation failed (all venues): {e}")


def read_html_file(path: Path, encoding: Optional[str] = None) -> str:
    if encoding:
        with path.open("r", encoding=encoding, errors="ignore") as f:
            return f.read()
    for enc in ("utf-8", "cp932", "shift_jis"):
        try:
            with path.open("r", encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def is_scrape_window_ok(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone(timedelta(hours=9)))
    if now.weekday() in BLOCKED_WEEKDAYS and BLOCK_START_HOUR <= now.hour < BLOCK_END_HOUR:
        return False
    return True


def scrape_race_data(
    target_day: Optional[str] = None,
    source_url: Optional[str] = None,
    html_path: Optional[Path] = None,
    allow_partial: bool = False,
    venue_keyword: Optional[str] = None,
    use_playwright: bool = False,
    all_venues: bool = False,
    fetch_horse_detail: bool = False,
    fetch_jockey_detail: bool = False,
) -> dict:
    if not is_scrape_window_ok() and not allow_partial:
        raise AbortScrapeError("Scraping halted: site likely updating (Tue-Thu 16:00頃).")

    if all_venues:
        # 常にヘッドレスで実行（ブラウザを前面表示しない）
        venues_html = fetch_all_syutsuba_with_playwright(headless=True)
        merged: Optional[dict] = None
        for venue_label, html in venues_html:
            data = parse_syutsuba_html(html)
            if data.get("venues"):
                data["venues"][0]["session"] = venue_label
                data["venues"][0]["name"] = data["venues"][0].get("venue") or venue_label
            if merged is None:
                merged = data
            else:
                day_key = next(iter(data["days"]))
                if day_key not in merged["days"]:
                    merged["days"][day_key] = data["days"][day_key]
                else:
                    merged["days"][day_key]["venues"].extend(data["days"][day_key]["venues"])
                merged["venues"].extend(data["venues"])
        if merged is None:
            raise AbortScrapeError("No venue data fetched.")
        if target_day and target_day not in merged.get("days", {}):
            merged.setdefault("days", {})[target_day] = merged["days"][next(iter(merged["days"]))]
        data = merged
    else:
        if source_url:
            html = fetch_html_from_url(source_url)
        elif use_playwright:
            if not venue_keyword:
                raise AbortScrapeError("venue_keyword is required when use_playwright is True.")
            html = fetch_syutsuba_with_playwright(venue_keyword=venue_keyword)
        else:
            path = html_path or DEFAULT_HTML_PATH
            if not path.exists():
                raise AbortScrapeError(f"HTML file not found: {path}")
            html = read_html_file(path)
        data = parse_syutsuba_html(html)

    if target_day and target_day not in data.get("days", {}):
        data.setdefault("days", {})[target_day] = data["days"][next(iter(data["days"]))]

    if fetch_horse_detail:
        for venue in data.get("venues", []):
            for race in venue.get("races", []):
                for h in race.get("horses", []):
                    href = h.get("detail_url")
                    if not href:
                        continue
                    try:
                        html_detail = fetch_html_from_url(href)
                        detail = parse_horse_detail(html_detail)
                        if use_playwright and not detail.get("father") and not detail.get("pastRaces"):
                            html_detail = fetch_page_with_playwright(href)
                            detail = parse_horse_detail(html_detail)
                        # 上書きは値があるときだけ
                        for key in ["father", "mother", "trainer", "birthday", "color", "serei"]:
                            if detail.get(key):
                                h[key] = detail[key]
                        if detail.get("pastRaces"):
                            h["pastRaces"] = detail["pastRaces"]
                    except Exception as e:
                        h.setdefault("detail_error", str(e))

    if fetch_jockey_detail:
        jockey_seen = {}
        for venue in data.get("venues", []):
            for race in venue.get("races", []):
                for h in race.get("horses", []):
                    # clear any horse-detail fields that might bleed into jockey info
                    h["birthday"] = ""
                    h["height"] = ""
                    h["weight"] = ""
                    h["first_license"] = ""
                    h["stats_current"] = {}
                    h["stats_total"] = {}

                    name = h.get("jockey")
                    url = h.get("jockey_url")
                    if not name or not url or name in jockey_seen:
                        continue
                    try:
                        html_j = fetch_html_from_url(url)
                        detail = parse_jockey_detail(html_j)
                        if use_playwright and not detail.get("birthday") and not detail.get("stats_current"):
                            html_j = fetch_page_with_playwright(url)
                            detail = parse_jockey_detail(html_j)
                        jockey_seen[name] = detail
                    except Exception:
                        continue
        # attach back to horses for build_jockey_json
        for venue in data.get("venues", []):
            for race in venue.get("races", []):
                for h in race.get("horses", []):
                    det = jockey_seen.get(h.get("jockey"))
                    if det:
                        h.update(det)
    return data


def build_horse_json(race_data: dict) -> dict:
    horses: List[dict] = []
    for venue in race_data.get("venues", []):
        for race in venue.get("races", []):
            for h in race.get("horses", []):
                entry = dict(h)
                allowed = {
                    "name": entry.get("name", ""),
                    "serei": entry.get("serei", ""),
                    "trainer": entry.get("trainer", ""),
                    "father": entry.get("father", ""),
                    "mother": entry.get("mother", ""),
                    "birthday": entry.get("birthday", ""),
                    "color": entry.get("color", ""),
                    "pastRaces": entry.get("pastRaces", []),
                }
                horses.append(allowed)
    return {"horses": horses}


def sanitize_race_data(data: dict) -> dict:
    new_data = json.loads(json.dumps(data))

    def clean_venues(venues: List[dict]):
        for v in venues:
            for r in v.get("races", []):
                for h in r.get("horses", []):
                    for key in [
                        "odds",
                        "detail_url",
                        "jockey_url",
                    ]:
                        h.pop(key, None)

    clean_venues(new_data.get("venues", []))
    for day in new_data.get("days", {}).values():
        clean_venues(day.get("venues", []))
    return new_data


def build_jockey_json(race_data: dict) -> dict:
    jockeys = {}
    for venue in race_data.get("venues", []):
        for race in venue.get("races", []):
            for h in race.get("horses", []):
                name = h.get("jockey", "")
                if not name:
                    continue
                info = jockeys.setdefault(
                    name,
                    {
                        "name": name,
                        "birthday": h.get("birthday", ""),
                        "height": h.get("height", ""),
                        "weight": h.get("weight", ""),
                        "first_license": h.get("first_license", ""),
                        "stats_current": h.get("stats_current", ""),
                        "stats_total": h.get("stats_total", ""),
                    },
                )
    return {"jockeys": list(jockeys.values())}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrape JRA 出馬表 and dump JSON.")
    parser.add_argument("--url", help="URL to fetch 出馬表 HTML from.")
    parser.add_argument("--html", help="Local HTML path to read.")
    parser.add_argument("--out", help="Output RaceTest.json path.")
    parser.add_argument("--horses", help="Output HorseTest.json path.")
    parser.add_argument("--jockeys", help="Output JockeyTest.json path.")
    parser.add_argument("--target-day", help='Hint like "saturday".')
    parser.add_argument("--allow-partial", action="store_true", help="Skip availability guard (for dev/off-hours).")
    parser.add_argument("--venue", help="Venue keyword to click when using Playwright (e.g., 中山, 阪神).")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright navigation from jra.go.jp home.")
    parser.add_argument("--all-venues", action="store_true", help="Fetch all venues from the 出馬表一覧 via Playwright.")
    parser.add_argument("--fetch-horse-detail", action="store_true", help="Fetch horse detail pages and enrich HorseTest.json.")
    args = parser.parse_args()

    html_path = Path(args.html) if args.html else None
    race_data = scrape_race_data(
        target_day=args.target_day,
        source_url=args.url,
        html_path=html_path,
        allow_partial=args.allow_partial,
        venue_keyword=args.venue,
        use_playwright=args.playwright,
        all_venues=args.all_venues,
        fetch_horse_detail=args.fetch_horse_detail,
    )
    race_data["generated_at"] = None

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(sanitize_race_data(race_data), f, ensure_ascii=False, indent=2)

    if args.horses:
        horse_data = build_horse_json(race_data)
        Path(args.horses).parent.mkdir(parents=True, exist_ok=True)
        with open(args.horses, "w", encoding="utf-8") as f:
            json.dump(horse_data, f, ensure_ascii=False, indent=2)

    if args.jockeys:
        jockey_data = build_jockey_json(race_data)
        Path(args.jockeys).parent.mkdir(parents=True, exist_ok=True)
        with open(args.jockeys, "w", encoding="utf-8") as f:
            json.dump(jockey_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
