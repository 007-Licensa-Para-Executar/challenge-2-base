"""CLI para inferência emocional em JSON para integração com front-ends e serviços externos.

Recebe texto via argumento --text ou via stdin e imprime o resultado JSON estruturado
contendo a classificação da rede neural e os metadados do Divertidamente e How We Feel.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from models.emotion_predictor import DEFAULT_EMOTION_MODEL_PATH, EmotionDiaryPredictor


def main() -> None:
    parser = argparse.ArgumentParser(description="Inferência emocional em JSON.")
    parser.add_argument("--text", type=str, default=None, help="Texto do relato a ser analisado.")
    parser.add_argument(
        "--model",
        type=str,
        default=str(DEFAULT_EMOTION_MODEL_PATH),
        help="Caminho do arquivo do modelo treinado.",
    )
    args = parser.parse_args()

    # Se não fornecido via argumento, lê do stdin
    text = args.text
    if text is None:
        text = sys.stdin.read()

    predictor = EmotionDiaryPredictor(model_path=Path(args.model))
    result = predictor.predict(text)
    json_output = json.dumps(result.to_dict(), ensure_ascii=False)
    sys.stdout.buffer.write(json_output.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
