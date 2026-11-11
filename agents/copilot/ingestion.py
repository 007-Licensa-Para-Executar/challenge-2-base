"""Adaptador de classificação que conserva o original mesmo em falha operacional."""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from typing import Any

from .contracts import DiaryRecord, ThemePrediction


def _raised_while_unpickling(error: BaseException) -> bool:
    tb = error.__traceback__
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename.replace("\\", "/")
        if filename.endswith("/pickle.py") or "/joblib/" in filename:
            return True
        tb = tb.tb_next
    return False


def _model_version(model_path: Path, vectorizer_path: Path) -> str:
    digest = hashlib.sha256()
    for path in (model_path, vectorizer_path):
        # Hashes of hashes avoid ambiguous concatenation while not storing model bytes.
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return "sha256:" + digest.hexdigest()


def classify_record(
    record: DiaryRecord,
    predictor: Any | None = None,
    model_path: str | Path | None = None,
    vectorizer_path: str | Path | None = None,
) -> DiaryRecord:
    """Solicita classificação; para não solicitá-la, persista o registro diretamente.

    O módulo do preditor é importado apenas quando necessário. A ausência dos
    artefatos é um erro de classificação explícito, não uma categoria temática.
    """
    model_version = None
    try:
        if predictor is None:
            from models.predictor import (
                DEFAULT_MODEL_PATH,
                DEFAULT_VECTORIZER_PATH,
                ClinicalThemePredictor,
            )

            weights = Path(model_path or DEFAULT_MODEL_PATH)
            vectorizer = Path(vectorizer_path or DEFAULT_VECTORIZER_PATH)
            predictor = ClinicalThemePredictor(model_path=weights, vectorizer_path=vectorizer)
            model_version = _model_version(weights, vectorizer)
        elif model_path is not None and vectorizer_path is not None:
            model_version = _model_version(Path(model_path), Path(vectorizer_path))
        result = predictor.predict_text(record.original_text)
        from models.torch_mlp import THEME_CLASSES

        if result.primary_theme not in THEME_CLASSES or (
            result.candidate_theme is not None and result.candidate_theme not in THEME_CLASSES
        ):
            raise ValueError("Categoria fora da taxonomia temática")
        classification = ThemePrediction(
            status="ok",
            primary_theme=result.primary_theme,
            candidate_theme=result.candidate_theme,
            candidate_score=result.confidence,
            abstention_reason=result.abstention_reason,
            model_version=model_version,
        )
    except FileNotFoundError:
        classification = ThemePrediction(
            status="error", error_code="classification_model_unavailable"
        )
    except ModuleNotFoundError as error:
        if not _raised_while_unpickling(error):
            raise
        classification = ThemePrediction(
            status="error", error_code="classification_failed", model_version=model_version
        )
    except (ValueError, TypeError, AttributeError):
        classification = ThemePrediction(
            status="error", error_code="classification_invalid_output", model_version=model_version
        )
    except (OSError, RuntimeError, EOFError, pickle.UnpicklingError):
        classification = ThemePrediction(
            status="error", error_code="classification_failed", model_version=model_version
        )
    return record.model_copy(update={"classification": classification})
