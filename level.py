"""Progressão de fase e parâmetros de dificuldade ao longo do tempo."""

from constants import PHASE_TIME_THRESHOLDS, PHASE_DIFFICULTY, TOTAL_GAME_TIME


class LevelManager:
    """Calcula fase atual, velocidade de scroll e intervalo de spawn."""

    def __init__(self):
        self.phase         = 0
        self.scroll_speed, self.spawn_interval = PHASE_DIFFICULTY[0]
        self._prev_phase   = -1

    def update(self, elapsed: float) -> bool:
        """Retorna True se a fase mudou."""
        new_phase = 0
        for i, threshold in enumerate(PHASE_TIME_THRESHOLDS):
            if elapsed >= threshold:
                new_phase = i

        changed = new_phase != self.phase
        if changed:
            self.phase = new_phase
            self.scroll_speed, self.spawn_interval = PHASE_DIFFICULTY[new_phase]
        return changed

    def is_complete(self, elapsed: float) -> bool:
        """Indica se o tempo total da partida foi atingido."""
        return elapsed >= TOTAL_GAME_TIME
