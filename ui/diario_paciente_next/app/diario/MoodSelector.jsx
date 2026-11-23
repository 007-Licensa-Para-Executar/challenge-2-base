"use client";

import { useState } from "react";
import { EMOTIONS_DIVERTIDAMENTE } from "../lib/emotionTaxonomy";

export default function MoodSelector({ selectedEmotion, selectedSub, onSelect }) {
  const [expandedEmotion, setExpandedEmotion] = useState(null);

  const mainEmotions = [
    EMOTIONS_DIVERTIDAMENTE.alegria,
    EMOTIONS_DIVERTIDAMENTE.tristeza,
    EMOTIONS_DIVERTIDAMENTE.medo,
    EMOTIONS_DIVERTIDAMENTE.raiva,
    EMOTIONS_DIVERTIDAMENTE.nojinho,
    EMOTIONS_DIVERTIDAMENTE.neutro,
  ];

  function handleEmotionClick(emotion) {
    if (expandedEmotion === emotion.id) {
      setExpandedEmotion(null);
    } else {
      setExpandedEmotion(emotion.id);
      // Seleciona o primeiro sub-sentimento por padrão
      onSelect({
        character: emotion.personagem,
        primary_emotion: emotion.id,
        color_hex: emotion.corHex,
        color_secondary_hex: emotion.corSecundariaHex,
        sub_emotion_name: emotion.subSentimentos[0].nome,
        sub_emotion_symbol: emotion.subSentimentos[0].simbolo,
        confidence: 1.0,
        is_risk_emotion: emotion.isRiskEmotion,
      });
    }
  }

  function handleSubClick(emotion, sub) {
    onSelect({
      character: emotion.personagem,
      primary_emotion: emotion.id,
      color_hex: emotion.corHex,
      color_secondary_hex: emotion.corSecundariaHex,
      sub_emotion_name: sub.nome,
      sub_emotion_symbol: sub.simbolo,
      confidence: 1.0,
      is_risk_emotion: emotion.isRiskEmotion,
    });
  }

  return (
    <div className="mood-selector-container">
      <div className="mood-pills-row">
        {mainEmotions.map((emo) => {
          const isSelected = selectedEmotion === emo.id;
          return (
            <button
              key={emo.id}
              type="button"
              className={`mood-pill ${isSelected ? "active" : ""}`}
              style={{
                borderColor: emo.corHex,
                backgroundColor: isSelected ? emo.corSecundariaHex : "#FFFFFF",
                color: isSelected ? emo.corTexto : "var(--cor-texto)",
              }}
              onClick={() => handleEmotionClick(emo)}
            >
              <span
                className="mood-pill-dot"
                style={{ backgroundColor: emo.corHex }}
                aria-hidden="true"
              />
              <span className="mood-pill-name">{emo.personagem}</span>
            </button>
          );
        })}
      </div>

      {expandedEmotion && (
        <div className="sub-emotions-panel">
          <p className="sub-panel-title">
            Nuances de {EMOTIONS_DIVERTIDAMENTE[expandedEmotion]?.personagem} (How We Feel):
          </p>
          <div className="sub-pills-grid">
            {EMOTIONS_DIVERTIDAMENTE[expandedEmotion]?.subSentimentos.map((sub) => {
              const isSubSelected = selectedSub === sub.nome;
              const emo = EMOTIONS_DIVERTIDAMENTE[expandedEmotion];
              return (
                <button
                  key={sub.id}
                  type="button"
                  className={`sub-pill ${isSubSelected ? "active" : ""}`}
                  style={{
                    borderColor: isSubSelected ? emo.corHex : "var(--cor-borda)",
                    backgroundColor: isSubSelected ? emo.corSecundariaHex : "#FFFFFF",
                  }}
                  onClick={() => handleSubClick(emo, sub)}
                >
                  <span className="sub-symbol">{sub.simbolo}</span>
                  <div className="sub-texts">
                    <strong>{sub.nome}</strong>
                    <span>{sub.descricao}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
