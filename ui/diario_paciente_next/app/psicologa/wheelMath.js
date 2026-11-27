// Geometria do Sunburst (2 anéis concêntricos) e gradiente polar estilo MIT ImpactBench.

export const MACRO_THEME_META = {
  familia: {
    label: "Família",
    shortLabel: "FAMÍLIA",
    description: "Vínculos familiares, convivência em casa, apoio ou atritos com parentes.",
  },
  trabalho: {
    label: "Trabalho",
    shortLabel: "TRABALHO",
    description: "Rotina profissional, sobrecarga de prazos, chefia, metas e realizações.",
  },
  relacionamentos: {
    label: "Relacionamentos",
    shortLabel: "RELAÇÕES",
    description: "Relacionamentos afetivos, amizades, limites interpessoais e comunicação.",
  },
  estudos: {
    label: "Estudos",
    shortLabel: "ESTUDOS",
    description: "Provas, entregas acadêmicas, desempenho e carga cognitiva nos estudos.",
  },
  saude_sono: {
    label: "Saúde & Sono",
    shortLabel: "SAÚDE & SONO",
    description: "Qualidade do sono, insônia, sintomas físicos, disposição e autocuidado.",
  },
  financas: {
    label: "Finanças",
    shortLabel: "FINANÇAS",
    description: "Preocupações materiais, dívidas, orçamento e estabilidade financeira.",
  },
  luto: {
    label: "Luto",
    shortLabel: "LUTO",
    description: "Elaboração de perdas, saudade profunda, abatimento e tristeza aguda.",
  },
  autoestima: {
    label: "Autoestima",
    shortLabel: "AUTOESTIMA",
    description: "Autocrítica, comparação social, culpa, confiança e valor próprio.",
  },
  outros_indeterminado: {
    label: "Outros / Indeterminado",
    shortLabel: "OUTROS",
    description: "Relatos abertos sem um único macro-tema predominante na rede neural.",
  },
};

export function getMacroMeta(macroKey) {
  return (
    MACRO_THEME_META[macroKey] || {
      label: macroKey || "Outros",
      shortLabel: String(macroKey || "OUTROS").toUpperCase().slice(0, 14),
      description: "Tema clínico agrupado a partir dos relatos do diário.",
    }
  );
}

export function polarToCartesian(radius, angleDeg) {
  // 0 graus no topo (-90 graus em coordenadas padrão SVG)
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: radius * Math.cos(rad),
    y: radius * Math.sin(rad),
  };
}

export function buildArcPath(innerR, outerR, startDeg, endDeg) {
  const span = endDeg - startDeg;
  const safeEnd = span >= 359.95 ? startDeg + 359.95 : endDeg;
  const largeArc = safeEnd - startDeg > 180 ? 1 : 0;

  const p1 = polarToCartesian(outerR, startDeg);
  const p2 = polarToCartesian(outerR, safeEnd);
  const p3 = polarToCartesian(innerR, safeEnd);
  const p4 = polarToCartesian(innerR, startDeg);

  return [
    `M ${p1.x.toFixed(3)} ${p1.y.toFixed(3)}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${p2.x.toFixed(3)} ${p2.y.toFixed(3)}`,
    `L ${p3.x.toFixed(3)} ${p3.y.toFixed(3)}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${p4.x.toFixed(3)} ${p4.y.toFixed(3)}`,
    "Z",
  ].join(" ");
}

/**
 * Replica a assinatura visual do gradiente radial do MIT ImpactBench:
 * - scores altos (bem-estar / positivo): verde esmeralda do centro para fora, borda suave.
 * - scores mistos: transição verde -> bege neutro -> coral na borda externa.
 * - scores negativos / sofrimento: predomínio rosa/coral intenso até vermelho clínico.
 */
export function buildImpactBenchGradientStops(healthRatio, hasData = true) {
  if (!hasData) {
    return [
      { offset: "0%", color: "#f3f4f6" },
      { offset: "100%", color: "#e5e7eb" },
    ];
  }

  const s = Math.max(0.05, Math.min(0.95, healthRatio));
  const pct = s * 100;
  const greenPeak = Math.max(0, pct - 55);
  const midPoint = (pct + 100) / 2;

  if (s >= 0.65) {
    return [
      { offset: "0%", color: "rgb(57, 176, 100)" },
      { offset: `${greenPeak.toFixed(1)}%`, color: "rgb(73, 182, 112)" },
      { offset: `${pct.toFixed(1)}%`, color: "rgb(147, 212, 169)" },
      { offset: `${midPoint.toFixed(1)}%`, color: "rgb(190, 206, 178)" },
      { offset: "100%", color: "rgb(241, 176, 176)" },
    ];
  }

  if (s >= 0.45) {
    return [
      { offset: "0%", color: "rgb(112, 198, 142)" },
      { offset: `${Math.max(5, pct - 20).toFixed(1)}%`, color: "rgb(176, 220, 190)" },
      { offset: `${pct.toFixed(1)}%`, color: "rgb(225, 188, 168)" },
      { offset: `${midPoint.toFixed(1)}%`, color: "rgb(236, 152, 152)" },
      { offset: "100%", color: "rgb(233, 128, 128)" },
    ];
  }

  if (s >= 0.30) {
    return [
      { offset: "0%", color: "rgb(214, 210, 178)" },
      { offset: "35%", color: "rgb(241, 178, 178)" },
      { offset: "72%", color: "rgb(235, 138, 138)" },
      { offset: "100%", color: "rgb(226, 98, 98)" },
    ];
  }

  return [
    { offset: "0%", color: "rgb(245, 188, 188)" },
    { offset: "45%", color: "rgb(238, 146, 146)" },
    { offset: "100%", color: "rgb(224, 92, 92)" },
  ];
}

