"""Orquestração do estado global do jogo (update, render e inputs)."""

from player   import Player
from obstacle import ObstacleManager
from level    import LevelManager
from renderer import Renderer
from hud      import HUD
from collision import circle_aabb_collision
from constants import PLAYER_RADIUS


def _entry_audio_module():
    """Áudio definido na `main.py`. Com `python main.py` o runnable é `__main__`, não `main`.

    Importar `main` aqui pode carregar ``main.py`` de novo (duplicação) ou ciclo de imports.
    """
    import sys

    root = sys.modules.get("__main__")
    if root is not None and callable(getattr(root, "start_bg_music", None)):
        return root
    import main as mod

    return mod


class GameState:
    """Coordena player, obstáculos, fases, HUD e renderer."""

    def __init__(self):
        self.renderer = Renderer()
        self.renderer.load_phase_textures()
        self.renderer.load_player_textures()

        self.player   = Player()
        self.obstacles = ObstacleManager()
        self.level    = LevelManager()
        self.hud      = HUD(self.renderer)

        self.elapsed  = 0.0
        self.state    = "running"   # "running" | "game_over" | "victory"

    # ------------------------------------------------------------------ #

    def update(self, dt: float):
        """Atualiza simulação do frame atual usando delta time."""
        if self.state != "running":
            return

        self.elapsed += dt
        self.level.update(self.elapsed)

        # Verifica vitória (completou todas as fases)
        if self.level.is_complete(self.elapsed):
            self.state = "victory"
            _entry_audio_module().stop_bg_music()
            return

        speed    = self.level.scroll_speed
        interval = self.level.spawn_interval
        phase    = self.level.phase

        self.renderer.update_scroll(dt, speed)
        self.player.update(dt)
        self.obstacles.update(dt, speed, interval, phase)

        self._check_collisions()

    def _check_collisions(self):
        """Processa colisão player-obstáculo e transição para game over."""
        for ob in self.obstacles.active_obstacles():
            if circle_aabb_collision(self.player.position, PLAYER_RADIUS, ob.aabb):
                self.player.take_hit()
                if self.player.lives <= 0:
                    self.state = "game_over"
                    _entry_audio_module().stop_bg_music()
                break

    # ------------------------------------------------------------------ #

    def render(self):
        """Desenha mundo, player e HUD conforme fase/estado atual."""
        phase = self.level.phase

        self.renderer.draw_background(phase)

        for ob in self.obstacles.active_obstacles():
            self.renderer.draw_obstacle(ob, phase)
        
        self.renderer.draw_ground(phase)
        self.renderer.draw_player(self.player, phase)

        self.hud.render(self.elapsed, self.player.lives, phase, self.state)

    # ------------------------------------------------------------------ #

    def on_jump(self):
        """Input de pulo (ativo somente durante gameplay)."""
        if self.state == "running":
            self.player.jump()

    def on_restart(self):
        """Restaura todos os subsistemas para início de partida."""
        self.elapsed = 0.0
        self.state   = "running"
        self.player.reset()
        self.obstacles.reset()
        self.level    = LevelManager()
        self.hud.reset()
        # Reinicia scroll visual
        self.renderer._bg_scroll = 0.0
        _entry_audio_module().start_bg_music()
