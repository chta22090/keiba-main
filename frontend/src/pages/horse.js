import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./horse.css";

export default function Horse() {
  const { horseName } = useParams();
  const [horse, setHorse] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/server/HorseTest.json");
        const json = await res.json();

        const decodedName = decodeURIComponent(horseName);
        const horseData = json.horses.find((h) => h.name === decodedName);

        if (!horseData) throw new Error("馬データなし");

        setHorse(horseData);
      } catch (err) {
        console.error(err);
        setHorse(null);
      }
    }

    load();
  }, [horseName]);

  if (!horse) {
    return (
      <div className="horse-container">
        <button onClick={() => navigate(-1)}>← 戻る</button>
        <h1>馬データなし</h1>
        <p>データが存在しないか、読み込み中です。</p>
      </div>
    );
  }

  return (
    <div className="horse-container">
      <button onClick={() => navigate(-1)}>← 戻る</button>
      <h1>{horse.name}</h1>

      <table>
        <tbody>
          <tr><td>父</td><td>{horse.father || "－"}</td></tr>
          <tr><td>母</td><td>{horse.mother || "－"}</td></tr>
          <tr><td>性齢</td><td>{horse.serei || "－"}</td></tr>
          <tr><td>調教師</td><td>{horse.trainer || "－"}</td></tr>
          <tr><td>生年月日</td><td>{horse.birthday || "－"}</td></tr>
          <tr><td>毛色</td><td>{horse.color || "－"}</td></tr>
        </tbody>
      </table>

      <div className="horse-history">
        <h2>過去レース成績</h2>
        {horse.pastRaces && horse.pastRaces.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>年月日</th>
                <th>場</th>
                <th>レース名</th>
                <th>距離</th>
                <th>馬場</th>
                <th>頭数</th>
                <th>人気</th>
                <th>着順</th>
                <th>騎手名</th>
                <th>負担重量</th>
                <th>馬体重</th>
                <th>タイム</th>
                <th>1着馬（2着馬）</th>
              </tr>
            </thead>
            <tbody>
              {horse.pastRaces.map((r, i) => (
                <tr key={i}>
                  <td>{r.date}</td>
                  <td>{r.venue}</td>
                  <td>{r.title}</td>
                  <td>{r.distance}</td>
                  <td>{r.track}</td>
                  <td>{r.total}</td>
                  <td>{r.popularity}</td>
                  <td>{r.rank}</td>
                  <td>{r.jockey}</td>
                  <td>{r.weight}</td>
                  <td>{r.bataiju}</td>
                  <td>{r.time}</td>
                  <td>{r.winner}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>過去レースデータなし</p>
        )}
      </div>
    </div>
  );
}
