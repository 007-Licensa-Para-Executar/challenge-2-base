import EmotionBadge from "./EmotionBadge";

export default function DiaryEntryCard({ entry }) {
  const dataFormatada = new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(entry.created_at));

  const corAcento = entry.color_hex || "#9E9E9E";

  return (
    <article
      style={{
        position: "relative",
        background: "#FFFFFF",
        borderRadius: "18px",
        border: "1px solid rgba(220, 229, 223, 0.9)",
        boxShadow: "0 4px 16px rgba(38, 51, 47, 0.04)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        transition: "transform 150ms ease, box-shadow 150ms ease",
      }}
    >
      {/* Barra lateral temática Divertidamente */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          bottom: 0,
          width: "6px",
          backgroundColor: corAcento,
        }}
        aria-hidden="true"
      />

      <div style={{ padding: "18px 20px 18px 26px" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px",
            marginBottom: "12px",
          }}
        >
          <EmotionBadge
            emotion={entry.primary_emotion}
            subEmotion={entry.sub_emotion_name}
            symbol={entry.sub_emotion_symbol}
            showRisk={Boolean(entry.is_risk_emotion)}
          />
          <time
            style={{
              fontSize: "13px",
              color: "var(--cor-texto-suave)",
              fontWeight: "500",
            }}
          >
            {dataFormatada}
          </time>
        </header>

        <p
          style={{
            margin: "0 0 8px",
            fontSize: "15px",
            lineHeight: "1.6",
            color: "var(--cor-texto)",
            whiteSpace: "pre-wrap",
          }}
        >
          {entry.text}
        </p>

        {/* Reprodutor de áudio anexado ao relato */}
        {(entry.audio_data || entry.input_type === "audio") && (
          <div
            style={{
              marginTop: "12px",
              padding: "10px 14px",
              borderRadius: "12px",
              background: "#F2F5F3",
              border: "1px solid rgba(132, 145, 136, 0.2)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "12px",
                color: "var(--cor-texto-suave)",
                fontWeight: "600",
              }}
            >
              <span>🎙️ Áudio do Relato {entry.audio_name ? `• ${entry.audio_name}` : ""}</span>
              {entry.audio_duration && <span>{entry.audio_duration}</span>}
            </div>
            {entry.audio_data && (
              <audio
                controls
                src={entry.audio_data}
                style={{ width: "100%", height: "36px" }}
              />
            )}
          </div>
        )}

        {Boolean(entry.is_risk_emotion) && (
          <div
            style={{
              marginTop: "12px",
              padding: "10px 14px",
              borderRadius: "10px",
              background: "#F6E8E6",
              border: "1px solid rgba(140, 58, 50, 0.2)",
              color: "#8C3A32",
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span style={{ fontSize: "16px" }}>💙</span>
            <span>
              Identificamos um momento delicado no seu relato. Lembre-se de que você tem apoio da sua equipe de saúde.
            </span>
          </div>
        )}
      </div>
    </article>
  );
}
