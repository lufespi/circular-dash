"""Lógica do personagem: física, pulo, vidas e invencibilidade."""

import numpy as np
from constants import (
    PLAYER_X_NDC, PLAYER_GROUND_Y, PLAYER_JUMP_VELOCITY,
    GRAVITY, MAX_LIVES, INVINCIBILITY_DURATION,
)


class Player:
    """Representa o jogador controlado pelo teclado."""

    def __init__(self):
        self.position = np.array([PLAYER_X_NDC, PLAYER_GROUND_Y], dtype=float)
        self.velocity = np.array([0.0, 0.0], dtype=float)
        self.lives     = MAX_LIVES
        self.on_ground = True
        self.inv_timer = 0.0          # tempo restante de invencibilidade
        self.flash_timer = 0.0        # alterna a cada 0.1s
        self.is_flashing = False      # controla visibilidade do flash

    def update(self, dt: float):
        """Integra física vertical e controla estado de invencibilidade."""
        # Física vertical
        self.velocity[1] += GRAVITY * dt
        self.position    += self.velocity * dt

        # Clamp no chão
        if self.position[1] <= PLAYER_GROUND_Y:
            self.position[1] = PLAYER_GROUND_Y
            self.velocity[1] = 0.0
            self.on_ground   = True

        # Invencibilidade + flash
        if self.inv_timer > 0:
            self.inv_timer  -= dt
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.flash_timer = 0.1
                self.is_flashing = not self.is_flashing
            if self.inv_timer <= 0:
                self.inv_timer   = 0.0
                self.is_flashing = False

    def jump(self):
        """Aplica impulso vertical se o player estiver no chão."""
        if self.on_ground:
            self.velocity[1] = PLAYER_JUMP_VELOCITY
            self.on_ground   = False

    def take_hit(self):
        """Consome uma vida e inicia janela de invencibilidade."""
        if self.inv_timer > 0:
            return
        self.lives    -= 1
        self.inv_timer = INVINCIBILITY_DURATION
        self.flash_timer = 0.1
        self.is_flashing = True

    def reset(self):
        """Retorna o player para o estado inicial de partida."""
        self.position    = np.array([PLAYER_X_NDC, PLAYER_GROUND_Y], dtype=float)
        self.velocity    = np.array([0.0, 0.0], dtype=float)
        self.lives       = MAX_LIVES
        self.on_ground   = True
        self.inv_timer   = 0.0
        self.flash_timer = 0.0
        self.is_flashing = False
