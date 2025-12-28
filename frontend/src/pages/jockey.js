import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./jockey.css";

export default function Jockey() {
  const { jockeyName } = useParams();
  const [jockey, setJockey] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/server/JockeyTest.json");
        const json = await res.json();
        const decodedName = decodeURIComponent(jockeyName);
        const data = (json.jockeys || []).find((j) => j.name === decodedName);
        setJockey(data || null);
      } catch (err) {
        console.error(err);
        setJockey(null);
      }
    }
    load();
  }, [jockeyName]);

  if (!jockey) {
    return (
      <div className="jockey-container">
        <button onClick={() => navigate(-1)}>↩ 戻る</button>
        <h1>騎手データなし</h1>
        <p>データが存在しないか、読み込み中です。</p>
      </div>
    );
  }

  const hasCurrent = jockey.stats_current && Array.isArray(jockey.stats_current.rows);
  const hasTotal = jockey.stats_total && Array.isArray(jockey.stats_total.rows);

  return (
    <div className="jockey-container">
      <button onClick={() => navigate(-1)}>↩ 戻る</button>
      <h1>{jockey.name}</h1>

      <table>
        <tbody>
          <tr><td>生年月日</td><td>{jockey.birthday || "―"}</td></tr>
          <tr><td>身長</td><td>{jockey.height || "―"}</td></tr>
          <tr><td>体重</td><td>{jockey.weight || "―"}</td></tr>
          <tr><td>初免許年</td><td>{jockey.first_license || "―"}</td></tr>
        </tbody>
      </table>

      <div className="jockey-history">
        <h2>本年成績</h2>
        {hasCurrent ? (
          <table>
            <thead>
              {(jockey.stats_current.headers || []).length ? (
                <tr>
                  {jockey.stats_current.headers.map((h, i) => (
                    <th key={i}>{h}</th>
                  ))}
                </tr>
              ) : null}
            </thead>
            <tbody>
              {jockey.stats_current.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((c, j) => (
                    <td key={j}>{c}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>データなし</p>
        )}
      </div>

      <div className="jockey-history">
        <h2>累計成績</h2>
        {hasTotal ? (
          <table>
            <thead>
              {(jockey.stats_total.headers || []).length ? (
                <tr>
                  {jockey.stats_total.headers.map((h, i) => (
                    <th key={i}>{h}</th>
                  ))}
                </tr>
              ) : null}
            </thead>
            <tbody>
              {jockey.stats_total.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((c, j) => (
                    <td key={j}>{c}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>データなし</p>
        )}
      </div>
    </div>
  );
}
