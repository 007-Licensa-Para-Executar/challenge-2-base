"use client";

import { useEffect, useState } from "react";
import DiaryEntryCard from "./DiaryEntryCard";
import EmotionBadge from "./EmotionBadge";
import MoodSelector from "./MoodSelector";
import { EMOTIONS_DIVERTIDAMENTE, getEmotionProfile } from "../lib/emotionTaxonomy";

export default function DiaryWorkspace({ initialPaciente, initialRelatos }) {
  const [paciente] = useState(initialPaciente);
  const [relatos, setRelatos] = useState(initialRelatos || []);
  const [texto, setTexto] = useState("");
  const [filtroEmocao, setFiltroEmocao] = useState("todas");
  const [analisando, setAnalisando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState(null);

  // Emoção selecionada manualmente ou inferida pela rede neural
  const [emocaoAtual, setEmocaoAtual] = useState(null);

  // Analisa o sentimento automaticamente com debounce quando o paciente digita
  useEffect(() => {
    const trimmed = texto.trim();
    if (trimmed.length < 15) {
      if (emocaoAtual && !emocaoAtual.manual) {
        setEmocaoAtual(null);
      }
      return;
    }

    const timer = setTimeout(async () => {
      setAnalisando(true);
      try {
        const res = await fetch("/api/diario/analisar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: trimmed }),
        });
        if (res.ok) {
          const dados = await res.json();
          setEmocaoAtual({ ...dados, manual: false });
        }
      } catch {
        // Silêncio em caso de falha de conexão na digitação
      } finally {
        setAnalisando(false);
      }
    }, 800);

    return () => clearTimeout(timer);
  }, [texto]);

  async function handleSalvar(e) {
    e.preventDefault();
    const cleanText = texto.trim();
    if (!cleanText) {
      setAviso({ tipo: "erro", texto: "Por favor, escreva algo no seu relato antes de salvar." });
      return;
    }

    setSalvando(true);
    setAviso(null);

    try {
      const res = await fetch("/api/diario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: cleanText,
          emotion: emocaoAtual,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setAviso({ tipo: "erro", texto: data.message || "Erro ao salvar o relato." });
        return;
      }

      // Adiciona o novo relato no topo da lista
      setRelatos((prev) => [data.entry, ...prev]);
      setTexto("");
      setEmocaoAtual(null);
      setAviso({ tipo: "sucesso", texto: "Relato registrado com sucesso no seu diário." });
    } catch {
      setAviso({ tipo: "erro", texto: "Não foi possível conectar ao servidor. Tente novamente." });
    } finally {
      setSalvando(false);
    }
  }

  function handleSelectMood(moodData) {
    setEmocaoAtual({ ...moodData, manual: true });
  }

  const relatosFiltrados = relatos.filter((r) => {
    if (filtroEmocao === "todas") return true;
    return (r.primary_emotion || "").toLowerCase() === filtroEmocao;
  });

  return (
    <div className="diary-app-shell">
      {/* Barra superior de navegação */}
      <header className="diary-top-bar">
        <div className="diary-top-content">
          <div className="diary-brand">
            <span className="brand-dot" aria-hidden="true" />
            <span className="brand-title">meu diário</span>
          </div>
          <div className="diary-user-info">
            <span>Olá, <strong>{paciente?.name || "Paciente"}</strong></span>
            <button
              type="button"
              className="logout-button"
              onClick={() => {
                document.cookie = "diario_sessao=; Path=/; Max-Age=0";
                window.location.href = "/";
              }}
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="diary-main-container">
        {/* Painel 1: Check-in visual Divertidamente */}
        <section className="diary-card-section">
          <div className="section-header">
            <h2>Como você está se sentindo hoje?</h2>
            <p>Selecione um sentimento no espectro Divertidamente ou deixe a rede neural detectar pelo seu texto.</p>
          </div>
          <MoodSelector
            selectedEmotion={emocaoAtual?.primary_emotion}
            selectedSub={emocaoAtual?.sub_emotion_name}
            onSelect={handleSelectMood}
          />
        </section>

        {/* Painel 2: Redação do relato */}
        <section className="diary-card-section">
          <form onSubmit={handleSalvar} className="diary-editor-form">
            <label htmlFor="diario-texto" className="editor-label">
              Escreva seu relato
            </label>
            <textarea
              id="diario-texto"
              className="diary-textarea"
              rows={6}
              placeholder="Desabafe, conte como foi seu dia, suas sensações ou pensamentos..."
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              maxLength={20000}
            />

            <div className="editor-meta-row">
              <span className="char-count">{texto.length} / 20.000 caracteres</span>
              {analisando && (
                <span className="analyzing-pill">
                  <span className="spinner-dot" /> Analisando emoção com Rede Neural...
                </span>
              )}
            </div>

            {/* Visualização em tempo real do sentimento detectado pela Rede Neural */}
            {emocaoAtual && (
              <div
                className="emotion-preview-box"
                style={{
                  backgroundColor: emocaoAtual.color_secondary_hex || "#F5F5F5",
                  borderColor: emocaoAtual.color_hex || "#DDD",
                }}
              >
                <div className="preview-header">
                  <span className="preview-label">
                    {emocaoAtual.manual ? "Sentimento Escolhido:" : "Sentimento Detectado pela Rede Neural:"}
                  </span>
                  {emocaoAtual.confidence && !emocaoAtual.manual && (
                    <span className="confidence-pill">
                      Confiança: {Math.round(emocaoAtual.confidence * 100)}%
                    </span>
                  )}
                </div>

                <div className="preview-body">
                  <EmotionBadge
                    emotion={emocaoAtual.primary_emotion}
                    subEmotion={emocaoAtual.sub_emotion_name}
                    symbol={emocaoAtual.sub_emotion_symbol}
                    showRisk={emocaoAtual.is_risk_emotion}
                  />
                  <p className="preview-description">
                    {getEmotionProfile(emocaoAtual.primary_emotion)?.descricao}
                  </p>
                </div>
              </div>
            )}

            {aviso && (
              <div className={`form-feedback ${aviso.tipo}`} role="alert">
                {aviso.texto}
              </div>
            )}

            <div className="editor-actions">
              <button
                type="submit"
                className="submit-button"
                disabled={salvando || !texto.trim()}
              >
                {salvando ? "Salvando relato..." : "Salvar relato no meu diário"}
              </button>
            </div>
          </form>
        </section>

        {/* Painel 3: Histórico e Linha do Tempo */}
        <section className="diary-card-section">
          <div className="section-header timeline-header">
            <h2>Seu Histórico de Cuidados</h2>
            <div className="filter-chips-row">
              <button
                type="button"
                className={`filter-chip ${filtroEmocao === "todas" ? "active" : ""}`}
                onClick={() => setFiltroEmocao("todas")}
              >
                Todas ({relatos.length})
              </button>
              {Object.values(EMOTIONS_DIVERTIDAMENTE).map((emo) => {
                const count = relatos.filter((r) => r.primary_emotion === emo.id).length;
                if (count === 0) return null;
                return (
                  <button
                    key={emo.id}
                    type="button"
                    className={`filter-chip ${filtroEmocao === emo.id ? "active" : ""}`}
                    onClick={() => setFiltroEmocao(emo.id)}
                    style={{
                      borderColor: emo.corHex,
                      color: filtroEmocao === emo.id ? "#FFF" : emo.corTexto,
                      backgroundColor: filtroEmocao === emo.id ? emo.corHex : emo.corSecundariaHex,
                    }}
                  >
                    {emo.personagem} ({count})
                  </button>
                );
              })}
            </div>
          </div>

          <div className="timeline-entries-list">
            {relatosFiltrados.length === 0 ? (
              <div className="empty-state">
                <p>Nenhum relato encontrado para este filtro.</p>
              </div>
            ) : (
              relatosFiltrados.map((item) => (
                <DiaryEntryCard key={item.id} entry={item} />
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
