"use client";

import { useEffect, useRef, useState } from "react";
import { AudioLines, LoaderCircle, Mic, X } from "lucide-react";

const MIME_EXTENSIONS = {
  "audio/webm": "webm",
  "audio/ogg": "ogg",
  "audio/mp4": "mp4",
  "audio/wav": "wav",
};

function formatClock(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const secs = (totalSeconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

function readAudioAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Não foi possível preparar o áudio gravado."));
    reader.readAsDataURL(blob);
  });
}

export default function VoiceMicButton({
  onTranscript,
  transcript = "",
  onTranscriptChange,
  maxTranscriptLength = 20000,
  onAudioReady,
  audioAttachment = null,
  onDiscardAudio,
  onBusyChange,
}) {
  const [recording, setRecording] = useState(false);
  const [starting, setStarting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const [errorNotice, setErrorNotice] = useState("");
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const elapsedRef = useRef(0);
  const maxTranscriptLengthRef = useRef(maxTranscriptLength);
  maxTranscriptLengthRef.current = maxTranscriptLength;

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.onstop = null;
      try {
        mediaRecorderRef.current.stop();
      } catch {}
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  async function handleRecordedAudio(recorder) {
    const mimeType = recorder.mimeType || "audio/webm";
    const audioBlob = new Blob(chunksRef.current, { type: mimeType });
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;

    if (!audioBlob.size) {
      onBusyChange?.(false);
      setErrorNotice("A gravação ficou vazia. Verifique o microfone e tente novamente.");
      return;
    }

    const baseMimeType = mimeType.split(";")[0].toLowerCase();
    const extension = MIME_EXTENSIONS[baseMimeType] || "webm";
    const fileName = `relato-${new Date().toISOString().replace(/[:.]/g, "-")}.${extension}`;

    setTranscribing(true);
    setErrorNotice("");
    try {
      const audioData = await readAudioAsDataUrl(audioBlob);
      onAudioReady({
        audioData,
        audioName: fileName,
        audioDuration: formatClock(elapsedRef.current),
        inputType: "audio",
      });
    } catch (error) {
      setErrorNotice(error.message);
    }

    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, fileName);
      const response = await fetch("/api/diario/transcrever", {
        method: "POST",
        body: formData,
      });
      const result = await response.json().catch(() => ({}));
      const transcript = String(result.text || "").trim();
      if (!response.ok || !transcript) {
        throw new Error(result.message || "Não foi possível transcrever o áudio. Tente novamente.");
      }

      onTranscript(transcript.slice(0, maxTranscriptLengthRef.current));
      setErrorNotice("");
    } catch (error) {
      setErrorNotice(error.message || "Não foi possível transcrever o áudio. Tente novamente.");
    } finally {
      setTranscribing(false);
      onBusyChange?.(false);
    }
  }

  async function handleStart() {
    if (starting || recording || transcribing) return;
    setErrorNotice("");
    setStarting(true);
    onBusyChange?.(true);
    setElapsed(0);
    elapsedRef.current = 0;
    chunksRef.current = [];

    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStarting(false);
      onBusyChange?.(false);
      setErrorNotice("Este navegador não permite gravar áudio. Use um navegador atualizado e seguro.");
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
        "audio/ogg",
      ].find((type) => MediaRecorder.isTypeSupported?.(type));
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data?.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => { void handleRecordedAudio(recorder); };
      recorder.start(250);
      setRecording(true);
      setStarting(false);
      onDiscardAudio?.();

      timerRef.current = setInterval(() => {
        elapsedRef.current += 1;
        setElapsed(elapsedRef.current);
        if (elapsedRef.current >= 600) handleStop();
      }, 1000);
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setRecording(false);
      setStarting(false);
      onBusyChange?.(false);
      setErrorNotice(
        error.name === "NotAllowedError" || error.name === "PermissionDeniedError"
          ? "Acesso ao microfone bloqueado. Libere a permissão no navegador e tente novamente."
          : "Não foi possível iniciar a gravação. Confira o microfone e tente novamente.",
      );
    }
  }

  function handleStop() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current?.state === "recording") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        onBusyChange?.(false);
        setErrorNotice("Não foi possível concluir a gravação. Tente novamente.");
      }
    }
    setRecording(false);
  }

  function handleDiscardAudio() {
    setErrorNotice("");
    onDiscardAudio?.();
  }

  return (
    <div className="voice-mic-control-root">
      {(!audioAttachment?.audioData || recording) && (
        <button
          type="button"
          className={`mic-inline-button ${recording ? "is-recording" : ""}`}
          onClick={recording ? handleStop : handleStart}
          disabled={starting || transcribing}
          title={recording ? "Concluir gravação" : "Gravar áudio pelo microfone"}
          aria-label={recording ? "Concluir gravação" : "Gravar áudio pelo microfone"}
          aria-pressed={recording}
        >
          {starting || transcribing
            ? <LoaderCircle size={18} className="spinner-dot" aria-hidden="true" />
            : recording
              ? <span className="mic-stop-square" aria-hidden="true" />
              : <Mic size={19} aria-hidden="true" />}
        </button>
      )}

      {recording && (
        <div className="mic-live-status-bar" role="status">
          <span className="live-rec-dot" aria-hidden="true" />
          <span className="live-rec-label">Gravando seu relato</span>
          <span className="live-rec-timer">{formatClock(elapsed)}</span>
          <div className="live-wave-bars" aria-hidden="true">
            <span className="wave-bar bar-1" />
            <span className="wave-bar bar-2" />
            <span className="wave-bar bar-3" />
            <span className="wave-bar bar-4" />
          </div>
          <button type="button" className="stop-inline-rec-btn" onClick={handleStop}>
            Concluir
          </button>
        </div>
      )}

      {audioAttachment?.audioData && !recording && (
        <div className="audio-attachment-pill">
          <div className="audio-pill-left">
            <AudioLines size={16} aria-hidden="true" />
            <span className="audio-pill-name">
              Áudio gravado{audioAttachment.audioDuration ? ` (${audioAttachment.audioDuration})` : ""}
            </span>
          </div>
          <audio controls src={audioAttachment.audioData} className="mini-audio-player" />
          <div className="audio-attachment-actions">
            <button
              type="button"
              className="audio-review-action audio-discard-action"
              onClick={handleDiscardAudio}
              disabled={starting || transcribing}
            >
              <X size={15} aria-hidden="true" />
              Excluir áudio
            </button>
            <button
              type="button"
              className="audio-review-action audio-redo-action"
              onClick={handleStart}
              disabled={starting || transcribing}
            >
              <Mic size={15} aria-hidden="true" />
              Refazer áudio
            </button>
          </div>
        </div>
      )}

      {transcript && (
        <div className="transcript-review-panel">
          <div className="transcript-review-heading">
            <label htmlFor="audio-transcript">Transcrição do áudio</label>
            <span>Revise antes de salvar</span>
          </div>
          <textarea
            id="audio-transcript"
            className="transcript-review-textarea"
            rows={4}
            value={transcript}
            onChange={(event) => onTranscriptChange(event.target.value)}
            maxLength={maxTranscriptLength}
          />
          <p className="transcript-review-caption">Você pode editar o texto. Ele só será enviado ao salvar o relato.</p>
        </div>
      )}
      {transcribing && (
        <div className="transcribing-inline-notice" role="status">
          <span className="spinner-dot" aria-hidden="true" />
          Preparando o modelo local e transcrevendo. No primeiro uso pode demorar.
        </div>
      )}

      {errorNotice && <div className="form-feedback erro" role="alert">{errorNotice}</div>}
    </div>
  );
}
