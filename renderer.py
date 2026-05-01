"""Camada de renderização OpenGL (fundo, entidades, HUD e overlays)."""

import numpy as np
from OpenGL.GL import *
from PIL import Image
from constants import (
    CIRCLE_SEGMENTS, BG_SCROLL_PARALLAX, GROUND_TOP_Y, GROUND_BOTTOM_Y,
    PHASE_COLORS, PHASE_BG_IMAGES, PHASE_PERSONAGENS,
    COLOR_PLAYER, COLOR_PLAYER_FLASH,
    WINDOW_WIDTH, WINDOW_HEIGHT, PLAYER_RADIUS,PLAYER_SPRITE_HEIGHT_SCALE
)

def _script_dir():
    s = __file__.replace("\\", "/")
    return s.rsplit("/", 1)[0] if "/" in s else "."


def _slash_join(base, tail):
    a = base.replace("\\", "/").rstrip("/")
    b = tail.replace("\\", "/").strip().lstrip("/")
    return f"{a}/{b}"


_ROOT = _script_dir()


class Renderer:
    """Encapsula operações OpenGL em funções de desenho reutilizáveis."""

    def __init__(self):
        self._bg_textures  = []   # tex_id por fase (0 = sem imagem)
        self._bg_scroll    = 0.0  # deslocamento UV horizontal
        self._player_textures = []  # sprite do personagem por fase
        self._player_aspect   = []  # altura / largura (para manter proporção em NDC)

    def load_phase_textures(self):
        """Carrega todas as imagens de fundo. Chame após contexto GL ativo."""
        for path in PHASE_BG_IMAGES:
            self._bg_textures.append(self._load_texture(path))

    def load_player_textures(self):
        """Carrega sprites do personagem (PNG com alpha) por fase."""
        self._player_textures.clear()
        self._player_aspect.clear()
        for path in PHASE_PERSONAGENS:
            tid, aspect = self._load_sprite_texture(path)
            self._player_textures.append(tid)
            self._player_aspect.append(aspect)

    # ------------------------------------------------------------------ #
    #  Textura                                                             #
    # ------------------------------------------------------------------ #

    def _resolve_texture_path(self, path: str) -> str:
        normalized = path.replace("\\", "/")
        parts = normalized.rsplit("/", 1)
        if len(parts) == 2:
            directory, filename = parts
        else:
            directory, filename = "", parts[0]

        return path

    def _load_texture(self, path: str) -> int:
        candidates = [path]
        resolved = self._resolve_texture_path(path)
        if resolved != path:
            candidates.append(resolved)

        try:
            img = None
            chosen_path = path
            for candidate in candidates:
                try:
                    img = Image.open(candidate).convert("RGB")
                    chosen_path = candidate
                    break
                except Exception:
                    continue

            if img is None:
                return 0

            img  = img.transpose(Image.FLIP_TOP_BOTTOM)
            w, h = img.size
            arr = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))

            tid = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tid)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, arr)
            glBindTexture(GL_TEXTURE_2D, 0)
            return tid
        except Exception as e:
            print(f"[Renderer] Falha ao carregar {chosen_path}: {e}")
            return 0

    def _load_sprite_texture(self, path: str) -> tuple:
        """Carrega PNG com alpha para sprite. Retorna (tex_id, altura/largura)."""
        pn = path.replace("\\", "/")
        candidates = [pn, _slash_join(_ROOT, pn)]
        img = None
        chosen = path
        for candidate in candidates:
            try:
                img = Image.open(candidate).convert("RGBA")
                chosen = candidate
                break
            except Exception:
                continue
        if img is None:
            return 0, 1.0
        try:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            w, h = img.size
            if w <= 0:
                return 0, 1.0
            aspect = float(h) / float(w)
            arr = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
            tid = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tid)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, arr)
            glBindTexture(GL_TEXTURE_2D, 0)
            return tid, aspect
        except Exception as e:
            print(f"[Renderer] Falha ao carregar sprite {chosen}: {e}")
            return 0, 1.0

    # ------------------------------------------------------------------ #
    #  Upload de textura de texto (usado pelo HUD)                        #
    # ------------------------------------------------------------------ #

    def upload_text_texture(self, pil_image) -> int:
        """Recebe PIL Image RGBA, devolve tex_id OpenGL."""
        img  = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
        w, h = img.size
        arr = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))

        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, arr)
        glBindTexture(GL_TEXTURE_2D, 0)
        return tid

    def delete_texture(self, tid: int):
        if tid:
            glDeleteTextures(1, np.array([tid], dtype=np.uint32))

    # ------------------------------------------------------------------ #
    #  Scroll do fundo                                                     #
    # ------------------------------------------------------------------ #

    def update_scroll(self, dt: float, scroll_speed: float):
        """Atualiza deslocamento horizontal UV do fundo em parallax."""
        self._bg_scroll += scroll_speed * BG_SCROLL_PARALLAX * dt
        if self._bg_scroll >= 1.0:
            self._bg_scroll -= 1.0

    # ------------------------------------------------------------------ #
    #  Fundo                                                               #
    # ------------------------------------------------------------------ #

    def draw_background(self, phase: int):
        """Desenha fundo da fase por textura ou cor sólida se arquivo faltar."""
        tid = self._bg_textures[phase] if phase < len(self._bg_textures) else 0
        if tid:
            self._draw_texture_bg(tid)
        else:
            self._draw_solid_fallback_bg(phase)

    def _draw_texture_bg(self, tid: int):
        u0 = self._bg_scroll
        u1 = self._bg_scroll + 1.0

        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tid)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(u0, 0); glVertex2f(-1, -1)
        glTexCoord2f(u1, 0); glVertex2f( 1, -1)
        glTexCoord2f(u1, 1); glVertex2f( 1,  1)
        glTexCoord2f(u0, 1); glVertex2f(-1,  1)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def _draw_solid_fallback_bg(self, phase: int):
        """Quad cheio quando não há textura — evita tela sem fundo definido."""
        rgb = PHASE_COLORS[phase]["bg_fallback"]
        glBegin(GL_QUADS)
        glColor3f(*rgb); glVertex2f(-1, -1)
        glColor3f(*rgb); glVertex2f( 1, -1)
        glColor3f(*rgb); glVertex2f( 1,  1)
        glColor3f(*rgb); glVertex2f(-1,  1)
        glEnd()

    # ------------------------------------------------------------------ #
    #  Chão                                                                #
    # ------------------------------------------------------------------ #

    def draw_ground(self, phase: int):
        """Faixa de chão procedural (alinha física/player); desenha por cima do BG."""
        c = PHASE_COLORS[phase]["ground"]
        glColor3f(*c)
        glBegin(GL_QUADS)
        glVertex2f(-1, GROUND_BOTTOM_Y)
        glVertex2f( 1, GROUND_BOTTOM_Y)
        glVertex2f( 1, GROUND_TOP_Y)
        glVertex2f(-1, GROUND_TOP_Y)
        glEnd()

    # ------------------------------------------------------------------ #
    #  Player                                                              #
    # ------------------------------------------------------------------ #

    def draw_player(self, player, phase: int):
        """Renderiza o personagem: sprite por fase (PNG) ou círculo se textura faltar."""
        cx, cy = float(player.position[0]), float(player.position[1])
        half_w = PLAYER_RADIUS
        tid = (
            self._player_textures[phase]
            if phase < len(self._player_textures)
            else 0
        )
        aspect = (
            self._player_aspect[phase]
            if phase < len(self._player_aspect)
            else 1.0
        )
        half_h = half_w * aspect * PLAYER_SPRITE_HEIGHT_SCALE

        if tid:
            a = 0.45 if player.is_flashing else 1.0
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, tid)
            glColor4f(1.0, 1.0, 1.0, a)
            glBegin(GL_QUADS)
            x0, x1 = cx - half_w, cx + half_w
            y0, y1 = cy - half_h, cy + half_h
            glTexCoord2f(0, 0); glVertex2f(x0, y0)
            glTexCoord2f(1, 0); glVertex2f(x1, y0)
            glTexCoord2f(1, 1); glVertex2f(x1, y1)
            glTexCoord2f(0, 1); glVertex2f(x0, y1)
            glEnd()
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            return

        if player.is_flashing:
            r, g, b, a = COLOR_PLAYER_FLASH
        else:
            r, g, b, a = COLOR_PLAYER

        radius = PLAYER_RADIUS
        glColor4f(r, g, b, a)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        for i in range(CIRCLE_SEGMENTS + 1):
            angle = 2 * np.pi * i / CIRCLE_SEGMENTS
            glVertex2f(cx + radius * float(np.cos(angle)),
                       cy + radius * float(np.sin(angle)))
        glEnd()

        glColor4f(1.0, 1.0, 1.0, 0.6)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        for i in range(CIRCLE_SEGMENTS):
            angle = 2 * np.pi * i / CIRCLE_SEGMENTS
            glVertex2f(cx + radius * float(np.cos(angle)),
                       cy + radius * float(np.sin(angle)))
        glEnd()


    # ------------------------------------------------------------------ #
    #  Obstáculo                                                           #
    # ------------------------------------------------------------------ #

    def draw_obstacle(self, obstacle, phase: int):
        """Renderiza obstáculo com preenchimento e borda."""
        c = PHASE_COLORS[phase]["obstacle"]
        x, y = obstacle.position
        w, h = obstacle.width, obstacle.height

        glColor3f(*c)
        glBegin(GL_QUADS)
        glVertex2f(x,     y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x,     y + h)
        glEnd()

        # Borda escura
        glColor4f(0, 0, 0, 0.5)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x,     y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x,     y + h)
        glEnd()

    # ------------------------------------------------------------------ #
    #  Textura de HUD (texto, ícones)                                     #
    # ------------------------------------------------------------------ #

    def draw_texture_quad(self, tid: int, x: float, y: float,
                          w: float, h: float, alpha: float = 1.0):
        """Desenha quad texturizado em coordenadas NDC."""
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tid)
        glColor4f(1, 1, 1, alpha)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x,     y)
        glTexCoord2f(1, 0); glVertex2f(x + w, y)
        glTexCoord2f(1, 1); glVertex2f(x + w, y + h)
        glTexCoord2f(0, 1); glVertex2f(x,     y + h)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    # ------------------------------------------------------------------ #
    #  Overlays                                                            #
    # ------------------------------------------------------------------ #

    def draw_overlay(self, r: float, g: float, b: float, a: float):
        """Retângulo semitransparente cobrindo a tela inteira."""
        glColor4f(r, g, b, a)
        glBegin(GL_QUADS)
        glVertex2f(-1, -1)
        glVertex2f( 1, -1)
        glVertex2f( 1,  1)
        glVertex2f(-1,  1)
        glEnd()

    def draw_life_icon(self, cx: float, cy: float, radius: float, filled: bool):
        """Ícone de vida: círculo cheio ou cinza."""
        if filled:
            glColor4f(1.0, 0.25, 0.25, 1.0)
        else:
            glColor4f(0.3, 0.3, 0.3, 0.8)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        for i in range(CIRCLE_SEGMENTS + 1):
            angle = 2 * np.pi * i / CIRCLE_SEGMENTS
            glVertex2f(cx + radius * float(np.cos(angle)),
                       cy + radius * float(np.sin(angle)))
        glEnd()

