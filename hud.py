"""HUD do jogo: tempo, fase, vidas e mensagens de fim de partida."""

from PIL import Image, ImageDraw, ImageFont
from constants import MAX_LIVES, PHASE_NAMES, WINDOW_WIDTH, WINDOW_HEIGHT, TOTAL_GAME_TIME
import phase_progress
from debug import DEBUG


def _try_font(size: int):
    candidates = [
        "arialbd.ttf", "arial.ttf",
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _text_to_pil(text: str, font, color=(255, 255, 255, 255)):
    """Renderiza texto em PIL Image RGBA, tamanho exato do texto."""
    dummy = Image.new("RGBA", (1, 1))
    bbox  = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + 4
    h = bbox[3] - bbox[1] + 4
    img  = Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((2 - bbox[0], 2 - bbox[1]), text, font=font, fill=color)
    return img


class HUD:
    """Controla cache e renderização de textos/ícones da interface."""

    def __init__(self, renderer):
        self._renderer   = renderer
        self._font_large = _try_font(28)
        self._font_small = _try_font(18)
        self._font_big   = _try_font(48)

        # Cache de texturas
        self._timer_tex  = 0
        self._phase_tex  = 0
        self._debug_tex  = 0
        self._over_tex   = 0
        self._win_tex    = 0

        self._last_timer_str = ""
        self._last_phase     = -1
        self._last_debug_on  = None

    # ------------------------------------------------------------------ #

    def _px_to_ndc_x(self, px: float) -> float:
        return (px / WINDOW_WIDTH) * 2.0 - 1.0

    def _px_to_ndc_y(self, py: float) -> float:
        return 1.0 - (py / WINDOW_HEIGHT) * 2.0

    def _ndc_w(self, px_w: float) -> float:
        return (px_w / WINDOW_WIDTH) * 2.0

    def _ndc_h(self, px_h: float) -> float:
        return (px_h / WINDOW_HEIGHT) * 2.0

    # ------------------------------------------------------------------ #

    def _upload(self, img) -> int:
        return self._renderer.upload_text_texture(img)

    def _release(self, tid: int) -> int:
        if tid:
            self._renderer.delete_texture(tid)
        return 0

    # ------------------------------------------------------------------ #

    def render(self, elapsed: float, lives: int, phase: int, state: str):
        """Desenha todos os elementos visuais do HUD no frame atual."""
        if DEBUG.get("show_timer_text", False):
            self._draw_timer(elapsed)
        elif DEBUG.get("show_phase_progress", True) and state not in ("game_over", "victory"):
            phase_progress.render_progress(self._renderer, elapsed, TOTAL_GAME_TIME,
                                           x_px=12, y_px=12)
        self._draw_phase(phase)
        self._draw_debug_status()
        self._draw_lives(lives)

        if state == "game_over":
            self._draw_game_over()
        elif state == "victory":
            self._draw_victory()

    # ------------------------------------------------------------------ #

    def _draw_timer(self, elapsed: float):
        """Atualiza e desenha cronômetro no canto superior esquerdo."""
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        text = f"{minutes:01d}:{seconds:02d}"
        if text != self._last_timer_str:
            self._timer_tex      = self._release(self._timer_tex)
            img                  = _text_to_pil(text, self._font_large,
                                                color=(255, 255, 255, 230))
            self._timer_tex      = self._upload(img)
            self._last_timer_str = text
            self._tw, self._th   = img.size

        if self._timer_tex:
            x = self._px_to_ndc_x(12)
            y = self._px_to_ndc_y(12 + self._th)
            w = self._ndc_w(self._tw)
            h = self._ndc_h(self._th)
            self._renderer.draw_texture_quad(self._timer_tex, x, y, w, h)

    def _draw_phase(self, phase: int):
        """Atualiza e desenha nome da fase corrente."""
        if phase != self._last_phase:
            self._phase_tex  = self._release(self._phase_tex)
            name = PHASE_NAMES[phase]
            img  = _text_to_pil(name, self._font_small, color=(220, 220, 255, 200))
            self._phase_tex  = self._upload(img)
            self._last_phase = phase
            self._pw, self._ph = img.size

        if self._phase_tex:
            x = self._px_to_ndc_x(12)
            y = self._px_to_ndc_y(12 + 34 + self._ph)
            w = self._ndc_w(self._pw)
            h = self._ndc_h(self._ph)
            self._renderer.draw_texture_quad(self._phase_tex, x, y, w, h)

    def _draw_debug_status(self):
        """Mostra um indicador quando o modo debug de vidas infinitas está ativo."""
        debug_on = DEBUG.get("infinite_lives", False)
        if debug_on != self._last_debug_on:
            self._debug_tex = self._release(self._debug_tex)
            if debug_on:
                img = _text_to_pil("DEBUG = ON", self._font_small, color=(255, 210, 90, 230))
                self._debug_tex = self._upload(img)
                self._dw, self._dh = img.size
            self._last_debug_on = debug_on

        if self._debug_tex:
            x = self._px_to_ndc_x(12)
            y = self._px_to_ndc_y(12 + 34 + self._ph + 3 + self._dh)
            w = self._ndc_w(self._dw)
            h = self._ndc_h(self._dh)
            self._renderer.draw_texture_quad(self._debug_tex, x, y, w, h)

    def _draw_lives(self, lives: int):
        """Desenha ícones de vida no canto superior direito."""
        r       = 0.025
        spacing = 0.075
        cx_base = 0.80
        cy      = 0.88
        for i in range(MAX_LIVES):
            cx = cx_base + i * spacing
            self._renderer.draw_life_icon(cx, cy, r, filled=(i < lives))

    def _draw_game_over(self):
        """Desenha overlay e mensagem de derrota."""
        if not self._over_tex:
            img = _text_to_pil("GAME OVER", self._font_big, color=(220, 50, 50, 240))
            self._over_tex = self._upload(img)
            self._ow, self._oh = img.size

        self._renderer.draw_overlay(0, 0, 0, 0.5)

        if self._over_tex:
            w = self._ndc_w(self._ow)
            h = self._ndc_h(self._oh)
            x = -w / 2
            y = -h / 2 + 0.1
            self._renderer.draw_texture_quad(self._over_tex, x, y, w, h)

        self._draw_restart_hint()

    def _draw_victory(self):
        """Desenha overlay e mensagem de vitória."""
        if not self._win_tex:
            img = _text_to_pil("VOCÊ VENCEU!", self._font_big, color=(80, 220, 80, 240))
            self._win_tex = self._upload(img)
            self._vw, self._vh = img.size

        self._renderer.draw_overlay(0, 0, 0, 0.45)

        if self._win_tex:
            w = self._ndc_w(self._vw)
            h = self._ndc_h(self._vh)
            x = -w / 2
            y = -h / 2 + 0.1
            self._renderer.draw_texture_quad(self._win_tex, x, y, w, h)

        self._draw_restart_hint()

    def _draw_restart_hint(self):
        """Desenha dica de reinício (tecla R)."""
        hint = "Pressione R para jogar novamente"
        img  = _text_to_pil(hint, self._font_small, color=(200, 200, 200, 200))
        tid  = self._upload(img)
        w    = self._ndc_w(img.width)
        h    = self._ndc_h(img.height)
        self._renderer.draw_texture_quad(tid, -w / 2, -h / 2 - 0.12, w, h)
        self._renderer.delete_texture(tid)

    def reset(self):
        """Limpa cache de HUD para reinício de partida."""
        self._last_timer_str = ""
        self._last_phase     = -1
        self._last_debug_on  = None
        self._timer_tex = self._release(self._timer_tex)
        self._phase_tex = self._release(self._phase_tex)
        self._debug_tex = self._release(self._debug_tex)
        phase_progress.release(self._renderer)
