"use client";

import { useMemo, useRef, useState } from "react";
import {
  buildArcPath,
  buildImpactBenchGradientStops,
  polarToCartesian,
  wrapSubtopicLabel,
} from "./wheelMath";
import styles from "./impactbench.module.css";

function sanitizeGradId(raw) {
  return String(raw).replace(/[^a-zA-Z0-9_-]/g, "_");
}

function formatRing1LabelTransform(midDeg, radius) {
  const pos = polarToCartesian(radius, midDeg);
  // Mantém o texto tangencial sempre legível (sem ponta-cabeça na metade inferior)
  let rot = midDeg;
  if (midDeg > 90 && midDeg < 270) rot += 180;
  return `translate(${pos.x.toFixed(2)}, ${pos.y.toFixed(2)}) rotate(${rot.toFixed(2)})`;
}

function formatRing2LabelTransform(midDeg, radius) {
  const pos = polarToCartesian(radius, midDeg);
  // Orientação radial do centro para fora, invertida no lado esquerdo para leitura natural
  let rot = midDeg - 90;
  if (midDeg > 180) rot = midDeg + 90;
  return `translate(${pos.x.toFixed(2)}, ${pos.y.toFixed(2)}) rotate(${rot.toFixed(2)})`;
}

export default function ImpactBenchSunburst({
  geometry,
  selectedThemeId,
  selectedSubtopicKey,
  valenceFilter,
  totalSubtemas,
  maxSubtemas = 24,
  isDemo = false,
  onSelectTheme,
  onSelectSubtopic,
  onResetSelection,
  onChangeValenceFilter,
}) {
  const containerRef = useRef(null);
  const [hovered, setHovered] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const hasSelection = Boolean(selectedThemeId || selectedSubtopicKey);
  const { isEmpty, ring1, ring2 } = geometry;

  const activeLegendTitle = useMemo(() => {
    if (selectedSubtopicKey) {
      const sub = ring2.find((s) => s.key === selectedSubtopicKey);
      if (sub) return `${sub.label} (${sub.parentLabel})`;
    }
    if (selectedThemeId) {
      const macro = ring1.find((m) => m.id === selectedThemeId);
      if (macro) return macro.label;
    }
    return "Visão Geral · Todos os Temas";
  }, [ring1, ring2, selectedSubtopicKey, selectedThemeId]);

  function handlePointerMove(event) {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.min(Math.max(16, event.clientX - rect.left + 14), rect.width - 275);
    const y = Math.min(Math.max(16, event.clientY - rect.top - 24), rect.height - 155);
    setTooltipPos({ x, y });
  }

  return (
    <div className={styles.centerCanvas} ref={containerRef} onMouseMove={handlePointerMove}>
      <div className={styles.canvasTopBar}>
        <div className={styles.engineStatusPill}>
          <span className={styles.engineDot} aria-hidden="true" />
          <span>
            Anel 1: <strong>Rede Neural (MLP)</strong> · Anel 2: <strong>Agente 1</strong>{" "}
            ({totalSubtemas}/{maxSubtemas} subtemas)
          </span>
          {isDemo && <span className={styles.demoTag}>DEMO SINTÉTICO</span>}
        </div>

        <label className={styles.filterPillWrap}>
          <span className={styles.filterIcon} aria-hidden="true">⌄</span>
          <select
            aria-label="Filtrar valência emocional da roda"
            className={styles.filterSelect}
            value={valenceFilter}
            onChange={(e) => onChangeValenceFilter(e.target.value)}
          >
            <option value="all">Filtro: Todos os relatos</option>
            <option value="negative">Apenas alerta & negativos</option>
            <option value="positive">Apenas bem-estar & positivos</option>
          </select>
        </label>
      </div>

      <div className={styles.svgStage}>
        <svg
          id="sunburst-svg"
          className={styles.sunburstSvg}
          viewBox="-390.625 -390.625 781.25 781.25"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Roda hierárquica de temas da rede neural e subtemas do Agente 1"
        >
          <defs>
            <clipPath id="sunburst-center-clip">
              <circle r="96" />
            </clipPath>

            {ring1.map((macro) => {
              const stops = buildImpactBenchGradientStops(macro.healthRatio, !isEmpty);
              return (
                <radialGradient
                  key={`grad-r1-${macro.id}`}
                  id={`area-grad-${sanitizeGradId(macro.id)}`}
                  gradientUnits="userSpaceOnUse"
                  cx="0"
                  cy="0"
                  r="195"
                  fr="105"
                >
                  {stops.map((s, idx) => (
                    <stop key={idx} offset={s.offset} stopColor={s.color} />
                  ))}
                </radialGradient>
              );
            })}

            {ring2.map((sub) => {
              const stops = buildImpactBenchGradientStops(sub.healthRatio, !isEmpty);
              return (
                <radialGradient
                  key={`grad-r2-${sub.key}`}
                  id={`subarea-grad-${sanitizeGradId(sub.key)}`}
                  gradientUnits="userSpaceOnUse"
                  cx="0"
                  cy="0"
                  r="335"
                  fr="200"
                >
                  {stops.map((s, idx) => (
                    <stop key={idx} offset={s.offset} stopColor={s.color} />
                  ))}
                </radialGradient>
              );
            })}
          </defs>

          <g className="arcs-group">
            {/* ANEL 1: MACRO-TEMAS EXTRAÍDOS PELA REDE NEURAL */}
            {ring1.map((macro) => {
              const isSelected = selectedThemeId === macro.id;
              const isDimmed = hasSelection && !isSelected;
              const pathD = buildArcPath(105, 195, macro.startDeg, macro.endDeg);
              const gradId = `area-grad-${sanitizeGradId(macro.id)}`;

              return (
                <g
                  key={macro.id}
                  data-ring="1"
                  data-node-id={macro.id}
                  className={styles.arcGroup}
                  style={{ opacity: isDimmed ? 0.22 : 1, cursor: isEmpty ? "default" : "pointer" }}
                  tabIndex={isEmpty ? -1 : 0}
                  role="button"
                  aria-label={`Tema ${macro.label}: ${macro.mencoes} relatos`}
                  aria-pressed={isSelected}
                  onClick={() => !isEmpty && onSelectTheme(macro.id)}
                  onKeyDown={(e) => {
                    if (!isEmpty && (e.key === "Enter" || e.key === " ")) {
                      e.preventDefault();
                      onSelectTheme(macro.id);
                    }
                  }}
                  onMouseEnter={() =>
                    setHovered({
                      kind: "TEMA · REDE NEURAL",
                      title: macro.label,
                      description: macro.description,
                      healthPct: Math.round(macro.healthRatio * 100),
                      counts: macro.counts,
                      total: macro.mencoes,
                      hasData: !isEmpty,
                    })
                  }
                  onMouseLeave={() => setHovered(null)}
                >
                  <path
                    d={pathD}
                    fill={`url(#${gradId})`}
                    stroke={isSelected ? "#0f172a" : "#ffffff"}
                    strokeWidth={isSelected ? 3.2 : 2.5}
                  />
                  {macro.spanDeg >= 16 && (
                    <text
                      className="area-label"
                      data-node-id={macro.id}
                      x="0"
                      y="0"
                      transform={formatRing1LabelTransform(macro.midDeg, 150)}
                      style={{
                        fill: "#1f2937",
                        fontSize: macro.spanDeg < 26 ? "9.5px" : "11px",
                        fontWeight: 700,
                        letterSpacing: "0.04em",
                        textAnchor: "middle",
                        dominantBaseline: "middle",
                        pointerEvents: "none",
                      }}
                    >
                      {macro.shortLabel}
                    </text>
                  )}
                </g>
              );
            })}

            {/* ANEL 2: SUBTEMAS EXTRAÍDOS PELO AGENTE 1 (FILHOS DO ANEL 1) */}
            {ring2.map((sub) => {
              const isSelected = selectedSubtopicKey === sub.key;
              const isParentSelected = selectedThemeId === sub.parentId && !selectedSubtopicKey;
              const isActive = isSelected || isParentSelected;
              const isDimmed = hasSelection && !isActive;
              const pathD = buildArcPath(200, 335, sub.startDeg, sub.endDeg);
              const gradId = `subarea-grad-${sanitizeGradId(sub.key)}`;
              const lines = wrapSubtopicLabel(sub.label, sub.spanDeg < 18 ? 10 : 14, 2);

              return (
                <g
                  key={sub.key}
                  data-ring="2"
                  data-node-id={sub.key}
                  className={styles.arcGroup}
                  style={{ opacity: isDimmed ? 0.22 : 1, cursor: "pointer" }}
                  tabIndex={0}
                  role="button"
                  aria-label={`Subtema ${sub.label} (${sub.parentLabel}): ${sub.mencoes} menções`}
                  aria-pressed={isSelected}
                  onClick={() => onSelectSubtopic(sub.parentId, sub.key)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectSubtopic(sub.parentId, sub.key);
                    }
                  }}
                  onMouseEnter={() =>
                    setHovered({
                      kind: `SUBTEMA · AGENTE 1 · ${sub.parentLabel.toUpperCase()}`,
                      title: sub.label,
                      description:
                        sub.occurrences?.[0]?.description ||
                        `Subtema extraído pelo Agente 1 dentro de ${sub.parentLabel}.`,
                      healthPct: Math.round(sub.healthRatio * 100),
                      counts: sub.counts,
                      total: sub.occurrences?.length || sub.mencoes,
                      hasData: true,
                    })
                  }
                  onMouseLeave={() => setHovered(null)}
                >
                  <path
                    d={pathD}
                    fill={`url(#${gradId})`}
                    stroke={isSelected ? "#0f172a" : "#ffffff"}
                    strokeWidth={isSelected ? 3 : 2}
                  />
                  {sub.spanDeg >= 9 && (
                    <text
                      className="subarea-label"
                      data-node-id={sub.key}
                      x="0"
                      y="0"
                      transform={formatRing2LabelTransform(sub.midDeg, 267.5)}
                      style={{
                        fill: "#1f2937",
                        fontSize: sub.spanDeg < 15 ? "10px" : "11.5px",
                        fontWeight: isSelected ? 700 : 500,
                        textAnchor: "middle",
                        dominantBaseline: "middle",
                        pointerEvents: "none",
                      }}
                    >
                      {lines.map((line, i) => (
                        <tspan
                          key={i}
                          x="0"
                          dy={i === 0 ? (lines.length === 1 ? "0" : "-0.55em") : "1.15em"}
                        >
                          {line}
                        </tspan>
                      ))}
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          {/* CENTRO: HOMEM VITRUVIANO (BOTÃO DE RESET PARA VISÃO GERAL) */}
          <g
            clipPath="url(#sunburst-center-clip)"
            style={{ cursor: hasSelection ? "pointer" : "default" }}
            onClick={() => hasSelection && onResetSelection()}
          >
            <circle cx="0" cy="0" r="98" fill="#ffffff" />
            <g stroke="#374151" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.88">
              <circle cx="0" cy="2" r="78" strokeWidth="1.6" />
              <rect x="-64" y="-44" width="128" height="124" strokeWidth="1.2" opacity="0.55" />
              {/* Cabeça */}
              <circle cx="0" cy="-42" r="10.5" fill="#4b5563" stroke="none" />
              {/* Braços abertos (pose horizontal + pose elevada) */}
              <path d="M-64 -26 L64 -26" strokeWidth="4.2" stroke="#4b5563" />
              <path d="M-54 -56 L0 -25 L54 -56" strokeWidth="3.2" stroke="#6b7280" />
              {/* Tronco */}
              <path d="M-14 -28 L14 -28 L10 18 L-10 18 Z" fill="#4b5563" stroke="none" />
              {/* Pernas (vertical + afastada) */}
              <path d="M-6 18 L-9 78 M6 18 L9 78" strokeWidth="4.4" stroke="#4b5563" />
              <path d="M-5 18 L-34 72 M5 18 L34 72" strokeWidth="3.2" stroke="#6b7280" />
            </g>
          </g>
          <circle
            className="center-circle"
            r="98"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="2"
            style={{ pointerEvents: "none" }}
          />
        </svg>

        {isEmpty && (
          <div className={styles.emptyWheelOverlay}>
            <p>Nenhum registro no período/filtro selecionado</p>
            <span>Adicione entradas no Diário ou altere o filtro acima.</span>
          </div>
        )}
      </div>

      {/* TOOLTIP FLUTUANTE ESCURO (PADRÃO IMPACTBENCH) */}
      {hovered && hovered.hasData && (
        <div
          className={styles.sunburstTooltip}
          style={{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }}
          role="tooltip"
        >
          <div className={styles.tooltipHeader}>
            <span className={styles.tooltipKind}>{hovered.kind}</span>
            <strong>{hovered.title}</strong>
          </div>
          {hovered.description && <p className={styles.tooltipDesc}>{hovered.description}</p>}
          <div className={styles.tooltipMetricRow}>
            <span
              className={styles.tooltipScore}
              style={{
                color: hovered.healthPct >= 55 ? "#4ade80" : hovered.healthPct <= 40 ? "#f87171" : "#fbbf24",
              }}
            >
              {hovered.healthPct}%
            </span>
            <span className={styles.tooltipMetricLabel}>BEM-ESTAR RELATIVO</span>
          </div>
          <div className={styles.tooltipBar}>
            {hovered.total > 0 && (
              <>
                <span style={{ width: `${(hovered.counts.positive / hovered.total) * 100}%`, background: "#22c55e" }} />
                <span style={{ width: `${(hovered.counts.neutral / hovered.total) * 100}%`, background: "#94a3b8" }} />
                <span style={{ width: `${(hovered.counts.negative / hovered.total) * 100}%`, background: "#ef4444" }} />
              </>
            )}
          </div>
          <p className={styles.tooltipCounts}>
            {hovered.counts.positive} positivos · {hovered.counts.neutral} neutros ·{" "}
            {hovered.counts.negative} negativos ({hovered.total})
          </p>
        </div>
      )}

      {/* LEGENDA INFERIOR DO ESPECTRO */}
      <div className={styles.legendSection}>
        <h3 className={styles.legendTitle}>{activeLegendTitle}</h3>
        <div className={styles.legendScale}>
          <span className={styles.legendNeg}>
            <i aria-hidden="true" />
            Sofrimento / Alerta
          </span>
          <div className={styles.legendGradientBar} aria-hidden="true" />
          <span className={styles.legendPos}>
            Bem-estar / Florescimento
            <i aria-hidden="true" />
          </span>
        </div>
      </div>
    </div>
  );
}
