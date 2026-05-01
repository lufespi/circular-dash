"""Funções utilitárias de colisão usadas no loop de jogo."""

import numpy as np


def circle_aabb_collision(center: np.ndarray, radius: float, aabb: tuple) -> bool:
    """Teste círculo vs AABB via ponto mais próximo (np.clip)."""
    cx, cy = center
    x0, y0, x1, y1 = aabb
    closest = np.array([np.clip(cx, x0, x1), np.clip(cy, y0, y1)])
    diff = center - closest
    return float(diff @ diff) < radius * radius
