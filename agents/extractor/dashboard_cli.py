"""CLI ponte em JSON (stdin/stdout) entre o dashboard Next.js e os módulos de IA."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from agents.copilot.contracts import DiaryRecord, Query, ThemePrediction
from agents.copilot.model import OllamaGenerator
from agents.copilot.retriever import Retriever
from agents.copilot.service import CopilotService
from agents.copilot.storage import DiaryStore
from agents.extractor.config import Settings
from agents.extractor.contracts import (
    Agent1Output,
    EvidenceSpan,
    IndicioRisco,
    MacroTema,
    Sentimento,
    SubTemaItem,
)
from agents.extractor.service import Agent1Service, analyze_polarity, validate_polarity
from agents.extractor.wheel import SubtopicWheelTracker

_PT_POSITIVE = {
    "feliz", "alegre", "alegria", "bem", "calmo", "calma", "tranquilo", "tranquila",
    "grato", "grata", "gratidao", "gratidão", "orgulho", "leve", "esperanca", "esperança",
    "animado", "animada", "otimo", "ótimo", "melhor", "melhorou", "consegui", "apoio",
    "acolhido", "acolhida", "carinho", "descansado", "descansada", "paz", "alivio", "alívio",
}
_PT_NEGATIVE = {
    "triste", "tristeza", "choro", "chorei", "luto", "aperto", "angustia", "angústia",
    "ansioso", "ansiosa", "ansiedade", "medo", "pavor", "panico", "pânico", "raiva",
    "odio", "ódio", "explodir", "pessimo", "péssimo", "horrivel", "horrível", "cansado",
    "cansada", "exausto", "exausta", "esgotado", "esgotada", "sobrecarga", "pressao",
    "pressão", "insonia", "insônia", "pesadelo", "culpa", "vergonha", "sozinho", "sozinha",
    "solidao", "solidão", "desespero", "vazio", "desanimado", "desanimada", "briga",
    "conflito", "prova", "reprovar", "demissao", "demissão", "divida", "dívida", "dor",
}
_PT_RISK = {
    "explodir", "matar", "morrer", "suicidio", "suicídio", "me machucar", "automutil",
    "nao aguento", "não aguento", "desaparecer", "acabar com tudo", "sem saida", "sem saída",
}

_THEME_SUBTOPIC_RULES: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "trabalho": [
        ("Sobrecarga e prazos", "Menções a excesso de demandas, pressão por metas ou prazos.", ("prazo", "meta", "chefe", "cobranca", "cobrança", "hora extra", "sobrecarga", "reuniao", "reunião")),
        ("Esgotamento profissional", "Sinais de cansaço extremo ou desgaste ligado à rotina laboral.", ("exaust", "burnout", "esgot", "cansad", "cansac", "trabalho")),
        ("Reconhecimento e carreira", "Reflexões sobre crescimento, feedback ou realizações no trabalho.", ("elogio", "promoc", "promov", "salario", "salário", "carreira", "projeto", "conquista")),
    ],
    "familia": [
        ("Conflito e tensão familiar", "Atritos, cobranças ou discussões no convívio familiar.", ("briga", "discuss", "pai", "mae", "mãe", "irmao", "irmão", "filho", "casa", "cobranca")),
        ("Saudade e vínculo afetivo", "Relatos de apoio, acolhimento ou saudade entre familiares.", ("saudade", "abraco", "abraço", "apoio", "familia", "família", "junto", "carinho")),
    ],
    "relacionamentos": [
        ("Impulsos e conflito interpessoal", "Reações de raiva, frustração intensa ou conflito com outra pessoa.", ("raiva", "explodir", "briga", "ciume", "ciúme", "termino", "término", "distanci", "irritad")),
        ("Afeto e reciprocidade", "Vivências de alegria, conexão, amizade ou cuidado mútuo.", ("feliz", "amor", "namor", "amigo", "amiga", "carinho", "acolh", "junto", "convers")),
    ],
    "estudos": [
        ("Ansiedade com provas e notas", "Preocupação, medo ou desgaste ligados a exames e entregas acadêmicas.", ("prova", "exame", "nota", "faculdade", "escola", "tcc", "reprovar", "estudar", "materia", "matéria")),
        ("Progresso e aprendizado", "Senso de evolução, foco ou conclusão de tarefas acadêmicas.", ("aprendi", "passei", "consegui", "estudo", "livro", "aula", "pesquisa")),
    ],
    "saude_sono": [
        ("Insônia e privação de sono", "Dificuldade para dormir, despertares ou cansaço ao acordar.", ("insonia", "insônia", "dormir", "sono", "madrugada", "pesadelo", "acord")),
        ("Sintomas físicos e fadiga", "Mal-estar corporal, aperto no peito, dores ou falta de energia.", ("peito", "dor", "cabeca", "cabeça", "corpo", "cans", "remedio", "remédio", "medico", "médico", "terapia")),
    ],
    "financas": [
        ("Preocupação financeira", "Insegurança com contas, dívidas, orçamento ou renda.", ("divida", "dívida", "boleto", "conta", "dinheiro", "pagar", "aluguel", "gasto", "caro")),
        ("Organização e estabilidade", "Planejamento financeiro ou alívio em relação a gastos.", ("economi", "poup", "renda", "comprei", "salario", "salário")),
    ],
    "luto": [
        ("Luto e dor da perda", "Sofrimento profundo por ausência, perda, choro ou aperto emocional.", ("luto", "perda", "morreu", "falec", "chorei", "choro", "aperto", "saudade", "ausencia", "ausência")),
        ("Elaboração emocional e sobrecarga", "Abalo intenso frente a frustrações ou dias emocionalmente pesados.", ("pessimo", "péssimo", "triste", "vazio", "pesado", "dificil", "difícil", "nao aguento")),
    ],
    "autoestima": [
        ("Autocrítica e insegurança", "Dúvidas sobre o próprio valor, culpa ou sentimento de incapacidade.", ("culpa", "incapaz", "feio", "inutil", "inútil", "vergonha", "compare", "erro", "fracass")),
        ("Autoconfiança e autovalorização", "Reconhecimento das próprias conquistas e limites saudáveis.", ("orgulho", "consegui", "capaz", "limites", "merec", "cuidei")),
    ],
    "outros_indeterminado": [
        ("Vivência cotidiana", "Registro geral de humor, rotina ou percepção do dia.", ()),
    ],
}

_THEME_DEFAULT_SUBTOPIC: dict[str, tuple[str, str]] = {
    "trabalho": ("Vivências no trabalho", "Aspectos emocionais e rotina profissional relatados no diário."),
    "familia": ("Convivência familiar", "Dinâmicas, afetos e tensões no ambiente familiar."),
    "relacionamentos": ("Vínculos e relações", "Experiências interpessoais e reações afetivas com outras pessoas."),
    "estudos": ("Rotina e desempenho acadêmico", "Demandas de estudo, avaliações e aprendizado."),
    "saude_sono": ("Saúde, corpo e sono", "Percepções sobre bem-estar físico, energia e descanso."),
    "financas": ("Questões financeiras", "Impacto do orçamento, gastos ou estabilidade material."),
    "luto": ("Sofrimento, perda e abatimento", "Momentos de choro, tristeza intensa, perda ou desgaste agudo."),
    "autoestima": ("Autoimagem e valor próprio", "Percepções sobre capacidade pessoal, culpa ou confiança."),
    "outros_indeterminado": ("Contexto emocional geral", "Relato aberto sem macro-tema predominante único."),
}


def _to_macro_enum(raw_theme: str) -> MacroTema:
    try:
        return MacroTema(raw_theme)
    except ValueError:
        return MacroTema.OUTROS_INDETERMINADO


def _map_emotion_to_sentimento(primary_emotion: str | None, polarity: float) -> Sentimento:
    mapping = {
        "alegria": Sentimento.ALEGRIA,
        "calma": Sentimento.CALMA,
        "afeto": Sentimento.ALEGRIA,
        "esperanca": Sentimento.ALEGRIA,
        "tristeza": Sentimento.TRISTEZA,
        "raiva": Sentimento.RAIVA,
        "medo": Sentimento.MEDO,
        "ansiedade": Sentimento.PREOCUPACAO,
        "nojinho": Sentimento.FRUSTRACAO,
        "tedio": Sentimento.FRUSTRACAO,
        "vergonha": Sentimento.FRUSTRACAO,
        "inveja": Sentimento.FRUSTRACAO,
    }
    if primary_emotion and primary_emotion in mapping:
        return mapping[primary_emotion]
    if polarity >= 0.25:
        return Sentimento.ALEGRIA
    if polarity <= -0.25:
        return Sentimento.TRISTEZA
    return Sentimento.NAO_IDENTIFICADO


def _compute_hybrid_polarity(text: str, primary_emotion: str | None, is_risk: bool) -> tuple[float, float]:
    """Combina VADER oficial com sinais léxicos em PT-BR e emoção clínica quando VADER for neutro."""
    vader = analyze_polarity(text)
    tokens = re.findall(r"[\wà-úÀ-Ú]+", text.lower())
    pos_hits = sum(1 for tok in tokens if tok in _PT_POSITIVE)
    neg_hits = sum(1 for tok in tokens if tok in _PT_NEGATIVE)

    score = vader.score
    if abs(score) < 0.08:
        lex_diff = pos_hits - neg_hits
        if lex_diff > 0:
            score = min(0.85, 0.35 + 0.18 * lex_diff)
        elif lex_diff < 0:
            score = max(-0.9, -0.35 - 0.18 * abs(lex_diff))
        elif primary_emotion in {"alegria", "calma", "afeto", "esperanca"}:
            score = 0.62
        elif primary_emotion in {"tristeza", "raiva", "medo", "ansiedade", "nojinho", "vergonha"}:
            score = -0.62
    if is_risk and score > -0.45:
        score = min(score, -0.65)
    return round(max(-1.0, min(1.0, score)), 4), round(vader.score, 4)


def _split_clauses_with_spans(text: str) -> list[tuple[str, int, int]]:
    clauses: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[^.!?\n;]+(?:[.!?\n;]+)?", text):
        raw = match.group(0)
        if not raw.strip():
            continue
        lead = len(raw) - len(raw.lstrip())
        trail = len(raw) - len(raw.rstrip())
        start = match.start() + lead
        end = match.end() - trail
        if end > start:
            clauses.append((text[start:end], start, end))
    if not clauses and text.strip():
        s = len(text) - len(text.lstrip())
        e = len(text.rstrip())
        clauses.append((text[s:e], s, e))
    return clauses


def _match_audio_window(
    quote_text: str, audio_segments: list[dict[str, Any]] | None
) -> tuple[float | None, float | None]:
    if not audio_segments:
        return None, None
    q_words = set(re.findall(r"\w+", quote_text.lower()))
    for seg in audio_segments:
        seg_text = str(seg.get("text", "")).lower()
        seg_words = set(re.findall(r"\w+", seg_text))
        if q_words and seg_words and len(q_words & seg_words) >= max(1, min(3, len(q_words) // 2)):
            return seg.get("start"), seg.get("end")
    return None, None


def _detect_subtopics_structural(
    macro_tema: str,
    clauses: list[tuple[str, int, int]],
    audio_segments: list[dict[str, Any]] | None = None,
) -> list[SubTemaItem]:
    rules = _THEME_SUBTOPIC_RULES.get(macro_tema, _THEME_SUBTOPIC_RULES["outros_indeterminado"])
    found: dict[str, tuple[str, list[EvidenceSpan]]] = {}

    for clause_text, start, end in clauses:
        lowered = clause_text.lower()
        matched_rule = None
        for title, desc, keywords in rules:
            if any(kw in lowered for kw in keywords):
                matched_rule = (title, desc)
                break
        if not matched_rule:
            default_title, default_desc = _THEME_DEFAULT_SUBTOPIC.get(
                macro_tema,
                ("Contexto emocional geral", "Relato aberto sem macro-tema predominante único."),
            )
            matched_rule = (default_title, default_desc)

        title, desc = matched_rule
        a_start, a_end = _match_audio_window(clause_text, audio_segments)
        span = EvidenceSpan(
            quote_text=clause_text[:500],
            start_char=start,
            end_char=min(end, start + 500),
            audio_start_sec=a_start,
            audio_end_sec=a_end,
        )
        if title not in found:
            found[title] = (desc, [span])
        elif len(found[title][1]) < 3:
            found[title][1].append(span)

    return [
        SubTemaItem(nome=name, descricao=desc, evidencias=spans)
        for name, (desc, spans) in list(found.items())[:3]
    ]


def _detect_ollama_model(host: str, preferred: str | None) -> str | None:
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{host.rstrip('/')}/api/tags")
            if resp.status_code != 200:
                return None
            models = [str(m.get("name", "")) for m in resp.json().get("models", []) if m.get("name")]
    except (httpx.HTTPError, ValueError):
        return None
    if not models:
        return None
    if preferred and any(m == preferred or m.startswith(f"{preferred}:") for m in models):
        return preferred
    default_model = Settings().model
    if any(m == default_model or m.startswith(f"{default_model}:") for m in models):
        return default_model
    return models[0]


def _entry_uuid(raw_id: str) -> UUID:
    try:
        return UUID(str(raw_id))
    except ValueError:
        return uuid5(NAMESPACE_URL, f"diario-entry:{raw_id}")


def _parse_datetime(raw: Any) -> datetime:
    if isinstance(raw, (int, float)):
        ts = float(raw) / 1000.0 if float(raw) > 1e11 else float(raw)
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(raw, str) and raw.strip():
        try:
            dt = datetime.fromisoformat(raw)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def _modalidade(raw: str | None) -> str:
    return "audio" if raw == "audio" else "texto"


def _resolve_macro_theme(dist: Any) -> tuple[str, float]:
    # Preserve the predictor's abstention; the UI must show the class the MLP accepted.
    return str(dist.primary_theme), float(dist.confidence)


def _analyze_batch(payload: dict[str, Any]) -> dict[str, Any]:
    from models.predictor import ClinicalThemePredictor

    patient_id = str(payload.get("patient_id") or "PACIENTE")
    entries = payload.get("entries") or []
    use_ollama = bool(payload.get("use_ollama", False))
    requested_model = payload.get("model_name")
    max_subtemas = int(payload.get("max_subtemas") or 24)

    predictor = ClinicalThemePredictor()
    settings = Settings()
    selected_ollama_model = (
        _detect_ollama_model(settings.host, requested_model) if use_ollama else None
    )
    agent1_service = (
        Agent1Service(
            ollama_url=settings.host,
            model_name=selected_ollama_model,
            settings=Settings(
                model=selected_ollama_model,
                host=settings.host,
                timeout_seconds=max(90, int(payload.get("timeout_seconds") or 120)),
            ),
        )
        if selected_ollama_model
        else None
    )

    analyzed_entries: list[dict[str, Any]] = []
    wheel_inputs: list[Agent1Output] = []

    for raw in entries:
        entry_id = str(raw["id"])
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        created_dt = _parse_datetime(raw.get("created_at"))
        modal = _modalidade(raw.get("input_type"))
        primary_emotion = raw.get("primary_emotion")
        is_risk = bool(raw.get("is_risk_emotion"))
        audio_segments = raw.get("audio_segments")

        dist = predictor.predict_text(text)
        breakdown = predictor.destrinchar_diario(text)
        macro_str, macro_conf = _resolve_macro_theme(dist)

        agent1_out: Agent1Output | None = None
        analysis_source = "theme_mlp_primary_v1+estrutural"

        if agent1_service is not None:
            try:
                agent1_out = agent1_service.process(
                    patient_id=patient_id,
                    text=text,
                    macro_tema=macro_str,
                    confidence=macro_conf,
                    modalidade=modal,
                    audio_segments=audio_segments,
                )
                analysis_source = f"theme_mlp_primary_v1+agent1_ollama:{selected_ollama_model}"
            except (httpx.HTTPError, ValueError, RuntimeError):
                agent1_out = None

        if agent1_out is None:
            clauses = _split_clauses_with_spans(text)
            polarity_score, vader_raw = _compute_hybrid_polarity(text, primary_emotion, is_risk)
            sentimento = _map_emotion_to_sentimento(primary_emotion, polarity_score)
            subtemas = _detect_subtopics_structural(macro_str, clauses, audio_segments)
            lower_text = text.lower()
            has_risk_phrase = is_risk or any(kw in lower_text for kw in _PT_RISK)
            risco = IndicioRisco.PRESENTE if has_risk_phrase else IndicioRisco.NAO_IDENTIFICADO
            vader_pol = analyze_polarity(text)
            val_metrics = validate_polarity(sentimento, vader_pol)
            if vader_raw == 0.0 and val_metrics.nlp_score == 0.0:
                val_label = "POSITIVO" if polarity_score > 0.1 else ("NEGATIVO" if polarity_score < -0.1 else "NEUTRO")
                val_metrics = val_metrics.model_copy(
                    update={"nlp_polaridade": val_label, "nlp_score": polarity_score}
                )
            agent1_out = Agent1Output(
                entry_id=_entry_uuid(entry_id),
                patient_id=patient_id,
                created_at=created_dt,
                macro_tema_validado=_to_macro_enum(macro_str),
                confianca_macro_tema=round(max(0.0, min(1.0, macro_conf)), 4),
                subtemas=subtemas,
                sentimento_predominante=sentimento,
                score_polaridade=polarity_score,
                indicio_textual_risco=risco,
                modalidade=modal,
                validation=val_metrics,
            )

        agent1_out = agent1_out.model_copy(update={"entry_id": _entry_uuid(entry_id), "created_at": created_dt})
        wheel_inputs.append(agent1_out)
        analyzed_entries.append(
            {
                "entry_id": entry_id,
                "macro_tema": agent1_out.macro_tema_validado.value,
                "macro_confidence": float(agent1_out.confianca_macro_tema),
                "theme_percentages": dist.percentages,
                "theme_is_fallback": bool(dist.is_fallback),
                "segments": [
                    {
                        "text": seg.quote,
                        "theme": seg.theme,
                        "confidence": seg.confidence,
                        "start_char": seg.start_char,
                        "end_char": seg.end_char,
                    }
                    for seg in breakdown.segments
                ],
                "polarity_score": float(agent1_out.score_polaridade),
                "analysis_source": analysis_source,
                "agent1": agent1_out.model_dump(mode="json"),
            }
        )

    wheel = SubtopicWheelTracker(max_total_subtemas=max_subtemas).build_wheel(
        wheel_inputs,
        patient_id=patient_id,
        periodo=str(payload.get("periodo") or "Período selecionado"),
    )
    return {"analyzed_entries": analyzed_entries, "wheel": wheel.to_dict()}


def _build_wheel(payload: dict[str, Any]) -> dict[str, Any]:
    patient_id = str(payload.get("patient_id") or "PACIENTE")
    max_subtemas = int(payload.get("max_subtemas") or 24)
    current_outputs = [Agent1Output.model_validate(item) for item in (payload.get("current_outputs") or [])]
    previous_outputs = [Agent1Output.model_validate(item) for item in (payload.get("previous_outputs") or [])]

    tracker = SubtopicWheelTracker(max_total_subtemas=max_subtemas)
    wheel = tracker.build_wheel(
        current_outputs,
        patient_id=patient_id,
        periodo=str(payload.get("periodo") or "Período atual"),
    )
    longitudinal = tracker.compare_periods(
        current_outputs,
        previous_outputs,
        patient_id=patient_id,
        current_label=str(payload.get("periodo") or "Período atual"),
        previous_label=str(payload.get("previous_label") or "Período anterior"),
    )
    return {
        "wheel": wheel.to_dict(),
        "longitudinal": asdict(longitudinal),
    }


def _rag_query(payload: dict[str, Any]) -> dict[str, Any]:
    raw_pid = str(payload.get("patient_id") or "PACIENTE")
    safe_pid = re.sub(r"[^A-Za-z0-9_-]", "_", raw_pid)[:80] or "PACIENTE"
    question = str(payload.get("question") or "").strip()
    mode = "ollama" if payload.get("generation_mode") == "ollama" else "extractive"
    top_k = max(1, min(8, int(payload.get("top_k") or 4)))
    entries = payload.get("entries") or []

    with tempfile.TemporaryDirectory() as tmpdir:
        store = DiaryStore(os.path.join(tmpdir, "rag.sqlite"))
        for idx, raw in enumerate(entries):
            text = str(raw.get("text") or "").strip()
            if not text:
                continue
            rec_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(raw.get("id") or idx))[:80]
            theme = raw.get("macro_tema")
            pred = (
                ThemePrediction(status="ok", primary_theme=str(theme), model_version="clinical_mlp_v1")
                if theme
                else ThemePrediction(status="not_requested")
            )
            store.save(
                DiaryRecord(
                    record_id=rec_id,
                    patient_id=safe_pid,
                    recorded_at=_parse_datetime(raw.get("created_at")),
                    original_text=text[:19500],
                    source_title=f"Diário ({raw.get('input_type') or 'texto'})",
                    classification=pred,
                    synthetic=True,
                )
            )

        retriever = Retriever(backend="bm25")
        generator = None
        if mode == "ollama":
            settings = Settings()
            model_name = _detect_ollama_model(settings.host, payload.get("model_name")) or settings.model
            generator = OllamaGenerator(model=model_name, host=settings.host, timeout=120)

        service = CopilotService(store=store, retriever=retriever, generator=generator)
        ans = service.answer(
            Query(patient_id=safe_pid, question=question),
            generation_mode=mode,
            top_k=top_k,
        )
        return ans.model_dump(mode="json")


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze-batch"
    raw_in = sys.stdin.read().strip()
    payload = json.loads(raw_in) if raw_in else {}

    if cmd == "analyze-batch":
        result = _analyze_batch(payload)
    elif cmd == "build-wheel":
        result = _build_wheel(payload)
    elif cmd == "rag-query":
        result = _rag_query(payload)
    else:
        raise ValueError(f"Comando desconhecido: {cmd}")

    sys.stdout.write(json.dumps(result, ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
