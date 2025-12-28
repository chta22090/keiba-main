import { Link } from "react-router-dom";

// 画像を import（src/image 配下）
import marksheet from "../image/marksheet.png";
import tansyou from "../image/tansyou.png";
import hukusyou from "../image/hukusyou.png";
import ouenbaken from "../image/ouenbaken.png";
import wakuren from "../image/wakuren.png";
import umaren from "../image/umaren.png";
import umatan from "../image/umatan.png";
import waido from "../image/waido.png";
import renpuku3 from "../image/3renpuku.png";
import rentan3 from "../image/3rentan.png";

// ファイル名 → 実体の対応表
const images = {
  "marksheet.png": marksheet,
  "tansyou.png": tansyou,
  "hukusyou.png": hukusyou,
  "ouenbaken.png": ouenbaken,
  "wakuren.png": wakuren,
  "umaren.png": umaren,
  "umatan.png": umatan,
  "waido.png": waido,
  "3renpuku.png": renpuku3,
  "3rentan.png": rentan3,
};

// 画像表示用コンポーネント
const Img = ({ filename }) => (
  <div style={{ margin: "4px 0 8px" }}>
    <img
      src={images[filename]}
      alt={filename}
      style={{
        width: "100%",
        maxWidth: "420px",
        display: "block",
        borderRadius: "8px",
        border: "1px solid #e5e7eb",
      }}
    />
  </div>
);

export default function Baken() {
  return (
    <div
      style={{
        padding: "24px",
        maxWidth: "900px",
        margin: "0 auto",
        lineHeight: 1.8,
      }}
    >
      <h1>馬券の買い方</h1>

      <p>
        現地での競馬の購入方法は二種類あり、マークシート（紙）とスマッピー（スマホ）である。
        マークシートは五種類あるが、今回は一般的な緑のカードを紹介し、記入方法を馬券の種類とともに表示する。
      </p>

      <Img filename="marksheet.png" />

      <h2>・馬券の種類</h2>

      <h3>単勝</h3>
      <p>1着になる馬を当てる馬券であり、馬番号で指定します。</p>
      <p>記入例：単勝　馬番12　500円</p>
      <Img filename="tansyou.png" />

      <h3>複勝</h3>
      <p>3着までに入る馬を当てる馬券であり、馬番号で指定します。</p>
      <p>記入例：複勝　馬番12　500円</p>
      <Img filename="hukusyou.png" />

      <h3>応援馬券(単勝＋複勝)</h3>
      <p>1頭の馬の「単勝」と「複勝」を同時に購入できる馬券であり、馬番号で指定します。</p>
      <p>
        一度に同じ金額の単勝と複勝を同時に購入したことになるので、
        購入金額はマークカードに記入された金額の倍になる。
      </p>
      <p>記入例：単勝＋複勝　馬番12　500円</p>
      <Img filename="ouenbaken.png" />

      <h3>枠連</h3>
      <p>1着と2着になる馬の枠番号の組合せを当てる馬券</p>
      <p>1着と2着の着順は関係ない</p>
      <p>記入例：枠連　枠5-7　500円</p>
      <Img filename="wakuren.png" />

      <h3>馬連</h3>
      <p>1着と2着になる馬の馬番号の組合せを当てる馬券</p>
      <p>1着・2着の着順は関係ない</p>
      <p>記入例：馬連　馬番6-12　500円</p>
      <Img filename="umaren.png" />

      <h3>馬単</h3>
      <p>1着と2着になる馬の馬番号を着順通りに当てる馬券</p>
      <p>着順通りに当てないと的中にならない</p>
      <p>記入例：馬単　馬番5-3　500円</p>
      <Img filename="umatan.png" />

      <h3>ワイド</h3>
      <p>3着までに入る2頭の組合せを馬番号で当てる馬券</p>
      <p>1着・2着・3着の着順は関係ない</p>
      <p>記入例：ワイド　馬番12-3　500円</p>
      <Img filename="waido.png" />

      <h3>3連複</h3>
      <p>1着、2着、3着となる馬の組合せを馬番号で当てる馬券</p>
      <p>1着・2着・3着の着順は関係ない</p>
      <p>記入例：3連複　馬番12-3-2　500円</p>
      <Img filename="3renpuku.png" />

      <h3>3連単</h3>
      <p>1着、2着、3着となる馬の馬番号を着順通りに当てる馬券</p>
      <p>着順通りに当てないと的中にならない</p>
      <p>記入例：3連単　馬番8-4-2　500円</p>
      <Img filename="3rentan.png" />

      <h2>・スマッピー</h2>
      <p>スマホで馬券を購入できる。マークシート形式ではないので購入しやすい。</p>
      <p>
        <a
          href="http://qrcode.jra.go.jp/"
          target="_blank"
          rel="noopener noreferrer"
        >
          http://qrcode.jra.go.jp/
        </a>
      </p>

      <div style={{ marginTop: "32px" }}>
        <Link to="/" className="nav-button">
          トップページへ戻る
        </Link>
      </div>
    </div>
  );
}
