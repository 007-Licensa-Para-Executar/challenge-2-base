"use client";

import { useState } from "react";
import Image from "next/image";
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTheme, PortalPatient } from "./types";
import { DASHBOARD_THEMES } from "./types";
import styles from "./patient-management.module.css";

interface PatientDashboardProps {
  patient: PortalPatient;
}

const wheelCenterX = 619;
const wheelCenterY = 630;
const wheelOuterRadius = 548;
const wheelInnerRadius = 243;
const wheelSegmentAngle = 360 / DASHBOARD_THEMES.length;

// Cada tema tem uma cor de apoio; a legenda textual continua legível sem cor.
const themeColors: Record<DashboardTheme, string> = {
  Relacionamentos: "#315C50",
  "Saúde e Sono": "#587B70",
  Finanças: "#8A6A36",
  "Outros / Indeterminado": "#596B9A",
  Trabalho: "#8D554A",
  Autoestima: "#477D89",
  Luto: "#735F7E",
  Família: "#657846",
  Estudos: "#9B6641",
};

function wheelPoint(angleDegrees: number, radius: number) {
  const radians = (angleDegrees * Math.PI) / 180;
  return {
    x: wheelCenterX + Math.cos(radians) * radius,
    y: wheelCenterY + Math.sin(radians) * radius,
  };
}

