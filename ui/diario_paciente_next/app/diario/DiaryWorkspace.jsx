"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  LogOut,
  Send,
  Sprout,
} from "lucide-react";
import VoiceMicButton from "./VoiceMicButton";
import PatientSelfProfileEditor from "./PatientSelfProfileEditor";
import {
  EMOTIONS_DIVERTIDAMENTE,
  getEmotionProfile,
  getSubEmotionProfile,
} from "../lib/emotionTaxonomy";
import styles from "./diary.module.css";

const EMOTION_SPRITES = {
  alegria: 0,
  tristeza: 1,
  medo: 2,
  raiva: 3,
  nojinho: 4,
  neutro: 5,
  surpresa: 6,
  gratidao: 7,
};

function emotionSprite(emotionId, subEmotionId) {
  const index = EMOTION_SPRITES[subEmotionId] ?? EMOTION_SPRITES[emotionId] ?? EMOTION_SPRITES.neutro;
  return { spriteColumn: index % 4, spriteRow: Math.floor(index / 4) };
}

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function groupDominantEmotions(entries) {
  const days = new Map();

  entries.forEach((entry) => {
    const date = new Date(Number(entry.created_at));
    if (!Number.isFinite(date.getTime())) return;

    const profile = getEmotionProfile(entry.primary_emotion);
    const sub = getSubEmotionProfile(profile.id, entry.sub_emotion_name);
    const emotionKey = sub?.id || profile.id;
    const key = dateKey(date);
    const candidates = days.get(key) || new Map();
    const candidate = candidates.get(emotionKey) || {
      label: sub?.nome || profile.personagem,
      ...emotionSprite(profile.id, sub?.id),
      color: sub?.corHex || entry.color_hex || profile.corHex,
      softColor: sub?.corSecundariaHex || entry.color_secondary_hex || profile.corSecundariaHex,
      count: 0,
      confidenceTotal: 0,
      latestAt: 0,
    };

    candidate.count += 1;
    candidate.confidenceTotal += Number(entry.confidence) || 0;
    candidate.latestAt = Math.max(candidate.latestAt, date.getTime());
    candidates.set(emotionKey, candidate);
    days.set(key, candidates);
  });

  return new Map(Array.from(days, ([key, candidates]) => {
    const dominant = Array.from(candidates.values()).sort((a, b) =>
      b.count - a.count ||
      (b.confidenceTotal / b.count) - (a.confidenceTotal / a.count) ||
      b.latestAt - a.latestAt,
    )[0];

    return [key, {
      ...dominant,
      totalEntries: Array.from(candidates.values()).reduce((sum, item) => sum + item.count, 0),
    }];
  }));
}

function createCalendarPreview(year, month) {
  const options = Object.values(EMOTIONS_DIVERTIDAMENTE).flatMap((profile) =>
    profile.subSentimentos.map((sub) => {
      const detail = getSubEmotionProfile(profile.id, sub.id);
      return {
        label: detail.nome,
        ...emotionSprite(profile.id, sub.id),
        color: detail.corHex,
        softColor: detail.corSecundariaHex,
        isPreview: true,
      };
    }),
  );
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  return new Map(Array.from({ length: daysInMonth }, (_, index) => {
    const date = new Date(year, month, index + 1);
    return [dateKey(date), options[index % options.length]];
  }));
}

