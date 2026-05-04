"""Funções utilitárias de colisão usadas no loop de jogo."""

import numpy as np


def circle_aabb_collision(center: np.ndarray, radius: float, aabb: tuple) -> bool: #AABB = CAIXA DE COLISÃO RETANGULAR
    """Teste círculo vs AABB via ponto mais próximo (np.clip)."""
    cx, cy = center # coordenadas do centro do círculo
    x0, y0, x1, y1 = aabb # coordenadas do AABB
    closest = np.array([np.clip(cx, x0, x1), np.clip(cy, y0, y1)]) # ponto mais próximo do AABB
    diff = center - closest # vetor da distância entre o centro do círculo e o ponto mais próximo do AABB
    return float(diff @ diff) < radius * radius # verifica se a distância entre o centro do círculo e o ponto mais próximo do AABB é menor que o raio do círculo
