from __future__ import annotations

import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from scraper.race import (
    AbortScrapeError,
    build_horse_json,
    build_jockey_json,
    scrape_race_data,
)

# === Paths ===
BASE_DIR = Path(__file__).resolve().parent
RACE_JSON_PATH = (BASE_DIR.parent / "public" / "server" / "RaceTest.json").resolve()
HORSE_JSON_PATH = (BASE_DIR.parent / "public" / "server" / "HorseTest.json").resolve()
JOCKEY_JSON_PATH = (BASE_DIR.parent / "public" / "server" / "JockeyTest.json").resolve()

# JST
JST = timezone(timedelta(hours=9))

app = Flask(__name__)
CORS(app)  # React(3000) -> Flask(5000)

# Re-entrancy guard
_lock = threading.Lock()
_is_running = False


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


@app.post("/api/update/race")
def update_race():
    """
    POST endpoint called from React "更新" button.
    Body example: { "target": "saturday", "venue": "中山", "playwright": true } (optional).
    """
    global _is_running

    with _lock:
        if _is_running:
            return jsonify({"status": "busy", "message": "Update already running"}), 409
        _is_running = True

    try:
        payload = request.get_json(silent=True) or {}
        target = payload.get("target")  # "saturday" | "sunday" | "monday" | None
        venue_keyword = payload.get("venue")  # e.g., "中山", "阪神"
        source_url = payload.get("url")
        use_playwright = bool(payload.get("playwright"))
        allow_partial = bool(payload.get("allow_partial"))
        all_venues = bool(payload.get("all_venues"))
        fetch_horse_detail = bool(payload.get("fetch_horse_detail"))
        fetch_jockey_detail = bool(payload.get("fetch_jockey_detail"))

        data = scrape_race_data(
            target_day=target,
            source_url=source_url,
            venue_keyword=venue_keyword,
            use_playwright=use_playwright,
            allow_partial=allow_partial,
            all_venues=all_venues,
            fetch_horse_detail=fetch_horse_detail,
            fetch_jockey_detail=fetch_jockey_detail,
        )
        data["generated_at"] = datetime.now(JST).isoformat(timespec="seconds")

        # RaceTest.json 用に不要フィールドを削除
        from scraper.race import sanitize_race_data  # 局所 import
        atomic_write_json(RACE_JSON_PATH, sanitize_race_data(data))
        atomic_write_json(HORSE_JSON_PATH, build_horse_json(data))
        atomic_write_json(JOCKEY_JSON_PATH, build_jockey_json(data))

        return jsonify(
            {
                "status": "ok",
                "written_to": str(RACE_JSON_PATH),
                "generated_at": data["generated_at"],
            }
        )

    except AbortScrapeError as e:
        return jsonify({"status": "aborted", "reason": str(e)}), 200

    except Exception as e:
        return jsonify({"status": "error", "error": repr(e)}), 500

    finally:
        with _lock:
            _is_running = False


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