function wheelSegmentPath(index: number) {
  const middleAngle = -90 + index * wheelSegmentAngle;
  const startAngle = middleAngle - wheelSegmentAngle / 2;
  const endAngle = middleAngle + wheelSegmentAngle / 2;
  const outerStart = wheelPoint(startAngle, wheelOuterRadius);
  const outerEnd = wheelPoint(endAngle, wheelOuterRadius);
  const innerEnd = wheelPoint(endAngle, wheelInnerRadius);
  const innerStart = wheelPoint(startAngle, wheelInnerRadius);

  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${wheelOuterRadius} ${wheelOuterRadius} 0 0 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${wheelInnerRadius} ${wheelInnerRadius} 0 0 0 ${innerStart.x} ${innerStart.y}`,
    "Z",
  ].join(" ");
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function formatEntryDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data indisponível";

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

// Os gráficos visuais são ocultos da árvore acessível; tabelas e legendas oferecem os mesmos dados em texto.
export default function PatientDashboard({ patient }: PatientDashboardProps) {
  const [selectedTheme, setSelectedTheme] = useState<DashboardTheme | null>(null);
  const diaryEntries = patient.history.filter((item) => item.type === "diario").length;
  const consultations = patient.history.filter((item) => item.type === "consulta").length;
  const reportsCount = patient.reports.length;
  const themeData = DASHBOARD_THEMES.map((theme) => {
    const entries = patient.history.filter(
      (item) => item.type === "diario" && item.theme === theme,
    );

    return {
      theme,
      entries,
      total: Math.max(patient.themeDistribution[theme], entries.length),
    };
  });
  const totalThemeMentions = themeData.reduce((total, item) => total + item.total, 0);
  const hasDiaryData = patient.weeklyDiaryCounts.some((week) => week.entries > 0);
  const selectedThemeData = themeData.find((item) => item.theme === selectedTheme) ?? null;

  const metrics = [
    { label: "Entradas no diário", value: diaryEntries, note: "registros disponíveis" },
    { label: "Relatórios", value: reportsCount, note: "arquivos enviados" },
    { label: "Consultas", value: consultations, note: "registros no histórico" },
  ];

  return (
    <section className={styles.dashboard} aria-labelledby="dashboard-heading">
      <div className={styles.sectionHeading}>
        <div>
          <p className={styles.eyebrow}>VISÃO GERAL</p>
          <h2 id="dashboard-heading">Acompanhamento</h2>
        </div>
        <p className={styles.demoLabel}>Dados fictícios de demonstração</p>
      </div>

      <div className={styles.metricGrid}>
        {metrics.map((metric) => (
          <article className={styles.metricCard} key={metric.label}>
            <span className={styles.metricIcon} aria-hidden="true">
              {metric.label === "Entradas no diário" ? "D" : metric.label === "Relatórios" ? "R" : "C"}
            </span>
            <div>
              <p>{metric.label}</p>
              <strong>{formatNumber(metric.value)}</strong>
              <span>{metric.note}</span>
            </div>
          </article>
        ))}
      </div>

      <div className={styles.chartGrid}>
        <article className={styles.card} aria-labelledby="trend-heading">
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>RITMO AO LONGO DO TEMPO</p>
              <h3 id="trend-heading">Entradas no diário</h3>
            </div>
            <span className={styles.chartPeriod}>8 semanas</span>
          </div>

          {hasDiaryData ? (
            <>
              <p className={styles.chartDescription} id="trend-description">
                Quantidade de entradas por semana, conforme os dados fictícios disponíveis.
              </p>
              <div className={styles.chartPlot} aria-hidden="true">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={patient.weeklyDiaryCounts} margin={{ top: 12, right: 12, bottom: 4, left: -18 }}>
                    <CartesianGrid stroke="rgba(38, 51, 47, 0.12)" vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#5E6C64", fontSize: 12 }} />
                    <YAxis allowDecimals={false} width={34} tickLine={false} axisLine={false} tick={{ fill: "#5E6C64", fontSize: 12 }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="entries"
                      name="Entradas"
                      stroke="#315C50"
                      strokeWidth={3}
                      dot={{ r: 4, fill: "#FFFFFF", stroke: "#315C50", strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <table className={styles.screenReaderOnly}>
                <caption>Entradas no diário por semana</caption>
                <thead><tr><th scope="col">Semana</th><th scope="col">Entradas</th></tr></thead>
                <tbody>
                  {patient.weeklyDiaryCounts.map((week) => (
                    <tr key={week.label}><th scope="row">{week.label}</th><td>{week.entries}</td></tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className={styles.chartEmpty}>Ainda não há entradas para mostrar neste período.</p>
          )}
        </article>

        <article className={styles.card} aria-labelledby="themes-heading">
          <div className={styles.cardHeading}>
            <div>
              <p className={styles.eyebrow}>DISTRIBUIÇÃO POR TEMA</p>
              <h3 id="themes-heading">Temas do diário</h3>
            </div>
            <span className={styles.chartPeriod}>{formatNumber(totalThemeMentions)} registros</span>
          </div>

          <div className={styles.themeChartLayout}>
            {totalThemeMentions > 0 ? (
              <div className={styles.donutPlot} aria-hidden="true">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={themeData}
                      dataKey="total"
                      nameKey="theme"
                      innerRadius="59%"
                      outerRadius="88%"
                      paddingAngle={2}
                      stroke="#FFFFFF"
                      strokeWidth={2}
                      isAnimationActive={false}
                    >
                      {themeData.map((item) => (
                        <Cell key={item.theme} fill={themeColors[item.theme]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className={styles.chartEmpty}>Sem registros classificados ainda.</p>
            )}
            <ul className={styles.themeLegend} aria-label="Distribuição nos nove temas">
              {themeData.map((item) => (
                <li key={item.theme}>
                  <span className={styles.themeSwatch} style={{ backgroundColor: themeColors[item.theme] }} aria-hidden="true" />
                  <span>{item.theme}</span>
                  <strong>{formatNumber(item.total)}</strong>
                </li>
              ))}
            </ul>
          </div>
          <p className={styles.chartFootnote}>A distribuição usa somente os nove temas definidos para esta versão.</p>
        </article>
      </div>

      <article className={`${styles.card} ${styles.themeWheelCard}`} aria-labelledby="wheel-heading">
        <div className={styles.cardHeading}>
          <div>
            <p className={styles.eyebrow}>VISUALIZAÇÃO INTERATIVA</p>
            <h3 id="wheel-heading">Roda da Vida em Equilíbrio</h3>
          </div>
          <span className={styles.chartPeriod}>9 temas</span>
        </div>
        <p className={styles.chartDescription}>
          Clique ou use Tab e Enter para selecionar um tema e consultar os dados.
        </p>

        <div className={styles.themeWheelLayout}>
          <div className={styles.wheelWrap}>
            <Image
              className={styles.wheelImage}
              src="/roda-vida-equilibrio.png"
              alt=""
              aria-hidden="true"
              width={1254}
              height={1254}
              priority
            />
            <svg
              className={styles.wheelHotspots}
              viewBox="0 0 1254 1254"
              role="group"
              aria-labelledby="wheel-svg-title"
            >
              <title id="wheel-svg-title">Roda interativa com os nove temas do diário</title>
              {themeData.map((item, index) => {
                const isSelected = selectedTheme === item.theme;

                return (
                  <g
                    key={item.theme}
                    className={styles.wheelSegment}
                    role="button"
                    tabIndex={0}
                    aria-label={`${item.theme}: ${formatNumber(item.total)} ${item.total === 1 ? "registro" : "registros"}`}
                    aria-pressed={isSelected}
                    aria-controls="theme-details"
                    onClick={() => setSelectedTheme(item.theme)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedTheme(item.theme);
                      }
                    }}
                  >
                    <path
                      d={wheelSegmentPath(index)}
                      fill="rgba(49, 92, 80, 0.001)"
                      stroke="transparent"
                      pointerEvents="all"
                    />
                  </g>
                );
              })}
            </svg>
          </div>

          <aside className={styles.themeDetails} id="theme-details" aria-live="polite">
            {selectedThemeData ? (
              <>
                <p className={styles.themeDetailEyebrow}>TEMA SELECIONADO</p>
                <h4 className={styles.themeDetailHeading}>{selectedThemeData.theme}</h4>
                <div className={styles.themeDetailCount}>
                  <strong>{formatNumber(selectedThemeData.total)}</strong>
                  <span>{selectedThemeData.total === 1 ? "registro" : "registros"} no diário</span>
                </div>
                {selectedThemeData.entries.length > 0 ? (
                  <ul className={styles.themeRecords}>
                    {selectedThemeData.entries.map((entry) => (
                      <li key={entry.id}>
                        <div className={styles.themeRecordHeading}>
                          <strong>{entry.title}</strong>
                          <time dateTime={entry.date}>{formatEntryDate(entry.date)}</time>
                        </div>
                        {entry.description && <p>{entry.description}</p>}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className={styles.themeEmptyState}>
                    <span aria-hidden="true">○</span>
                    <p>
                      {selectedThemeData.total === 0
                        ? `Ainda não há registros em ${selectedThemeData.theme}.`
                        : "Os registros foram contados, mas seus detalhes ainda não estão disponíveis."}
                    </p>
                    {selectedThemeData.total === 0 && (
                      <small>Quando houver entradas do diário nesse tema, elas aparecerão aqui.</small>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className={styles.themeEmptyState}>
                <span aria-hidden="true">✳</span>
                <h4 className={styles.themeDetailHeading}>Explore os temas</h4>
                <p>Selecione um setor da roda para consultar os registros do diário.</p>
              </div>
            )}
          </aside>
        </div>
      </article>
    </section>
  );
}
