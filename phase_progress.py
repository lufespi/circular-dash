"""Barra de progresso de fase para o HUD do jogo."""

from PIL import Image, ImageDraw, ImageFont
from OpenGL.GL import *
from constants import WINDOW_WIDTH, WINDOW_HEIGHT

_DEFAULT_STYLE: dict = {
    "bg_color":     (0.12, 0.12, 0.12, 0.82),  # fundo escuro semi-transparente (RGBA 0-1)
    "border_color": (0.55, 0.55, 0.55, 0.85),  # borda cinza clara
    "border_px":    1.0,                         # espessura da borda (unidade GL)
    "show_label":   True,                        # exibir percentual no centro da barra
    "label_color":  (255, 255, 255, 210),        # cor do texto (RGBA 0-255, para PIL)
}

_cache_percent: int = -1   # último percentual inteiro renderizado
_cache_tex:     int = 0    # tex_id OpenGL; 0 = não alocado
_cache_tw:      int = 0    # largura da textura em pixels
_cache_th:      int = 0    # altura da textura em pixels
_font = None               # fonte PIL; inicializada na primeira chamada


def _get_font():
    global _font
    if _font is None:
        for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
            try:
                _font = ImageFont.truetype(name, 11)
                return _font
            except Exception:
                pass
        _font = ImageFont.load_default()
    return _font


def _px_to_ndc_x(px: float) -> float:
    return (px / WINDOW_WIDTH) * 2.0 - 1.0


def _px_to_ndc_y(py: float) -> float:
    return 1.0 - (py / WINDOW_HEIGHT) * 2.0


def _ndc_w(px_w: float) -> float:
    return (px_w / WINDOW_WIDTH) * 2.0


def _ndc_h(px_h: float) -> float:
    return (px_h / WINDOW_HEIGHT) * 2.0


def _fill_color(fraction: float) -> tuple:
    if fraction <= 0.5:
        t = fraction * 2.0           # 0→1 na primeira metade
        r, g = t, 1.0
    else:
        t = (fraction - 0.5) * 2.0  # 0→1 na segunda metade
        r, g = 1.0, 1.0 - t * 0.65
    return (r, g, 0.10, 0.95)

def render_progress(
    renderer,
    elapsed: float,
    total_time: float,
    x_px: float = 12,
    y_px: float = 12,
    w_px: float = 220,
    h_px: float = 16,
    style: dict = None,
) -> None:
    """Desenha a barra de progresso da fase no HUD."""
    global _cache_percent, _cache_tex, _cache_tw, _cache_th

    s = {**_DEFAULT_STYLE, **(style or {})}
    fraction = max(0.0, min(1.0, elapsed / total_time if total_time > 0.0 else 0.0))

    # Converte região da barra de pixels para NDC
    x0    = _px_to_ndc_x(x_px)
    x1    = _px_to_ndc_x(x_px + w_px)
    y_bot = _px_to_ndc_y(y_px + h_px)  # NDC y da base (valor menor)
    y_top = _px_to_ndc_y(y_px)          # NDC y do topo (valor maior)
    nw    = x1 - x0

    # Retângulo de fundo
    br, bg, bb, ba = s["bg_color"]
    glColor4f(br, bg, bb, ba)
    glBegin(GL_QUADS)
    glVertex2f(x0, y_bot); glVertex2f(x1, y_bot)
    glVertex2f(x1, y_top); glVertex2f(x0, y_top)
    glEnd()

    # Retângulo de preenchimento proporcional a fraction
    if fraction > 0.0:
        fr, fg, fb, fa = _fill_color(fraction)
        fx1 = x0 + nw * fraction
        glColor4f(fr, fg, fb, fa)
        glBegin(GL_QUADS)
        glVertex2f(x0,  y_bot); glVertex2f(fx1, y_bot)
        glVertex2f(fx1, y_top); glVertex2f(x0,  y_top)
        glEnd()

    # Borda
    bc = s.get("border_color")
    if bc:
        br2, bg2, bb2, ba2 = bc
        glColor4f(br2, bg2, bb2, ba2)
        glLineWidth(float(s.get("border_px", 1.0)))
        glBegin(GL_LINE_LOOP)
        glVertex2f(x0, y_bot); glVertex2f(x1, y_bot)
        glVertex2f(x1, y_top); glVertex2f(x0, y_top)
        glEnd()

    # Label percentual
    if s.get("show_label", True):
        percent = int(fraction * 100)
        if percent != _cache_percent:
            if _cache_tex:
                renderer.delete_texture(_cache_tex)
                _cache_tex = 0
            text  = f"{percent}%"
            font  = _get_font()
            dummy = Image.new("RGBA", (1, 1))
            bbox  = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
            tw    = bbox[2] - bbox[0] + 4
            th    = bbox[3] - bbox[1] + 4
            img   = Image.new("RGBA", (max(tw, 1), max(th, 1)), (0, 0, 0, 0))
            ImageDraw.Draw(img).text(
                (2 - bbox[0], 2 - bbox[1]), text, font=font,
                fill=s.get("label_color", (255, 255, 255, 210)),
            )
            _cache_tex             = renderer.upload_text_texture(img)
            _cache_tw, _cache_th   = img.size
            _cache_percent         = percent

        if _cache_tex:
            lw = _ndc_w(_cache_tw)
            lh = _ndc_h(_cache_th)
            cx = (x0 + x1) * 0.5
            cy = (y_bot + y_top) * 0.5
            renderer.draw_texture_quad(_cache_tex, cx - lw * 0.5, cy - lh * 0.5, lw, lh)


def release(renderer) -> None:
    """Libera textura de label do cache OpenGL. Chamar em HUD.reset() ao reiniciar."""
    global _cache_percent, _cache_tex, _cache_tw, _cache_th
    if _cache_tex:
        renderer.delete_texture(_cache_tex)
        _cache_tex = 0
    _cache_percent = -1
    _cache_tw = _cache_th = 0
