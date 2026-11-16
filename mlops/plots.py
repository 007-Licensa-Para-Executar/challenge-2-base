"""Figuras de diagnóstico registradas como artefatos do experimento."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_confusion_matrix(cm: list[list[int]], classes: list[str]) -> plt.Figure:
    """Desenha a matriz de confusão com contraste de texto relativo ao maior valor."""
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.matshow(cm, cmap=plt.cm.Blues)
    fig.colorbar(image)

    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=45, ha="left")
    ax.set_yticklabels(classes)

    peak = max((value for row in cm for value in row), default=0)
    cutoff = peak / 2
    for i in range(len(classes)):
        for j in range(len(classes)):
            value = cm[i][j]
            color = "white" if value > cutoff else "black"
            ax.text(j, i, str(value), ha="center", va="center", color=color)

    ax.set_xlabel("Predição do modelo")
    ax.set_ylabel("Rótulo esperado")
    ax.set_title("Matriz de confusão — sentimento", pad=20)
    plt.tight_layout()
    return fig
