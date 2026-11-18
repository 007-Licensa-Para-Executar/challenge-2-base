"use client";

import { useEffect, useRef, useState } from "react";

export default function AudioRecorder({
  inputMode,
  onChangeMode,
  onTranscriptReady,
  onAudioCaptured,
  onClearAudio,
}) {
  const [recording, setRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioName, setAudioName] = useState("");
  const [transcribing, setTranscribing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [speechSupported, setSpeechSupported] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const recognitionRef = useRef(null);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);

  // Detecta se a Web Speech API está disponível no navegador
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      setSpeechSupported(Boolean(SpeechRecognition));
    }
  }, []);

  // Formata os segundos em MM:SS
  function formatTime(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (totalSeconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  }

  // Inicia gravação com microfone + ditado por voz em tempo real
  async function handleStartRecording() {
    setErrorMessage("");
    audioChunksRef.current = [];
    setAudioUrl(null);
    setAudioName("");
    setElapsedSeconds(0);

    try {
      // 1. Acesso ao microfone via MediaDevices
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
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(audioBlob);
        const name = `gravação_${new Date().toLocaleTimeString("pt-BR").replace(/:/g, "-")}.webm`;
        const durationFormatted = formatTime(elapsedSeconds);

        setAudioUrl(url);
        setAudioName(name);

        // Converte para base64 para persistência segura
        const reader = new FileReader();
        reader.onloadend = () => {
          onAudioCaptured({
            audioData: reader.result,
            audioName: name,
            audioDuration: durationFormatted,
            inputType: "audio",
          });
        };
        reader.readAsDataURL(audioBlob);

        // Desliga os tracks do microfone
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
      };

      recorder.start(250); // Coleta a cada 250ms
      setRecording(true);

      // Cronômetro em tempo real
      let currentSeconds = 0;
      timerRef.current = setInterval(() => {
        currentSeconds += 1;
        setElapsedSeconds(currentSeconds);
        // Limite de segurança de 10 minutos
        if (currentSeconds >= 600) {
          handleStopRecording();
        }
      }, 1000);

      // 2. Ditado por Voz em Tempo Real (SpeechRecognition pt-BR)
      if (typeof window !== "undefined") {
        const SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
          try {
            const recognition = new SpeechRecognition();
            recognition.lang = "pt-BR";
            recognition.continuous = true;
            recognition.interimResults = true;

            let finalAccumulated = "";

            recognition.onresult = (event) => {
              let currentInterim = "";
              for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                  finalAccumulated += (finalAccumulated ? " " : "") + transcript;
                } else {
                  currentInterim += transcript;
                }
              }

              const combined = (
                finalAccumulated +
                (currentInterim ? (finalAccumulated ? " " : "") + currentInterim : "")
              ).trim();

              if (combined) {
                onTranscriptReady(combined);
              }
            };

            recognition.onerror = () => {
              // Silêncio em caso de ruído ou interrupção transitória
            };

            recognition.start();
            recognitionRef.current = recognition;
          } catch {
            // Se falhar o speech recognition, o áudio ainda continua gravando normalmente
          }
        }
      }
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage("Permissão de microfone negada no navegador. Habilite o acesso para gravar seu áudio.");
      } else {
        setErrorMessage("Não foi possível acessar o dispositivo de áudio.");
      }
      setRecording(false);
    }
  }

  // Para a gravação
  function handleStopRecording() {
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

  // Upload manual de arquivo de áudio
  async function handleFileSelected(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorMessage("");
    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage("O arquivo de áudio ultrapassa o limite de 25 MB.");
      return;
    }

    const validExtensions = [".wav", ".mp3", ".m4a", ".webm", ".ogg"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExtensions.includes(ext) && !file.type.startsWith("audio/")) {
      setErrorMessage("Formato não suportado. Escolha um arquivo WAV, MP3, M4A ou WEBM.");
      return;
    }

    const url = URL.createObjectURL(file);
    setAudioUrl(url);
    setAudioName(file.name);

    // Carrega em base64 para persistência
    const reader = new FileReader();
    reader.onloadend = () => {
      onAudioCaptured({
        audioData: reader.result,
        audioName: file.name,
        audioDuration: "Arquivo",
        inputType: "audio",
      });
    };
    reader.readAsDataURL(file);

    // Solicita transcrição ao backend
    setTranscribing(true);
    try {
      const formData = new FormData();
      formData.append("audio", file);

      const res = await fetch("/api/diario/transcrever", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (res.ok && data.text) {
        onTranscriptReady(data.text);
      }
    } catch {
      // Caso de falha silenciosa
    } finally {
      setTranscribing(false);
    }
  }

  function handleDiscard() {
    if (recording) {
      handleStopRecording();
    }
    setAudioUrl(null);
    setAudioName("");
    setElapsedSeconds(0);
    setErrorMessage("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClearAudio();
  }

  return (
    <div className="audio-input-widget">
      {/* Barra de modos: Digitar / Gravar / Upload */}
      <div className="input-mode-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={inputMode === "texto"}
          className={`mode-tab-button ${inputMode === "texto" ? "active" : ""}`}
          onClick={() => onChangeMode("texto")}
        >
          ✍️ Digitar Relato
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={inputMode === "voz"}
          className={`mode-tab-button ${inputMode === "voz" ? "active" : ""}`}
          onClick={() => onChangeMode("voz")}
        >
          🎙️ Gravar por Voz / Ditado
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={inputMode === "arquivo"}
          className={`mode-tab-button ${inputMode === "arquivo" ? "active" : ""}`}
          onClick={() => onChangeMode("arquivo")}
        >
          📁 Carregar Arquivo de Áudio
        </button>
      </div>

      {/* Painel do Modo de Gravação por Voz */}
      {inputMode === "voz" && (
        <div className="audio-panel voice-record-panel">
          <div className="voice-record-card">
            <div className="voice-record-center">
              <button
                type="button"
                className={`record-circle-button ${recording ? "is-recording" : ""}`}
                onClick={recording ? handleStopRecording : handleStartRecording}
                aria-label={recording ? "Parar gravação de voz" : "Iniciar gravação de voz"}
              >
                <span className="record-icon">{recording ? "⏹" : "🎙️"}</span>
              </button>

              <div className="record-info">
                {recording ? (
                  <>
                    <div className="recording-status-row">
                      <span className="live-dot" />
                      <span className="live-label">Gravando & Transcrevendo em tempo real</span>
                      <span className="recording-timer">{formatTime(elapsedSeconds)}</span>
                    </div>
                    {/* Animação de ondas de áudio */}
                    <div className="audio-wave-bars" aria-hidden="true">
                      <span className="wave-bar bar-1" />
                      <span className="wave-bar bar-2" />
                      <span className="wave-bar bar-3" />
                      <span className="wave-bar bar-4" />
                      <span className="wave-bar bar-5" />
                    </div>
                    <p className="record-hint">
                      Fale com naturalidade. Suas palavras aparecem automaticamente no texto do diário.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="record-title">
                      {audioUrl ? "Gravação concluída!" : "Fale e registre suas emoções"}
                    </p>
                    <p className="record-hint">
                      {speechSupported
                        ? "Clique no microfone para falar. A transcrição e a rede neural Divertidamente atuam em tempo real."
                        : "Clique no microfone para gravar seu áudio e anexá-lo ao diário."}
                    </p>
                  </>
                )}
              </div>
            </div>

            {recording && (
              <div className="recording-actions">
                <button
                  type="button"
                  className="stop-record-btn"
                  onClick={handleStopRecording}
                >
                  ⏹ Concluir Gravação ({formatTime(elapsedSeconds)})
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Painel do Modo de Upload de Arquivo */}
      {inputMode === "arquivo" && (
        <div className="audio-panel file-upload-panel">
          <input
            type="file"
            ref={fileInputRef}
            accept=".wav,.mp3,.m4a,.webm,.ogg,audio/*"
            style={{ display: "none" }}
            onChange={handleFileSelected}
          />
          <div
            className="audio-dropzone"
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
            }}
          >
            <span className="dropzone-icon">🎵</span>
            <p className="dropzone-title">Clique para selecionar um arquivo de áudio</p>
            <p className="dropzone-subtitle">Suporta WAV, MP3, M4A, WEBM ou OGG (até 25 MB)</p>
          </div>
        </div>
      )}

      {/* Card de Preview de Áudio Gravado ou Carregado */}
      {audioUrl && (
        <div className="audio-preview-card">
          <div className="preview-top-row">
            <div className="preview-file-info">
              <span className="file-icon">🎧</span>
              <div>
                <strong className="file-name">{audioName}</strong>
                {elapsedSeconds > 0 && (
                  <span className="file-meta"> • Duração: {formatTime(elapsedSeconds)}</span>
                )}
              </div>
            </div>
            <button
              type="button"
              className="discard-audio-button"
              onClick={handleDiscard}
              title="Descartar este áudio"
            >
              🗑️ Descartar
            </button>
          </div>

          <audio controls src={audioUrl} className="preview-audio-player" />

          {transcribing && (
            <div className="transcribing-notice">
              <span className="spinner-dot" /> Transcrevendo o áudio do relato...
            </div>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="form-feedback erro" role="alert" style={{ marginTop: "10px" }}>
          {errorMessage}
        </div>
      )}
    </div>
  );
}
