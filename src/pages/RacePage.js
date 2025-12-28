import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import "./RacePage.css";

const YOSOU_MARKS = [
  { value: "none", label: "---", className: "yosou-none" },
  { value: "honmei", label: "◎", className: "yosou-honmei" },
  { value: "taikou", label: "◯", className: "yosou-taikou" },
  { value: "tanana", label: "▲", className: "yosou-kuro" },
  { value: "renshita", label: "△", className: "yosou-shiro" },
  { value: "oshirase", label: "☆", className: "yosou-ana" }
];

const COLUMN_LABELS = {
  yosou: "予想印",
  serei: "性齢",
  weight: "斤量",
  jockey: "騎手",
  trainer: "調教師",
  bataiju: "馬体重"
};

const EMPTY_RACE_DATA = {
  title: "レース名（未取得）",
  race_number: "",
  start_time: "",
  course_distance: "",
  surface: "",
  horses: []
};

const WAKU_COLOR_MAP = {
  黒: "#000",
  白: "#fff",
  赤: "#f00",
  青: "#00f",
  黄: "#ff0",
  緑: "#080",
  橙: "#fa0",
  桃: "#fbc"
};

function findRace(json, venue, raceNum) {
  // 新形式: days.*.venues[*].races
  const dayEntries = Object.values(json?.days || {});
  for (const day of dayEntries) {
    for (const v of day?.venues || []) {
      if (v.venue === venue || v.name === venue) {
        const r = (v.races || []).find(
          (race) =>
            race.race_number?.toString() === raceNum ||
            race.raceNum?.toString() === raceNum
        );
        if (r) return r;
      }
    }
  }
  // 旧形式: top-level venues
  const legacyVenue = (json?.venues || []).find(
    (v) => v.name === venue || v.venue === venue
  );
  if (legacyVenue) {
    const r = (legacyVenue.races || []).find(
      (race) =>
        race.race_number?.toString() === raceNum ||
        race.raceNum?.toString() === raceNum
    );
    if (r) return r;
  }
  return null;
}

function normalizeRace(race) {
  if (!race) return EMPTY_RACE_DATA;
  return {
    title: race.title || EMPTY_RACE_DATA.title,
    race_number: race.race_number || race.raceNum || "",
    start_time: race.start_time || race.time || "",
    course_distance: race.course_distance || "",
    surface: race.surface || "",
    horses: race.horses || []
  };
}

export default function RacePage() {
  const { venue, raceNum } = useParams();
  const [data, setData] = useState(EMPTY_RACE_DATA);
  const [visible, setVisible] = useState({
    yosou: true,
    serei: true,
    weight: true,
    jockey: true,
    trainer: true,
    bataiju: true
  });
  const [yosou, setYosou] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/server/RaceTest.json");
        const json = await res.json();
        const race = findRace(json, venue, raceNum);
        setData(normalizeRace(race));
      } catch (err) {
        console.error(err);
        setData(EMPTY_RACE_DATA);
      }
    }
    load();
  }, [venue, raceNum]);

  const getMarkClass = (num) => {
    const selected = yosou[num] || "none";
    const markData = YOSOU_MARKS.find((m) => m.value === selected);
    return markData ? markData.className : "";
  };

  const getWakuStyle = (horse) => {
    if (horse.waku) {
      return {};
    }
    const colorName = horse.waku_color || "";
    const color = WAKU_COLOR_MAP[colorName];
    if (!color) return {};
    return { backgroundColor: color, color: colorName === "白" ? "#000" : "#fff" };
  };

  const courseInfo =
    data.course_distance || data.surface
      ? `${data.course_distance ? `${data.course_distance}m` : ""}${
          data.surface ? ` (${data.surface})` : ""
        }`
      : "";

  return (
    <div className="race-container">
      <header className="race-header">
        <Link to="/" className="back-button">
          ← メインページへ戻る
        </Link>
        <div className="race-header-main">
          <h1>
            {data.race_number ? <span className="race-number">{data.race_number}R</span> : null}
            <span className="race-title">{data.title}</span>
          </h1>
          <div className="race-meta">
            <div>発走時刻：{data.start_time || "-"}</div>
            {courseInfo ? <div>　{courseInfo}</div> : null}
          </div>
        </div>
      </header>

      {/* 表示項目カスタマイズ */}
      <div className="control-panel">
        <h2>表示項目カスタマイズ</h2>
        <div className="control-row">
          {Object.keys(visible).map((key) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={visible[key]}
                onChange={() => setVisible((prev) => ({ ...prev, [key]: !prev[key] }))}
              />
              {COLUMN_LABELS[key]}
            </label>
          ))}
        </div>
      </div>

      {/* 出馬表 */}
      <table id="race-table">
        <thead>
          <tr>
            {visible.yosou && <th>印</th>}
            <th>枠</th>
            <th>馬番</th>
            <th>馬名</th>
            {visible.serei && <th>性齢</th>}
            {visible.weight && <th>斤量</th>}
            {visible.jockey && <th>騎手</th>}
            {visible.trainer && <th>調教師</th>}
            {visible.bataiju && <th>馬体重</th>}
          </tr>
        </thead>
        <tbody>
          {data.horses.length === 0 ? (
            <tr>
              <td colSpan="9" style={{ textAlign: "center", padding: "20px" }}>
                データなし（ダミー表示）
              </td>
            </tr>
          ) : (
            data.horses.map((h) => (
              <tr key={`${h.waku}-${h.num}-${h.name}`}>
                {visible.yosou && (
                  <td className={getMarkClass(h.num)}>
                    <select
                      value={yosou[h.num] || "none"}
                      onChange={(e) =>
                        setYosou((prev) => ({ ...prev, [h.num]: e.target.value }))
                      }
                    >
                      {YOSOU_MARKS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                  </td>
                )}
                <td
                  className={`waku-cell ${h.waku ? `waku-${h.waku}` : ""}`}
                  style={getWakuStyle(h)}
                >
                  {h.waku}
                </td>
                <td>{h.num}</td>
                <td>
                  <Link
                    to={`/horse/${encodeURIComponent(h.name)}`}
                    state={{ venue, raceNum }}
                    className="horse-link"
                  >
                    {h.name}
                  </Link>
                </td>
                {visible.serei && <td>{h.serei}</td>}
                {visible.weight && <td>{h.weight}</td>}
                {visible.jockey && (
                  <td>
                    <Link
                      to={`/jockey/${encodeURIComponent(h.jockey)}`}
                      state={{ venue, raceNum }}
                    >
                      {h.jockey}
                    </Link>
                  </td>
                )}
                {visible.trainer && <td>{h.trainer}</td>}
                {visible.bataiju && <td>{h.bataiju}</td>}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
