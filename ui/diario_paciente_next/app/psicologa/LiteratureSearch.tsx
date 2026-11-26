"use client";

import { useState, type FormEvent } from "react";
import styles from "./patient-management.module.css";

type Passage = {
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  source_url: string | null;
  license: string | null;
  quote_text: string;
  chunk_id: string;
};

type Consultation = {
  status: string;
  evidence_sufficient: boolean;
  answer_extractive: string;
  sources: Passage[];
  error_code: string | null;
  limitations: string[];
};

const STATUS_LABEL: Record<string, string> = {
  evidence: "Trechos recuperados. Isto não é diagnóstico nem conclusão clínica.",
  insufficient_evidence: "Evidência insuficiente na literatura autorizada.",
  empty_corpus: "A base científica não tem texto utilizável.",
  configuration_error: "A base científica não está configurada neste servidor.",
  error: "Falha operacional. Nenhum trecho foi usado como resposta.",
};

const ERROR_LABEL: Record<string, string> = {
  database_unconfigured: "A base científica não está configurada neste servidor.",
  database_unavailable: "A base científica configurada não está acessível.",
  storage_error: "A base científica não pôde ser lida.",
};

function sourceHref(passage: Passage) {
  if (passage.doi) return `https://doi.org/${passage.doi}`;
  return passage.source_url;
}

export default function LiteratureSearch() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Consultation | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/psicologa/literatura", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Falha ao consultar a literatura.");
        return;
      }
      setResult(body as Consultation);
    } catch {
      setError("Não foi possível contactar a API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={`${styles.card} ${styles.literatureSearch}`} aria-labelledby="literature-search-title">
      <div>
        <h2 id="literature-search-title">Consulta à literatura científica</h2>
        <p className={styles.literatureNote}>
          A busca usa somente os artigos autorizados. O relato de um paciente não entra nesta consulta.
        </p>
      </div>
      <form className={styles.literatureForm} onSubmit={onSubmit}>
        <label htmlFor="literature-query">Pergunta</label>
        <textarea
          id="literature-query"
          value={query}
          maxLength={2000}
          required
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? "Pesquisando…" : "Pesquisar"}
        </button>
      </form>
      {error ? <p className={styles.literatureError} role="alert">{error}</p> : null}
      {result ? (
        <div>
          <p className={styles.literatureStatus} role="status">
            {(result.error_code && ERROR_LABEL[result.error_code]) || STATUS_LABEL[result.status] || "Resposta recebida."}
          </p>
          {result.limitations?.length ? (
            <ul className={styles.literatureNote}>
              {result.limitations.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : null}
          {result.evidence_sufficient ? <p>{result.answer_extractive}</p> : null}
          {result.sources?.map((source) => {
            const href = sourceHref(source);
            return (
              <article className={styles.literatureSource} key={source.chunk_id}>
                <strong>{source.title}</strong>
                <span>
                  {source.authors?.join(", ")}
                  {source.year ? `. ${source.year}` : ""}
                  {source.license ? `. ${source.license}` : ""}
                </span>
                {href ? <a href={href}>{source.doi || href}</a> : null}
                <blockquote className={styles.literatureQuote}>{source.quote_text}</blockquote>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