export default function DiaryWorkspace({ initialPaciente, initialRelatos }) {
  const [paciente, setPaciente] = useState(initialPaciente);
  const [relatos, setRelatos] = useState(initialRelatos || []);
  const [texto, setTexto] = useState("");
  const [transcricao, setTranscricao] = useState("");
  const [monthOffset, setMonthOffset] = useState(0);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [showCalendarPreview, setShowCalendarPreview] = useState(process.env.NODE_ENV !== "production");
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState(null);
  const [audioAttachment, setAudioAttachment] = useState(null);
  const [audioBusy, setAudioBusy] = useState(false);

  async function handleSalvar(event) {
    event.preventDefault();
    const cleanText = [texto.trim(), transcricao.trim()].filter(Boolean).join("\n\n");
    if (!cleanText) {
      setAviso({ tipo: "erro", texto: "Escreva algo no seu relato antes de salvar." });
      return;
    }
    if (audioBusy || (audioAttachment && !transcricao.trim())) {
      setAviso({ tipo: "erro", texto: "Aguarde a transcrição ou refaça o áudio antes de salvar." });
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
          inputType: audioAttachment ? "audio" : "text",
          audioName: audioAttachment?.audioName || null,
          audioDuration: audioAttachment?.audioDuration || null,
          audioData: audioAttachment?.audioData || null,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setAviso({ tipo: "erro", texto: data.message || "Não foi possível classificar e salvar o relato." });
        return;
      }

      setRelatos((previous) => [data.entry, ...previous]);
      setTexto("");
      setTranscricao("");
      setAudioAttachment(null);
      setAviso(data.entry?.classification_warning
        ? { tipo: "aviso", texto: "Relato salvo. " + data.entry.classification_warning }
        : { tipo: "sucesso", texto: "Relato salvo. Tema, sentimento e emoção estimados automaticamente." });
    } catch {
      setAviso({ tipo: "erro", texto: "Não foi possível conectar ao servidor. Tente novamente." });
    } finally {
      setSalvando(false);
    }
  }

  const now = new Date();
  const monthDate = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  const monthYear = monthDate.getFullYear();
  const monthIndex = monthDate.getMonth();
  const firstWeekday = new Date(monthYear, monthIndex, 1).getDay();
  const daysInMonth = new Date(monthYear, monthIndex + 1, 0).getDate();
  const calendarCellCount = Math.ceil((firstWeekday + daysInMonth) / 7) * 7;
  const dominantByDay = groupDominantEmotions(relatos);
  const previewByDay = showCalendarPreview ? createCalendarPreview(monthYear, monthIndex) : new Map();
  const calendarDays = Array.from({ length: calendarCellCount }, (_, index) => {
    const date = new Date(monthYear, monthIndex, index - firstWeekday + 1);
    const isCurrentMonth = date.getMonth() === monthIndex;
    return {
      date,
      isCurrentMonth,
      emotion: isCurrentMonth
        ? dominantByDay.get(dateKey(date)) || previewByDay.get(dateKey(date)) || null
        : null,
    };
  });
  const recordedDays = calendarDays.filter((day) =>
    day.isCurrentMonth && dominantByDay.has(dateKey(day.date)),
  ).length;
  const monthLabel = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(monthDate);
  const todayKey = dateKey(now);
  const weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

  return (
    <div className={styles.appShell}>
      <header className={styles.topBar}>
        <div className={styles.topContent}>
          <a className={styles.brand} href="/" aria-label="Meu Diário, início">
            <span className={styles.brandMark}><Sprout size={20} aria-hidden="true" /></span>
            <span>meu diário</span>
          </a>
          <div className={styles.userActions}>
            <PatientSelfProfileEditor
              patient={paciente}
              onSave={(profile) => setPaciente((current) => ({ ...current, ...profile }))}
            />
            <button
              type="button"
              className={styles.logoutButton}
              onClick={async () => {
                try {
                  await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
                } catch {}
                window.location.href = "/";
              }}
            >
              <LogOut size={16} aria-hidden="true" />
              <span>Sair</span>
            </button>
          </div>
        </div>
      </header>

      <main className={styles.mainContainer}>
        <section className={styles.hero}>
          <div>
            <p className={styles.eyebrow}>SEU ESPAÇO DE CUIDADO</p>
            <h1>Como foi o seu dia?</h1>
            <p className={styles.heroDescription}>
              Escreva ou dite o que está passando por você. O diário identifica as emoções automaticamente.
            </p>
          </div>
        </section>

        <div className={[styles.flowGrid, calendarOpen && styles.flowGridExpanded].filter(Boolean).join(" ")}>
          <section className={styles.card} aria-labelledby="entry-title">
            <div className={styles.sectionHeader}>
              <span className={styles.stepNumber}>01</span>
              <div>
                <h2 id="entry-title">Escreva seu relato</h2>
                <p>A classificação acontece automaticamente ao salvar; não é preciso escolher uma emoção.</p>
              </div>
            </div>

            <form onSubmit={handleSalvar} className={styles.editorForm}>
              <div className={styles.textareaShell}>
                <label className={styles.visuallyHidden} htmlFor="diario-texto">Seu relato</label>
                <textarea
                  id="diario-texto"
                  className={styles.diaryTextarea}
                  rows={7}
                  placeholder="O que aconteceu hoje? Como isso fez você se sentir?"
                  value={texto}
                  onChange={(event) => setTexto(event.target.value)}
                  maxLength={Math.max(0, 20000 - transcricao.length)}
                />
              </div>
              <VoiceMicButton
                onTranscript={setTranscricao}
                transcript={transcricao}
                onTranscriptChange={setTranscricao}
                maxTranscriptLength={Math.max(0, 20000 - texto.length)}
                onAudioReady={setAudioAttachment}
                audioAttachment={audioAttachment}
                onDiscardAudio={() => {
                  setAudioAttachment(null);
                  setTranscricao("");
                }}
                onBusyChange={setAudioBusy}
              />

              <div className={styles.editorMeta}>
                <span>{(texto.length + transcricao.length).toLocaleString("pt-BR")} / 20.000 caracteres</span>
                {salvando && (
                  <span className={styles.analyzingStatus} role="status">
                    <LoaderCircle size={14} className={styles.spinner} aria-hidden="true" />
                    Classificando com a rede neural e o Ollama…
                  </span>
                )}
              </div>

              {aviso && (
                <div
                  className={
                    aviso.tipo === "sucesso"
                      ? styles.feedbackSuccess
                      : aviso.tipo === "aviso"
                        ? styles.feedbackWarning
                        : styles.feedbackError
                  }
                  role={aviso.tipo === "erro" ? "alert" : "status"}
                >
                  {aviso.texto}
                </div>
              )}

              <div className={styles.editorActions}>
                <span className={styles.privateNote}>Seu diário é um espaço pessoal e protegido.</span>
                <button
                  type="submit"
                  className={styles.submitButton}
                  disabled={salvando || audioBusy || (!texto.trim() && !transcricao.trim()) || (Boolean(audioAttachment) && !transcricao.trim())}
                >
                  {salvando ? <LoaderCircle size={17} className={styles.spinner} aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
                  {salvando ? "Classificando…" : "Salvar relato"}
                </button>
              </div>
            </form>
          </section>

          <section className={[styles.card, styles.calendarCard].join(" ")} aria-labelledby="calendar-title">
            <div className={styles.calendarHeading}>
              <div className={styles.sectionHeader}>
                <span className={styles.stepNumber}>02</span>
                <div>
                  <h2 id="calendar-title">
                    <button
                      type="button"
                      className={styles.calendarTitleToggle}
                      aria-expanded={calendarOpen}
                      aria-controls="diary-calendar-panel"
                      onClick={() => setCalendarOpen((open) => !open)}
                    >
                      Seu mês
                      <ChevronDown
                        size={17}
                        className={styles.calendarToggleIcon}
                        aria-hidden="true"
                      />
                    </button>
                  </h2>
                  <p>Um símbolo mostra a emoção predominante de cada dia.</p>
                </div>
              </div>
              <div className={styles.calendarActions}>
                <span className={styles.entryCount}>{recordedDays} {recordedDays === 1 ? "dia" : "dias"} com relatos</span>
              </div>
            </div>

            <div id="diary-calendar-panel" className={styles.calendarContent} hidden={!calendarOpen}>
              <div className={styles.calendarToolbar}>
                <button
                  type="button"
                  className={styles.monthNavButton}
                  aria-label="Mês anterior"
                  onClick={() => setMonthOffset((offset) => offset - 1)}
                >
                  <ChevronLeft size={18} aria-hidden="true" />
                </button>
                <h3 className={styles.monthLabel}>{monthLabel}</h3>
                <button
                  type="button"
                  className={styles.monthNavButton}
                  aria-label="Próximo mês"
                  onClick={() => setMonthOffset((offset) => Math.min(offset + 1, 0))}
                  disabled={monthOffset === 0}
                >
                  <ChevronRight size={18} aria-hidden="true" />
                </button>
              </div>

              {process.env.NODE_ENV !== "production" && (
                <div className={styles.calendarPreviewRow}>
                  <button
                    type="button"
                    className={styles.calendarPreviewToggle}
                    aria-pressed={showCalendarPreview}
                    onClick={() => setShowCalendarPreview((visible) => !visible)}
                  >
                    {showCalendarPreview ? "Ocultar exemplos" : "Preencher mês"}
                  </button>
                </div>
              )}

              <div className={styles.calendarGrid} role="group" aria-label={`Calendário de emoções de ${monthLabel}`}>
                {weekdays.map((day) => (
                  <span key={day} className={styles.calendarWeekday} aria-hidden="true">{day}</span>
                ))}
                {calendarDays.map(({ date, isCurrentMonth, emotion }) => {
                  const key = dateKey(date);
                  const isToday = key === todayKey;
                  const label = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long" }).format(date);
                  const ariaLabel = emotion
                    ? emotion.isPreview
                      ? `${label}: exemplo de ${emotion.label}`
                      : `${label}: ${emotion.label}, ${emotion.totalEntries} ${emotion.totalEntries === 1 ? "relato" : "relatos"}`
                    : `${label}: sem relatos`;

                  return (
                    <div
                      key={key}
                      className={[
                        styles.calendarDay,
                        !isCurrentMonth && styles.calendarDayOutside,
                        isToday && styles.calendarDayToday,
                        emotion && styles.calendarDayRecorded,
                      ].filter(Boolean).join(" ")}
                      style={emotion ? { "--emotion-color": emotion.color, "--emotion-soft": emotion.softColor } : undefined}
                      role="group"
                      aria-label={ariaLabel}
                      title={emotion
                        ? emotion.isPreview
                          ? `Exemplo visual: ${emotion.label}`
                          : `${emotion.label} · ${emotion.totalEntries} ${emotion.totalEntries === 1 ? "relato" : "relatos"}`
                        : undefined}
                    >
                      <span className={styles.calendarDayNumber}>{date.getDate()}</span>
                      {emotion && (
                        <span
                          className={styles.calendarDaySprite}
                          style={{
                            "--sprite-column": `${(emotion.spriteColumn / 3) * 100}%`,
                            "--sprite-row": `${emotion.spriteRow * 100}%`,
                          }}
                          aria-hidden="true"
                        />
                      )}
                    </div>
                  );
                })}
              </div>

              <p className={styles.calendarLegend}>
                {showCalendarPreview
                  ? "Prévia visual: dias sem registro exibem exemplos; eles não são salvos no diário."
                  : relatos.length
                    ? "Os símbolos ajudam a perceber como suas emoções variam ao longo do tempo."
                    : "Os símbolos dos seus relatos aparecerão aqui quando você salvar o primeiro."}
              </p>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
