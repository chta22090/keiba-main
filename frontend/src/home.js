// keiba-main/keiba-main/src/pages/home.js

import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import "./App.css";
import "./App.mobile.css";

const RaceCell = ({ race, selectedRaceId, onRaceSelect, venue }) => {
  const isSelected = selectedRaceId === race.id;
  let cellClasses = "race-cell";
  if (isSelected) cellClasses += " selected";
  else cellClasses += " upcoming";

  return (
    <Link
      to={`/race/${venue.name}/${race.raceNum}`}
      className={cellClasses}
      onClick={() => onRaceSelect(race.id)}
    >
      <div className="race-num">{race.raceNum}R</div>
      <div className="race-time">{race.time}</div>
    </Link>
  );
};

const extractBaseDate = (text = "") => {
  const m = text.match(/^\s*(\d{4}年\d{1,2}月\d{1,2}日)/);
  return m ? m[1] : text;
};

const formatVenueLabel = (venue = {}) => {
  const raw = venue.venue_label || venue.session || "";
  if (raw) {
    const m = raw.match(/\s(\d+回.*?\d+日)/);
    if (m) return m[1];
  }
  return venue.venue || "";
};

const App = () => {
  const [raceData, setRaceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedRaceId, setSelectedRaceId] = useState(null);
  const [message, setMessage] = useState("");

  const loadRaceData = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await fetch(`/server/RaceTest.json?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) throw new Error("JSON読み込み失敗");
      const json = await res.json();
      setRaceData(json);
    } catch (err) {
      console.error(err);
      setRaceData(null);
    } finally {
      setLoading(false);
    }
  };

  const updateRaceData = async () => {
    setLoading(true);
    setMessage("更新中...");
    try {
      const res = await fetch("http://localhost:5000/api/update/race", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target: "saturday",
          playwright: true,
          allow_partial: true,
          all_venues: true,
          fetch_horse_detail: true,
          fetch_jockey_detail: true
        })
      });

      const result = await res.json();

      if (result.status === "busy") {
        setMessage("更新処理が実行中です。少し待ってから再度お試しください。");
        return;
      }
      if (result.status === "aborted") {
        setMessage(`今回は更新を中止しました: ${result.reason}`);
        return;
      }
      if (result.status === "ok") {
        setMessage("更新完了。最新データを読み込みます...");
        await loadRaceData();
        setMessage("更新完了");
        return;
      }
      setMessage(`更新に失敗しました: ${JSON.stringify(result)}`);
    } catch (err) {
      console.error(err);
      setMessage("更新に失敗しました。Flaskに接続できませんでした。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRaceData();
  }, []);

  if (loading) return <p style={{ padding: "20px" }}>読み込み中...</p>;
  if (!raceData) return <p style={{ padding: "20px" }}>データがありません</p>;

  const days = Object.entries(raceData.days || {});
  const COLUMN_WIDTH_PX = 200;
  const GAP_PX = 20;
  const PADDING_X_PX = 24;

  return (
    <div className="app-container">
      <div className="app-main-content">
        {/* 上部ボタン */}
        <header className="main-header" style={{ gap: "8px", flexWrap: "wrap" }}>
          <Link to="/baken" className="nav-button">
            馬券の買い方
          </Link>
          <Link to="/use" className="nav-button">
            使い方
          </Link>
          <button type="button" className="nav-button update-button" onClick={updateRaceData}>
            更新
          </button>
        </header>

        {/* メッセージ表示 */}
        {message ? (
          <div style={{ padding: "0 20px 10px", fontSize: "14px" }}>{message}</div>
        ) : null}

        {days.map(([dayKey, dayData]) => {
          const venues = Array.isArray(dayData?.venues) ? dayData.venues : [];
          const dateLabel = extractBaseDate(dayData?.date || "");
          const appWidth =
            COLUMN_WIDTH_PX * venues.length +
            GAP_PX * Math.max(venues.length - 1, 0) +
            PADDING_X_PX;
          const raceColumnsStyle = {
            display: "flex",
            justifyContent: "space-between",
            padding: "16px 0px 36px",
            gap: `${GAP_PX}px`,
            width: "100%",
            maxWidth: `${appWidth}px`,
            margin: "0 auto"
          };

          return (
            <section key={dayKey} style={{ marginBottom: "32px" }}>
              <div className="date-line">
                <strong>{dateLabel}</strong>
              </div>

              {/* 開催場 */}
              <div className="course-header-wrapper">
                {venues.map((venue) => (
                  <span
                    key={venue.venue}
                    className="course-header-item"
                    style={{ width: `${COLUMN_WIDTH_PX}px` }}
                  >
                    <strong>{formatVenueLabel(venue)}</strong>
                  </span>
                ))}
              </div>

              {/* レース一覧 */}
              <div className="race-columns-container" style={raceColumnsStyle}>
                {venues.map((venue) => (
                  <div
                    key={venue.venue}
                    id={`venue-${venue.venue}-${dayKey}`}
                    className="race-column"
                    style={{ width: `${COLUMN_WIDTH_PX}px`, gap: "16px" }}
                  >
                    {(venue.races || []).map((race) => (
                      <RaceCell
                        key={race.race_id}
                        race={{
                          id: race.race_id,
                          raceNum: race.race_number,
                          time: race.start_time
                        }}
                        selectedRaceId={selectedRaceId}
                        onRaceSelect={setSelectedRaceId}
                        venue={{ name: venue.venue }}
                      />
                    ))}
                  </div>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
};

export default App;
