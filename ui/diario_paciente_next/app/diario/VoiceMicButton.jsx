"use client";

import { useEffect, useRef, useState } from "react";

export default function VoiceMicButton({
  onTranscript,
  onAudioReady,
  currentText = "",
  audioAttachment = null,
  onDiscardAudio,
}) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const [errorNotice, setErrorNotice] = useState("");

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const recognitionRef = useRef(null);
  const baseTextRef = useRef("");

  // Formata o cronômetro em MM:SS
  function formatClock(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (totalSeconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  }

  // Desliga tracks do microfone se o componente desmontar
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
    };
  }, []);

  async function handleToggleRecord() {
    if (recording) {
      handleStop();
    } else {
      await handleStart();
    }
  }

  async function handleStart() {
    setErrorNotice("");
    chunksRef.current = [];
    setElapsed(0);
    baseTextRef.current = currentText.trim();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: mimeType });
        const durationFormatted = formatClock(elapsed);
        const name = `audio_${new Date().toLocaleTimeString("pt-BR").replace(/:/g, "-")}.webm`;

        // Converte para base64 para persistência
        const reader = new FileReader();
        reader.onloadend = () => {
          onAudioReady({
            audioData: reader.result,
            audioName: name,
            audioDuration: durationFormatted,
            inputType: "audio",
          });
        };
        reader.readAsDataURL(audioBlob);

        // Se o navegador não deu suporte a Web Speech, transcreve via backend
        if (!recognitionRef.current && audioBlob.size > 0) {
          setTranscribing(true);
          try {
            const formData = new FormData();
            formData.append("audio", audioBlob, name);
            const res = await fetch("/api/diario/transcrever", {
              method: "POST",
              body: formData,
            });
            const data = await res.json();
            if (res.ok && data.text) {
              const base = baseTextRef.current;
              onTranscript(base ? `${base} ${data.text}` : data.text);
            }
          } catch {
            // Silencioso em caso de erro na transcrição
          } finally {
            setTranscribing(false);
          }
        }

        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
      };

      recorder.start(250);
      setRecording(true);

      // Cronômetro
      let secs = 0;
      timerRef.current = setInterval(() => {
        secs += 1;
        setElapsed(secs);
        if (secs >= 600) {
          handleStop();
        }
      }, 1000);

      // Web Speech API em tempo real (pt-BR)
      if (typeof window !== "undefined") {
        const SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
          try {
            const rec = new SpeechRecognition();
            rec.lang = "pt-BR";
            rec.continuous = true;
            rec.interimResults = true;

            let finalAccumulated = "";

            rec.onresult = (event) => {
              let interim = "";
              for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                  finalAccumulated += (finalAccumulated ? " " : "") + transcript;
                } else {
                  interim += transcript;
                }
              }

              const spoken = (
                finalAccumulated +
                (interim ? (finalAccumulated ? " " : "") + interim : "")
              ).trim();

              if (spoken) {
                const base = baseTextRef.current;
                onTranscript(base ? `${base} ${spoken}` : spoken);
              }
            };

            rec.onerror = () => {};
            rec.start();
            recognitionRef.current = rec;
          } catch {}
        }
      }
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorNotice("Acesso ao microfone bloqueado no navegador.");
      } else {
        setErrorNotice("Não foi possível acessar o microfone.");
      }
      setRecording(false);
    }
  }

  function handleStop() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {}
    }

    setRecording(false);
  }

  return (
    <div className="voice-mic-control-root">
      {/* Botão de Microfone posicionado ao lado do input */}
      <button
        type="button"
        className={`mic-inline-button ${recording ? "is-recording" : ""}`}
        onClick={handleToggleRecord}
        title={recording ? "Parar gravação de voz" : "Gravar áudio pelo microfone"}
        aria-label={recording ? "Parar gravação de voz" : "Gravar áudio pelo microfone"}
      >
        {recording ? (
          <span className="mic-stop-square" aria-hidden="true" />
        ) : (
          <span className="mic-icon" aria-hidden="true">🎙️</span>
        )}
      </button>

      {/* Barra de status animada durante a gravação */}
      {recording && (
        <div className="mic-live-status-bar" role="status">
          <span className="live-rec-dot" aria-hidden="true" />
          <span className="live-rec-label">Ouvindo e transcrevendo...</span>
          <span className="live-rec-timer">{formatClock(elapsed)}</span>
          <div className="live-wave-bars" aria-hidden="true">
            <span className="wave-bar bar-1" />
            <span className="wave-bar bar-2" />
            <span className="wave-bar bar-3" />
            <span className="wave-bar bar-4" />
          </div>
          <button
            type="button"
            className="stop-inline-rec-btn"
            onClick={handleStop}
          >
            Concluir
          </button>
        </div>
      )}

      {/* Card compacto com player do áudio gravado */}
      {audioAttachment?.audioData && !recording && (
        <div className="audio-attachment-pill">
          <div className="audio-pill-left">
            <span className="audio-pill-icon">🎙️</span>
            <span className="audio-pill-name">
              Áudio Gravado {audioAttachment.audioDuration ? `(${audioAttachment.audioDuration})` : ""}
            </span>
          </div>
          <audio
            controls
            src={audioAttachment.audioData}
            className="mini-audio-player"
          />
          <button
            type="button"
            className="discard-audio-icon-btn"
            onClick={onDiscardAudio}
            title="Descartar gravação de áudio"
            aria-label="Descartar gravação de áudio"
          >
            ✕
          </button>
        </div>
      )}

      {transcribing && (
        <div className="transcribing-inline-notice">
          <span className="spinner-dot" /> Transcrevendo o áudio...
        </div>
      )}

      {errorNotice && (
        <div className="form-feedback erro" style={{ marginTop: "6px" }} role="alert">
          {errorNotice}
        </div>
      )}
    </div>
  );
}
