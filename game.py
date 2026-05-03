"""Orquestração do estado global do jogo (update, render e inputs)."""

from player   import Player
from obstacle import ObstacleManager
from level    import LevelManager
from renderer import Renderer
from hud      import HUD
from collision import circle_aabb_collision
from constants import PLAYER_RADIUS, TOTAL_GAME_TIME, PLAYER_GROUND_Y, PLAYER_X_NDC


def _entry_audio_module():
    import sys
    root = sys.modules.get("__main__")
    if root is not None and callable(getattr(root, "start_bg_music", None)):
        return root
    import main as mod
    return mod


class GameState:
    """Coordena player, obstáculos, fases, HUD e renderer."""

    def __init__(self):
        self.renderer  = Renderer()
        self.renderer.load_phase_textures()
        self.renderer.load_player_textures()

        self.player    = Player()
        self.obstacles = ObstacleManager()
        self.level     = LevelManager()
        self.hud       = HUD(self.renderer)

        self.elapsed         = 0.0
        self.state           = "running"
        self._finish_x       = 2.5
        self._finish_active  = False   # True a partir de TOTAL_GAME_TIME

    # ------------------------------------------------------------------ #

    def update(self, dt: float):
        if self.state not in ("running", "crossing"):
            return

        self.elapsed += dt
        old_phase = self.level.phase
        self.level.update(self.elapsed)
        new_phase = self.level.phase
        if new_phase != old_phase:
            self.renderer.start_phase_transition(old_phase, new_phase)

        speed    = self.level.scroll_speed
        interval = self.level.spawn_interval
        phase    = self.level.phase

        self.renderer.update_scroll(dt, speed)
        self.renderer.update_transition(dt)
        self.player.update(dt)

        # Spawna a linha de chegada exatamente quando o tempo total acaba
        if not self._finish_active and self.elapsed >= TOTAL_GAME_TIME:
            self._finish_active = True
            self._finish_x = 1.3
            self.state = "crossing"   # jogo continua, só para spawn de obstáculos
            _entry_audio_module().stop_bg_music()

        if self._finish_active:
            self._finish_x -= speed * dt
            # Vitória quando a linha cruza o jogador
            if self._finish_x < PLAYER_X_NDC - 0.10:
                self.state = "victory"
                return

        # Obstáculos só spawnam enquanto ainda não chegou o fim
        self.obstacles.update(dt, speed, interval, phase, self.elapsed, TOTAL_GAME_TIME)

        if self.state == "running":
            self._check_collisions()

    # ------------------------------------------------------------------ #

    def _check_collisions(self):
        """Bloco: topo = pouso seguro; lateral/base = perde vida.
           Espinho: sempre perde vida.
        """
        R   = PLAYER_RADIUS
        py  = float(self.player.position[1])
        px  = float(self.player.position[0])
        vy  = float(self.player.velocity[1])

        on_any_block = False

        for ob in self.obstacles.active_obstacles():
            if ob.kind == 'block':
                top_y = float(ob.position[1]) + ob.height
                x0    = float(ob.position[0])
                x1    = x0 + ob.width

                # Horizontalmente sobre o bloco?
                over_block = (px + R * 0.65 > x0) and (px - R * 0.65 < x1)
                player_bottom = py - R

                if over_block and vy <= 0.05 and (top_y - 0.07) <= player_bottom <= (top_y + 0.03):
                    self.player.set_platform(top_y)
                    on_any_block = True
                    continue

            # Colisão geral
            if not circle_aabb_collision(self.player.position, R, ob.aabb):
                continue

            # Lateral/inferior de bloco ou qualquer toque em espinho
            self.player.take_hit()
            if self.player.lives <= 0:
                self.state = "game_over"
                _entry_audio_module().stop_bg_music()
            break

        # Verifica se saiu do bloco (cair do lado)
        if not on_any_block and self.player.on_ground and abs(py - PLAYER_GROUND_Y) > 0.01:
            still_supported = False
            for ob in self.obstacles.active_obstacles():
                if ob.kind != 'block':
                    continue
                top_y = float(ob.position[1]) + ob.height
                x0    = float(ob.position[0])
                x1    = x0 + ob.width
                if abs(py - R - top_y) < 0.06 and (px + R * 0.5 > x0) and (px - R * 0.5 < x1):
                    still_supported = True
                    break
            if not still_supported:
                self.player.on_ground   = False
                self.player._platform_y = None

    # ------------------------------------------------------------------ #

    def render(self):
        phase = self.level.phase

        self.renderer.draw_background(phase)

        for ob in self.obstacles.active_obstacles():
            self.renderer.draw_obstacle(ob, phase)

        self.renderer.draw_ground(phase)

        if self._finish_active:
            self.renderer.draw_finish_line(self._finish_x)

        self.renderer.draw_player(self.player, phase)

        self.hud.render(self.elapsed, self.player.lives, phase, self.state)

    # ------------------------------------------------------------------ #

    def on_jump(self):
        if self.state in ("running", "crossing"):
            self.player.jump()

    def on_restart(self):
        self.elapsed         = 0.0
        self.state           = "running"
        self._finish_x       = 2.5
        self._finish_active  = False
        self.player.reset()
        self.obstacles.reset()
        self.level           = LevelManager()
        self.hud.reset()
        self.renderer._bg_scroll = 0.0
        _entry_audio_module().start_bg_music()