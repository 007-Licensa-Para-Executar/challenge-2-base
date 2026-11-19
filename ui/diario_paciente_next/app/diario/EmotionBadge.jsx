import { getEmotionProfile } from "../lib/emotionTaxonomy";

export default function EmotionBadge({ emotion, subEmotion, symbol, showRisk = true }) {
  const profile = getEmotionProfile(emotion);
  const displaySymbol = symbol || profile.subSentimentos[0]?.simbolo || "⚖️";
  const displaySub = subEmotion || profile.subSentimentos[0]?.nome || profile.personagem;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 10px",
        borderRadius: "999px",
        background: profile.corSecundariaHex,
        border: `1px solid ${profile.corHex}`,
        color: profile.corTexto,
        fontSize: "13px",
        fontWeight: "600",
      }}
    >
      <span style={{ fontSize: "15px" }}>{displaySymbol}</span>
      <span>{profile.personagem}</span>
      <span style={{ opacity: 0.6 }}>•</span>
      <span style={{ fontWeight: "500" }}>{displaySub}</span>
      {showRisk && profile.isRiskEmotion && (
        <span
          title="Emoção com indicador de cuidado clínico"
          style={{
            marginLeft: "2px",
            background: "#8C3A32",
            color: "#FFF",
            fontSize: "10px",
            padding: "1px 5px",
            borderRadius: "4px",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          Acolhimento
        </span>
      )}
    </div>
  );
}
