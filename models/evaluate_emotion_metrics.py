"""Avaliação aprofundada da rede neural de emoções e taxonomia Divertidamente.

Executa duas baterias de testes:
1. Métricas Estatísticas Formais no conjunto de teste independente (GoEmotions PT-BR, 5.357 amostras):
   - ROC-AUC Macro e Micro
   - F1-Score Multirrótulo (Macro e Micro)
   - Acurácia e F1 Macro da emoção dominante
   - Métricas por classe (Precisão, Recall, F1, Limiar, Suporte)
   - Matriz de confusão (7x7 Ekman)
2. Benchmark Clínico de Diário de Pacientes (Golden Suite):
   - Taxa de Inversão de Valência (Valence Safety)
   - Recall de Risco Clínico (Risk Recall)
   - Aderência à Taxonomia Divertidamente (15 sub-sentimentos + símbolos)
   - Robustez a Acentos e Gírias (Accent Invariance)
   - Latência média de inferência (ms)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from models.emotion_net import EKMAN_LABELS, EmotionPipeline
from models.emotion_predictor import EmotionDiaryPredictor
from models.emotion_taxonomy import DIVERTIDAMENTE_EMOTIONS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Casos clínicos de benchmark com expectativa de emoção primária, sub-emoção e risco
CLINICAL_BENCHMARK_CASES = [
    # --- MEDO (Roxo) ---
    {
        "id": "medo_01",
        "categoria": "Ansiedade / Prova",
        "text": "Hoje vou ter prova, que dia pessimo",
        "expected_emotion": "medo",
        "expected_sub_emotion": "ansiedade",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "medo_02",
        "categoria": "Pânico Agudo",
        "text": "Meu coração disparou do nada, falta de ar horrível, acho que vou morrer socorro",
        "expected_emotion": "medo",
        "expected_sub_emotion": "panico",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "medo_03",
        "categoria": "Insegurança",
        "text": "Me sinto completamente insegura e vulnerável com esse novo tratamento",
        "expected_emotion": "medo",
        "expected_sub_emotion": "inseguranca",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "medo_04",
        "categoria": "Ansiedade Generalizada",
        "text": "Não consigo parar de pensar no pior, uma angústia e insônia que não me deixam em paz",
        "expected_emotion": "medo",
        "expected_sub_emotion": "ansiedade",
        "expected_risk": True,
        "is_negative": True,
    },
    # --- RAIVA (Vermelho) ---
    {
        "id": "raiva_01",
        "categoria": "Fúria / Agressividade",
        "text": "quero explodir o cachorro do jonas",
        "expected_emotion": "raiva",
        "expected_sub_emotion": "furia",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "raiva_02",
        "categoria": "Indignação",
        "text": "Que absurdo e desrespeito com que me trataram na consulta, uma injustiça inaceitável!",
        "expected_emotion": "raiva",
        "expected_sub_emotion": "indignacao",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "raiva_03",
        "categoria": "Irritação Cotidiana",
        "text": "Estou muito irritado com o trânsito e o atraso dos remédios, saco cheio de tudo",
        "expected_emotion": "raiva",
        "expected_sub_emotion": "irritacao",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "raiva_04",
        "categoria": "Fúria Extrema",
        "text": "Estou com um ódio mortal, vontade de quebrar tudo que vejo pela frente",
        "expected_emotion": "raiva",
        "expected_sub_emotion": "furia",
        "expected_risk": True,
        "is_negative": True,
    },
    # --- TRISTEZA (Azul) ---
    {
        "id": "tristeza_01",
        "categoria": "Desânimo / Depressão",
        "text": "Não tenho ânimo pra nada hoje, passei o dia todo deitado sem forças",
        "expected_emotion": "tristeza",
        "expected_sub_emotion": "desanimo",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "tristeza_02",
        "categoria": "Solidão / Vazio",
        "text": "Sinto um vazio enorme no peito, parece que ninguém se importa comigo, abandono total",
        "expected_emotion": "tristeza",
        "expected_sub_emotion": "luto",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "tristeza_03",
        "categoria": "Luto / Perda",
        "text": "Chorei a tarde inteira de saudade da minha avó que faleceu",
        "expected_emotion": "tristeza",
        "expected_sub_emotion": "luto",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "tristeza_04",
        "categoria": "Ideação / Desespero",
        "text": "Não aguento mais esse sofrimento, perdi a esperança, queria sumir de vez",
        "expected_emotion": "tristeza",
        "expected_sub_emotion": "desanimo",
        "expected_risk": True,
        "is_negative": True,
    },
    # --- NOJINHO (Verde) ---
    {
        "id": "nojo_01",
        "categoria": "Aversão Somática",
        "text": "Senti uma náusea horrível com o cheiro da comida estragada no hospital",
        "expected_emotion": "nojinho",
        "expected_sub_emotion": "aversao",
        "expected_risk": False,
        "is_negative": True,
    },
    {
        "id": "nojo_02",
        "categoria": "Desprezo Moral",
        "text": "Que atitude asquerosa e hipócrita desse colega, sinto verdadeiro asco",
        "expected_emotion": "nojinho",
        "expected_sub_emotion": "desprezo",
        "expected_risk": False,
        "is_negative": True,
    },
    {
        "id": "nojo_03",
        "categoria": "Desconforto",
        "text": "Ambiente sujo e desagradável, me causou um desconforto tremendo",
        "expected_emotion": "nojinho",
        "expected_sub_emotion": "desconforto",
        "expected_risk": False,
        "is_negative": True,
    },
    # --- ALEGRIA (Amarelo) ---
    {
        "id": "alegria_01",
        "categoria": "Entusiasmo",
        "text": "Estou muito feliz e radiante hoje, tudo deu certo no meu trabalho!",
        "expected_emotion": "alegria",
        "expected_sub_emotion": "entusiasmo",
        "expected_risk": False,
        "is_negative": False,
    },
    {
        "id": "alegria_02",
        "categoria": "Gratidão",
        "text": "Quero agradecer do fundo do coração pelo apoio de toda a equipe médica, sou muito grato",
        "expected_emotion": "alegria",
        "expected_sub_emotion": "gratidao",
        "expected_risk": False,
        "is_negative": False,
    },
    {
        "id": "alegria_03",
        "categoria": "Otimismo",
        "text": "Estou com muita esperança de melhora nos exames, confiante no futuro",
        "expected_emotion": "alegria",
        "expected_sub_emotion": "otimismo",
        "expected_risk": False,
        "is_negative": False,
    },
    {
        "id": "alegria_04",
        "categoria": "Celebração",
        "text": "Recebi alta hoje! Que alívio maravilhoso e sensação de vitória!",
        "expected_emotion": "alegria",
        "expected_sub_emotion": "otimismo",
        "expected_risk": False,
        "is_negative": False,
    },
    # --- EQUILÍBRIO / NEUTRO (Cinza / Balança) ---
    {
        "id": "neutro_01",
        "categoria": "Rotina Clínica",
        "text": "Acordei às 7h, tomei a medicação prescrita e fiz uma caminhada leve",
        "expected_emotion": "neutro",
        "expected_sub_emotion": "equilibrio",
        "expected_risk": False,
        "is_negative": False,
    },
    {
        "id": "neutro_02",
        "categoria": "Constatação Objetiva",
        "text": "Hoje o dia correu normal, sem alterações nos sintomas",
        "expected_emotion": "neutro",
        "expected_sub_emotion": "equilibrio",
        "expected_risk": False,
        "is_negative": False,
    },
    # --- CASOS DE ROBUSTEZ A ACENTOS E GÍRIAS ---
    {
        "id": "robustez_01",
        "categoria": "Sem acento - Péssimo",
        "text": "hoje meu dia foi pessimo e to muito mal",
        "expected_emotion": "tristeza",
        "expected_sub_emotion": "desanimo",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "robustez_02",
        "categoria": "Gíria / Abreviação",
        "text": "ta osso aguentar essa crise de panico",
        "expected_emotion": "medo",
        "expected_sub_emotion": "panico",
        "expected_risk": True,
        "is_negative": True,
    },
    {
        "id": "robustez_03",
        "categoria": "Fúria sem pontuação",
        "text": "vou quebrar tudo to com muita raiva",
        "expected_emotion": "raiva",
        "expected_sub_emotion": "furia",
        "expected_risk": True,
        "is_negative": True,
    },
]


def run_statistical_evaluation(
    pipeline: EmotionPipeline,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    """Calcula métricas estatísticas e matriz de confusão no teste GoEmotions PT-BR."""
    texts = test_df["text"].fillna("").tolist()
    Y_true = test_df[EKMAN_LABELS].to_numpy()

    probs = pipeline.predict_proba(texts)
    thresholds = pipeline.thresholds_ if hasattr(pipeline, "thresholds_") else getattr(pipeline, "thresholds", np.full(len(EKMAN_LABELS), 0.5))
    Y_pred_multi = (probs >= thresholds).astype(int)

    # ROC-AUC
    roc_macro = roc_auc_score(Y_true, probs, average="macro")
    roc_micro = roc_auc_score(Y_true, probs, average="micro")

    # Multilabel F1
    f1_macro_multi = f1_score(Y_true, Y_pred_multi, average="macro", zero_division=0)
    f1_micro_multi = f1_score(Y_true, Y_pred_multi, average="micro", zero_division=0)

    # Per-class metrics
    per_class = {}
    for i, label in enumerate(EKMAN_LABELS):
        p = precision_score(Y_true[:, i], Y_pred_multi[:, i], zero_division=0)
        r = recall_score(Y_true[:, i], Y_pred_multi[:, i], zero_division=0)
        f = f1_score(Y_true[:, i], Y_pred_multi[:, i], zero_division=0)
        support = int(np.sum(Y_true[:, i]))
        per_class[label] = {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f), 4),
            "threshold": round(float(thresholds[i]), 4),
            "support": support,
        }

    # Primary emotion evaluation
    y_true_primary_idx = np.argmax(Y_true, axis=1)
    y_pred_primary_idx = np.argmax(probs, axis=1)

    y_true_labels = [EKMAN_LABELS[i] for i in y_true_primary_idx]
    y_pred_labels = [EKMAN_LABELS[i] for i in y_pred_primary_idx]

    acc_primary = accuracy_score(y_true_labels, y_pred_labels)
    balanced_acc = balanced_accuracy_score(y_true_labels, y_pred_labels)
    f1_macro_primary = f1_score(y_true_labels, y_pred_labels, average="macro", zero_division=0)
    f1_weighted_primary = f1_score(
        y_true_labels, y_pred_labels, average="weighted", zero_division=0
    )

    cm = confusion_matrix(y_true_labels, y_pred_labels, labels=EKMAN_LABELS)
    cm_dict = {
        label: {
            EKMAN_LABELS[j]: int(cm[i, j]) for j in range(len(EKMAN_LABELS))
        }
        for i, label in enumerate(EKMAN_LABELS)
    }

    report_dict = classification_report(
        y_true_labels, y_pred_labels, target_names=EKMAN_LABELS, output_dict=True, zero_division=0
    )

    return {
        "test_sample_count": len(test_df),
        "multilabel": {
            "roc_auc_macro": round(float(roc_macro), 4),
            "roc_auc_micro": round(float(roc_micro), 4),
            "f1_macro": round(float(f1_macro_multi), 4),
            "f1_micro": round(float(f1_micro_multi), 4),
            "per_class": per_class,
        },
        "primary_emotion": {
            "accuracy": round(float(acc_primary), 4),
            "balanced_accuracy": round(float(balanced_acc), 4),
            "f1_macro": round(float(f1_macro_primary), 4),
            "f1_weighted": round(float(f1_weighted_primary), 4),
            "confusion_matrix": cm_dict,
            "classification_report": report_dict,
        },
    }


def run_clinical_benchmark(predictor: EmotionDiaryPredictor) -> dict[str, Any]:
    """Executa o benchmark clínico de diários de saúde mental e valida guardrails."""
    results = []
    latencies = []

    negative_cases_tested = 0
    negative_labeled_as_joy = 0

    risk_cases_tested = 0
    risk_cases_detected = 0

    taxonomy_valid_count = 0
    exact_emotion_matches = 0
    exact_sub_matches = 0

    for case in CLINICAL_BENCHMARK_CASES:
        t0 = time.perf_counter()
        pred_res = predictor.predict(case["text"])
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(dt_ms)

        pred_emotion = pred_res.primary_emotion
        pred_sub = pred_res.active_sub_emotion.id if pred_res.active_sub_emotion else ""
        pred_risk = pred_res.is_risk_emotion

        # 1. Valence Safety Check
        if case["is_negative"]:
            negative_cases_tested += 1
            if pred_emotion == "alegria":
                negative_labeled_as_joy += 1

        # 2. Risk Recall Check
        if case["expected_risk"]:
            risk_cases_tested += 1
            if pred_risk:
                risk_cases_detected += 1

        # 3. Taxonomy Check: does active_sub belong to DIVERTIDAMENTE_EMOTIONS?
        valid_taxonomy = False
        for char_data in DIVERTIDAMENTE_EMOTIONS.values():
            for sub in char_data.sub_sentimentos:
                if sub.id == pred_sub:
                    valid_taxonomy = True
                    break
        if valid_taxonomy:
            taxonomy_valid_count += 1

        # 4. Emotion & Sub-emotion Match
        match_emotion = pred_emotion == case["expected_emotion"]
        match_sub = pred_sub == case["expected_sub_emotion"]
        if match_emotion:
            exact_emotion_matches += 1
        if match_sub:
            exact_sub_matches += 1

        results.append(
            {
                "id": case["id"],
                "categoria": case["categoria"],
                "text": case["text"],
                "expected": {
                    "emotion": case["expected_emotion"],
                    "sub_emotion": case["expected_sub_emotion"],
                    "risk": case["expected_risk"],
                },
                "predicted": {
                    "emotion": pred_emotion,
                    "sub_emotion": pred_sub,
                    "character": pred_res.character,
                    "symbol": pred_res.active_sub_emotion.simbolo if pred_res.active_sub_emotion else "⚖️",
                    "risk": pred_risk,
                    "confidence": round(pred_res.confidence, 4),
                },
                "match_emotion": match_emotion,
                "match_sub": match_sub,
                "latency_ms": round(dt_ms, 2),
            }
        )

    valence_inversion_rate = (
        (negative_labeled_as_joy / negative_cases_tested) if negative_cases_tested else 0.0
    )
    valence_safety_rate = 1.0 - valence_inversion_rate
    risk_recall = (risk_cases_detected / risk_cases_tested) if risk_cases_tested else 1.0
    taxonomy_compliance = taxonomy_valid_count / len(CLINICAL_BENCHMARK_CASES)
    emotion_accuracy = exact_emotion_matches / len(CLINICAL_BENCHMARK_CASES)
    sub_accuracy = exact_sub_matches / len(CLINICAL_BENCHMARK_CASES)

    return {
        "total_cases": len(CLINICAL_BENCHMARK_CASES),
        "valence_safety_rate": round(valence_safety_rate, 4),
        "valence_inversion_rate": round(valence_inversion_rate, 4),
        "risk_recall": round(risk_recall, 4),
        "taxonomy_compliance": round(taxonomy_compliance, 4),
        "emotion_accuracy": round(emotion_accuracy, 4),
        "sub_emotion_accuracy": round(sub_accuracy, 4),
        "latency": {
            "mean_ms": round(float(np.mean(latencies)), 2),
            "p95_ms": round(float(np.percentile(latencies, 95)), 2),
            "max_ms": round(float(np.max(latencies)), 2),
        },
        "cases": results,
    }


def log_to_mlflow(
    report: dict[str, Any],
    tracking_uri: str = "sqlite:///mlflow.db",
    experiment_name: str = "diario-emocional-sentimentos",
) -> str | None:
    """Registra as métricas e artefatos de avaliação no MLflow."""
    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name="mlp-numpy-divertidamente-goemotions-ptbr") as run:
            stat = report["statistical_metrics"]
            clin = report["clinical_benchmark"]
            arch = report["model_architecture"]

            mlflow.log_params(
                {
                    "model_type": "NumpyEmotionMLP",
                    "n_features": arch["input_features"],
                    "hidden_units": str(arch["hidden_units"]),
                    "activation": arch["activation"],
                    "dataset": "GoEmotions PT-BR (Multilabel Ekman)",
                    "test_samples": stat["test_sample_count"],
                    "taxonomy": "Divertidamente (5 Cores) + How We Feel (15 Sub-emocoes)",
                    "clinical_guardrails": "Enabled",
                }
            )
            mlflow.log_metrics(
                {
                    "test_roc_auc_macro": stat["multilabel"]["roc_auc_macro"],
                    "test_roc_auc_micro": stat["multilabel"]["roc_auc_micro"],
                    "test_f1_macro_multilabel": stat["multilabel"]["f1_macro"],
                    "test_f1_micro_multilabel": stat["multilabel"]["f1_micro"],
                    "test_primary_accuracy": stat["primary_emotion"]["accuracy"],
                    "test_primary_balanced_acc": stat["primary_emotion"]["balanced_accuracy"],
                    "test_primary_f1_macro": stat["primary_emotion"]["f1_macro"],
                    "test_primary_f1_weighted": stat["primary_emotion"]["f1_weighted"],
                    "clinical_valence_safety_rate": clin["valence_safety_rate"],
                    "clinical_valence_inversion_rate": clin["valence_inversion_rate"],
                    "clinical_risk_recall": clin["risk_recall"],
                    "clinical_taxonomy_compliance": clin["taxonomy_compliance"],
                    "clinical_emotion_accuracy": clin["emotion_accuracy"],
                    "clinical_sub_emotion_accuracy": clin["sub_emotion_accuracy"],
                    "clinical_latency_mean_ms": clin["latency"]["mean_ms"],
                }
            )
            for label, d in stat["multilabel"]["per_class"].items():
                mlflow.log_metric(f"f1_{label}", d["f1"])
                mlflow.log_metric(f"precision_{label}", d["precision"])
                mlflow.log_metric(f"recall_{label}", d["recall"])
                mlflow.log_metric(f"threshold_{label}", d["threshold"])

            for art in ["dist/emotion_evaluation_report.json", "dist/emotion_metrics.json"]:
                if Path(art).exists():
                    mlflow.log_artifact(art)

            return str(run.info.run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Registro no MLflow ignorado ou em fallback: %s", exc)
        return None


def main() -> None:
    model_path = Path("dist/emotion_classifier.joblib")
    test_csv_path = Path("data/goemotions/test.csv")
    out_report_path = Path("dist/emotion_evaluation_report.json")

    logger.info("Carregando pipeline de %s...", model_path)
    pipeline = EmotionPipeline.load(model_path)
    predictor = EmotionDiaryPredictor(model_path=model_path)

    logger.info("Carregando dataset de teste de %s...", test_csv_path)
    test_df = pd.read_csv(test_csv_path)

    logger.info("1. Executando avaliação estatística formal no teste (%d amostras)...", len(test_df))
    stat_metrics = run_statistical_evaluation(pipeline, test_df)

    logger.info("2. Executando Benchmark Clínico de Diários de Pacientes (Golden Suite)...")
    clinical_metrics = run_clinical_benchmark(predictor)

    full_report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_architecture": {
            "input_features": pipeline.n_features,
            "hidden_units": pipeline.hidden_units,
            "activation": pipeline.activation,
            "output_classes": EKMAN_LABELS,
        },
        "statistical_metrics": stat_metrics,
        "clinical_benchmark": clinical_metrics,
    }

    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_report_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)

    logger.info("Relatório completo salvo em %s", out_report_path)

    # Registro no MLflow
    mlflow_run_id = log_to_mlflow(full_report)
    if mlflow_run_id:
        logger.info("Experimento registrado no MLflow com Run ID: %s", mlflow_run_id)

    # Impressão formatada no terminal
    print("\n" + "=" * 70)
    print("📊 BATERIA DE MÉTRICAS DA REDE NEURAL & VALIDAÇÃO CLÍNICA")
    print("=" * 70)
    print("1. MÉTRICAS ESTATÍSTICAS NO CONJUNTO DE TESTE (5.357 AMOSTRAS NÃO VISTAS):")
    print(f"   • ROC-AUC Macro:             {stat_metrics['multilabel']['roc_auc_macro']:.4f}")
    print(f"   • ROC-AUC Micro:             {stat_metrics['multilabel']['roc_auc_micro']:.4f}")
    print(f"   • F1 Macro (Multirrótulo):   {stat_metrics['multilabel']['f1_macro']:.4f}")
    print(f"   • F1 Micro (Multirrótulo):   {stat_metrics['multilabel']['f1_micro']:.4f}")
    print(f"   • Acurácia Emoção Dominante: {stat_metrics['primary_emotion']['accuracy']:.4f}")
    print(f"   • F1 Macro Emoção Dominante: {stat_metrics['primary_emotion']['f1_macro']:.4f}")
    print("-" * 70)
    print(f"{'Classe Ekman':<14} | {'Precisão':<8} | {'Recall':<8} | {'F1':<8} | {'Limiar':<8} | {'Amostras':<8}")
    for label, d in stat_metrics["multilabel"]["per_class"].items():
        print(f"{label:<14} | {d['precision']:<8.4f} | {d['recall']:<8.4f} | {d['f1']:<8.4f} | {d['threshold']:<8.4f} | {d['support']:<8}")
    print("=" * 70)
    print("2. MÉTRICAS DE SEGURANÇA E ADERÊNCIA CLÍNICA (DIÁRIO DO PACIENTE):")
    print(f"   • Valence Safety Rate (Negativos não rotulados como Alegria): {clinical_metrics['valence_safety_rate'] * 100:.1f}%")
    print(f"   • Risk Recall (Sensibilidade a Crise/Ideação/Pânico):          {clinical_metrics['risk_recall'] * 100:.1f}%")
    print(f"   • Taxonomy Compliance (Cores Divertidamente + Símbolos HWFeel):{clinical_metrics['taxonomy_compliance'] * 100:.1f}%")
    print(f"   • Acurácia Emoção Clínica (Benchmark 24 casos):               {clinical_metrics['emotion_accuracy'] * 100:.1f}%")
    print(f"   • Acurácia Sub-emoção Específica:                             {clinical_metrics['sub_emotion_accuracy'] * 100:.1f}%")
    print(f"   • Latência Média de Inferência:                               {clinical_metrics['latency']['mean_ms']:.2f} ms")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
