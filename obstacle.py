"""Entidades de obstáculo e gerenciamento de spawn/pool."""

import random
import numpy as np
from constants import (
    OBSTACLE_WIDTH, OBSTACLE_HEIGHT, OBSTACLE_SPAWN_X, OBSTACLE_DESPAWN_X,
    COLLISION_TOLERANCE, GROUND_TOP_Y, OBSTACLE_POOL_SIZE, SPAWN_JITTER,
)


class Obstacle:
    """Obstáculo simples em AABB movendo-se da direita para esquerda."""

    def __init__(self):
        self.position = np.array([OBSTACLE_DESPAWN_X - 1.0, GROUND_TOP_Y], dtype=float)
        self.width    = OBSTACLE_WIDTH
        self.height   = OBSTACLE_HEIGHT
        self.active   = False

    def activate(self, height_var: float = 0.0):
        """Ativa obstáculo reutilizando objeto do pool."""
        self.position = np.array([OBSTACLE_SPAWN_X, GROUND_TOP_Y - height_var], dtype=float)
        self.height   = OBSTACLE_HEIGHT + height_var
        self.active   = True

    def update(self, dt: float, speed: float):
        """Atualiza deslocamento horizontal e desativa ao sair da tela."""
        if not self.active:
            return
        self.position[0] -= speed * dt
        if self.position[0] + self.width < OBSTACLE_DESPAWN_X:
            self.active = False

    @property
    def aabb(self):
        """Retorna caixa de colisão com tolerância para jogabilidade."""
        t  = COLLISION_TOLERANCE
        x0 = self.position[0] + t
        y0 = self.position[1] + t
        x1 = self.position[0] + self.width  - t
        y1 = self.position[1] + self.height - t
        return (x0, y0, x1, y1)


class ObstacleManager:
    """Gerencia pool fixo, timer e regras de spawn por fase."""

    def __init__(self):
        self._pool       = [Obstacle() for _ in range(OBSTACLE_POOL_SIZE)]
        self._spawn_timer = 0.0
        self._phase       = 0

    def update(self, dt: float, speed: float, spawn_interval: float, phase: int):
        """Atualiza obstáculos ativos e agenda novos spawns."""
        self._phase = phase
        for ob in self._pool:
            ob.update(dt, speed)

        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._try_spawn(phase)
            jitter = random.uniform(-SPAWN_JITTER, SPAWN_JITTER)
            self._spawn_timer = spawn_interval + jitter

    def _try_spawn(self, phase: int):
        """Tenta spawnar um obstáculo inativo com variação de altura."""
        # Fase 4+: 15% de chance de pular o spawn (cria gap)
        if phase >= 3 and random.random() < 0.15:
            return
        for ob in self._pool:
            if not ob.active:
                # Variação aleatória de altura do obstáculo
                height_var = random.uniform(0.0, 0.08)
                ob.activate(height_var)
                return

    def active_obstacles(self):
        """Lista somente obstáculos ativos para render/colisão."""
        return [ob for ob in self._pool if ob.active]

    def reset(self):
        """Limpa obstáculos e reinicia timer de spawn."""
        for ob in self._pool:
            ob.active = False
        self._spawn_timer = 0.0
