import { Headphones, ShieldAlert } from "lucide-react";
import { getEmotionProfile, getSubEmotionProfile } from "../lib/emotionTaxonomy";
import EmotionSymbol from "./EmotionSymbol";
import styles from "./diary.module.css";

export default function DiaryEntryCard({ entry }) {
  const profile = getEmotionProfile(entry.primary_emotion);
  const sub = getSubEmotionProfile(profile.id, entry.sub_emotion_name);
  const feeling = entry.sub_emotion_name || sub?.nome || profile.personagem;
  const accent = entry.color_hex || sub?.corHex || profile.corHex;
  const soft = sub?.corSecundariaHex || profile.corSecundariaHex;
  const dataFormatada = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(entry.created_at));

  return (
    <article
      className={styles.entryCard}
      style={{ "--emotion-color": accent, "--emotion-soft": soft }}
    >
      <header className={styles.entryHeader}>
        <div className={styles.entryFeeling}>
          <span className={styles.entrySymbol}>
            <EmotionSymbol emotion={profile.id} subEmotion={feeling} size={25} />
          </span>
          <span className={styles.entryFeelingCopy}>
            <span>Você se sentiu</span>
            <strong>{feeling}</strong>
            <small>{profile.personagem}</small>
          </span>
        </div>
        <time className={styles.entryTime} dateTime={new Date(entry.created_at).toISOString()}>
          {dataFormatada}
        </time>
      </header>

      <p className={styles.entryText}>{entry.text}</p>

      {(entry.audio_data || entry.input_type === "audio") && (
        <div className={styles.audioCard}>
          <div className={styles.audioHeading}>
            <Headphones size={16} aria-hidden="true" />
            <span>{entry.audio_name || "Áudio do relato"}</span>
            {entry.audio_duration && <small>{entry.audio_duration}</small>}
          </div>
          {entry.audio_data && (
            <audio controls src={entry.audio_data} className={styles.audioPlayer} />
          )}
        </div>
      )}

      {Boolean(entry.is_risk_emotion) && (
        <div className={styles.supportNote} role="note">
          <ShieldAlert size={17} aria-hidden="true" />
          <span>Um momento delicado também merece acolhimento. Sua equipe de cuidado está aqui para apoiar você.</span>
        </div>
      )}
    </article>
  );
}