export function polarityToHealthRatio(polarity) {
  const num = Number(polarity ?? 0);
  return Math.max(0, Math.min(1, (num + 1) / 2));
}

export function getValenceStatus(polarity, isRisk = false) {
  const p = Number(polarity ?? 0);
  if (isRisk || p <= -0.3) {
    return {
      key: "critical",
      label: isRisk ? "Acolhimento / Risco" : "Atenção clínica",
      badgeClass: "badgeCritical",
      dotColor: "#dc2626",
    };
  }
  if (p < 0.2) {
    return {
      key: "moderate",
      label: "Misto / Moderado",
      badgeClass: "badgeModerate",
      dotColor: "#d97706",
    };
  }
  return {
    key: "positive",
    label: "Bem-estar / Positivo",
    badgeClass: "badgePositive",
    dotColor: "#16a34a",
  };
}

export function wrapSubtopicLabel(text, maxCharsPerLine = 13, maxLines = 2) {
  const words = String(text || "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [""];

  const lines = [];
  let current = "";
  for (const w of words) {
    if (!current) {
      current = w;
    } else if (`${current} ${w}`.length <= maxCharsPerLine) {
      current = `${current} ${w}`;
    } else {
      lines.push(current);
      current = w;
      if (lines.length === maxLines - 1) break;
    }
  }
  if (lines.length < maxLines && current) {
    lines.push(current);
  }
  // Adiciona reticências apenas se sobrar texto significativo
  const joined = lines.join(" ");
  const full = words.join(" ");
  if (joined.length < full.length && lines.length > 0) {
    const last = lines[lines.length - 1];
    lines[lines.length - 1] = last.length > 10 ? `${last.slice(0, 10)}…` : `${last}…`;
  }
  return lines;
}

/**
 * Converte macrotemas + entradas enriquecidas em geometria Sunburst com 2 anéis reais:
 * Anel 1: Macro-temas da Rede Neural (ClinicalThemePredictor)
 * Anel 2: Subtemas do Agente 1 (SubtopicWheelTracker, filhos diretos do Anel 1)
 */
export function buildSunburstGeometry(wheel, entries = []) {
  const entryMap = new Map((entries || []).map((e) => [String(e.id), e]));
  const rawMacros = (wheel?.macrotemas || []).filter(
    (m) => (m.subtemas && m.subtemas.length > 0) || m.mencoes > 0,
  );

  // Fallback quando paciente ainda não tem entradas no período
  if (rawMacros.length === 0) {
    const defaultKeys = [
      "familia",
      "trabalho",
      "relacionamentos",
      "estudos",
      "saude_sono",
      "financas",
      "luto",
      "autoestima",
      "outros_indeterminado",
    ];
    const step = 360 / defaultKeys.length;
    return {
      isEmpty: true,
      ring1: defaultKeys.map((key, idx) => {
        const startDeg = idx * step;
        const endDeg = (idx + 1) * step;
        const meta = getMacroMeta(key);
        return {
          id: key,
          label: meta.label,
          shortLabel: meta.shortLabel,
          description: meta.description,
          startDeg,
          endDeg,
          midDeg: (startDeg + endDeg) / 2,
          spanDeg: step,
          mencoes: 0,
          polarity: 0,
          healthRatio: 0.5,
          counts: { positive: 0, neutral: 0, negative: 0 },
          subtemas: [],
        };
      }),
      ring2: [],
    };
  }

  // Peso angular por macro-tema proporcional à soma de subtemas/peso, com piso mínimo para legibilidade
  const rawWeights = rawMacros.map((m) =>
    Math.max(1.2, m.peso_total || m.mencoes || (m.subtemas?.length || 1)),
  );
  const totalWeight = rawWeights.reduce((acc, v) => acc + v, 0);

  let cursor = 0;
  const ring1 = [];
  const ring2 = [];

  rawMacros.forEach((macro, idx) => {
    const weight = rawWeights[idx];
    const spanDeg = (weight / totalWeight) * 360;
    const startDeg = cursor;
    const endDeg = idx === rawMacros.length - 1 ? 360 : cursor + spanDeg;
    cursor = endDeg;

    const meta = getMacroMeta(macro.macro_tema);
    const matchingEntries = (entries || []).filter(
      (e) => (e.theme_macro || e.agent1?.macro_tema_validado) === macro.macro_tema,
    );
    const counts = countValences(matchingEntries);
    const avgPol =
      matchingEntries.length > 0
        ? matchingEntries.reduce((a, b) => a + Number(b.polarity_score ?? 0), 0) / matchingEntries.length
        : Number(macro.polaridade_media ?? 0);

    const macroHealth = polarityToHealthRatio(avgPol);
    const subs = macro.subtemas || [];
    const subWeights = subs.map((s) => Math.max(1, s.peso_total || s.mencoes || 1));
    const subWeightTotal = subWeights.reduce((a, b) => a + b, 0) || 1;

    let subCursor = startDeg;
    const builtSubs = subs.map((sub, sIdx) => {
      const sSpan = (subWeights[sIdx] / subWeightTotal) * (endDeg - startDeg);
      const sStart = subCursor;
      const sEnd = sIdx === subs.length - 1 ? endDeg : subCursor + sSpan;
      subCursor = sEnd;

      const occurrences = extractSubtopicOccurrences(macro.macro_tema, sub, entries, entryMap);
      const subCounts = countValences(occurrences.map((o) => o.entry));
      const subAvgPol =
        occurrences.length > 0
          ? occurrences.reduce((a, o) => a + Number(o.entry.polarity_score ?? 0), 0) / occurrences.length
          : Number(sub.polaridade_media ?? avgPol);

      const node = {
        key: `${macro.macro_tema}::${sub.original_nome || sub.nome}`,
        id: sub.nome,
        originalName: sub.original_nome || sub.nome,
        parentId: macro.macro_tema,
        parentLabel: meta.label,
        label: sub.nome,
        clinicalNote: sub.clinical_note || "",
        editedByPsychologist: Boolean(sub.edited_by_psychologist),
        startDeg: sStart,
        endDeg: sEnd,
        midDeg: (sStart + sEnd) / 2,
        spanDeg: sEnd - sStart,
        mencoes: sub.mencoes || occurrences.length,
        polarity: subAvgPol,
        healthRatio: polarityToHealthRatio(subAvgPol),
        counts: subCounts,
        occurrences,
        fonte: "Agente 1",
      };
      ring2.push(node);
      return node;
    });

    ring1.push({
      id: macro.macro_tema,
      label: meta.label,
      shortLabel: meta.shortLabel,
      description: meta.description,
      startDeg,
      endDeg,
      midDeg: (startDeg + endDeg) / 2,
      spanDeg: endDeg - startDeg,
      mencoes: matchingEntries.length || macro.mencoes,
      entryCount: matchingEntries.length,
      polarity: avgPol,
      healthRatio: macroHealth,
      counts,
      subtemas: builtSubs,
      fonte: "Rede Neural (MLP)",
    });
  });

  return { isEmpty: false, ring1, ring2 };
}

function countValences(entries) {
  let positive = 0;
  let negative = 0;
  let neutral = 0;
  for (const e of entries) {
    if (!e) continue;
    const pol = Number(e.polarity_score ?? 0);
    if (e.is_risk_emotion || pol <= -0.15) negative += 1;
    else if (pol >= 0.15) positive += 1;
    else neutral += 1;
  }
  return { positive, neutral, negative };
}

function extractSubtopicOccurrences(macroTema, sub, entries) {
  const occurrences = [];
  const targetName = sub.original_nome || sub.nome;
  for (const entry of entries) {
    const entryMacro = entry.theme_macro || entry.agent1?.macro_tema_validado;
    if (entryMacro !== macroTema) continue;
    const agentSub = (entry.agent1?.subtemas || []).find((s) => s.nome === targetName);
    if (!agentSub) continue;
    const evidencias = agentSub.evidencias && agentSub.evidencias.length > 0
      ? agentSub.evidencias
      : [{ quote_text: entry.text.slice(0, 140), start_char: 0, end_char: Math.min(entry.text.length, 140) }];

    occurrences.push({
      occurrenceId: `${entry.id}::${targetName}`,
      entry,
      subtopicName: sub.nome,
      originalSubtopicName: targetName,
      description: agentSub.descricao || "",
      evidencias,
      primarySpan: evidencias[0],
    });
  }
  return occurrences.sort((a, b) => Number(b.entry.created_at) - Number(a.entry.created_at));
}
