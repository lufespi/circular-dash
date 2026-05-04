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

    # Duração de cada metade da transição (fade-out + fade-in), em segundos
    TRANSITION_HALF = 0.75

    def __init__(self):
        self._bg_textures  = []   # tex_id por fase (0 = sem imagem)
        self._bg_scroll    = 0.0  # deslocamento UV horizontal
        self._player_textures = []  # sprite do personagem por fase
        self._player_aspect   = []  # altura / largura (para manter proporção em NDC)
        self._trans_state      = None # estado da transição de fase
        self._trans_timer      = 0.0   # tempo decorrido na etapa atual
        self._trans_from_phase = 0     # fase de onde estamos saindo
        self._trans_to_phase   = 0     # fase para onde estamos indo
        self._trans_alpha      = 0.0   # opacidade atual do overlay preto (0..1)

    def load_phase_textures(self):
        """Carrega todas as imagens de fundo da fase. Chame após contexto GL ativo."""
        for path in PHASE_BG_IMAGES:
            self._bg_textures.append(self._load_texture(path))

    def load_player_textures(self):
        """Carrega sprites do personagem (PNG com alpha) por fase."""
        self._player_textures.clear() 
        self._player_aspect.clear() 
        for path in PHASE_PERSONAGENS:
            tid, aspect = self._load_sprite_texture(path) # carrega a textura e o aspecto do personagem
            self._player_textures.append(tid) 
            self._player_aspect.append(aspect) 

    def _resolve_texture_path(self, path: str) -> str: # normaliza o caminho da imagem
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

            img  = img.transpose(Image.FLIP_TOP_BOTTOM) # inverte a imagem (opengl usa a direção inversa)
            w, h = img.size
            arr = np.ascontiguousarray(np.asarray(img, dtype=np.uint8)) # converte a imagem para um array de uint8

            tid = glGenTextures(1) # gera um id para a textura
            glBindTexture(GL_TEXTURE_2D, tid) # vincula a textura ao id
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE) # define o modo de repetição da textura
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # define o filtro de minimização da textura
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR) # define o filtro de maximização da textura
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1) # define o alinhamento dos pixels da textura
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, arr) # carrega a textura na memória
            glBindTexture(GL_TEXTURE_2D, 0) # desvincula a textura
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

    def update_scroll(self, dt: float, scroll_speed: float):
        """Atualiza deslocamento horizontal UV do fundo em parallax."""
        self._bg_scroll += scroll_speed * BG_SCROLL_PARALLAX * dt
        if self._bg_scroll >= 1.0:
            self._bg_scroll -= 1.0

    def start_phase_transition(self, from_phase: int, to_phase: int):
        """Inicia transição de fade entre duas eras. Chame ao detectar mudança de fase."""
        self._trans_from_phase = from_phase
        self._trans_to_phase   = to_phase
        self._trans_state      = 'fade_out'
        self._trans_timer      = 0.0
        self._trans_alpha      = 0.0

    def update_transition(self, dt: float) -> bool:
        """Atualiza animação de fade. Retorna True enquanto a transição estiver ativa."""
        if self._trans_state is None:
            return False
        self._trans_timer += dt
        half = self.TRANSITION_HALF
        if self._trans_state == 'fade_out':
            self._trans_alpha = min(self._trans_timer / half, 1.0)
            if self._trans_timer >= half:
                self._trans_state = 'fade_in'
                self._trans_timer = 0.0
        elif self._trans_state == 'fade_in':
            self._trans_alpha = 1.0 - min(self._trans_timer / half, 1.0)
            if self._trans_timer >= half:
                self._trans_state = None
                self._trans_alpha = 0.0
        return True

    @property
    def transition_active(self) -> bool:
        return self._trans_state is not None

    @property
    def transition_phase(self) -> int:
        """Fase que deve ser usada para o fundo durante a transição."""
        if self._trans_state == 'fade_in':
            return self._trans_to_phase
        return self._trans_from_phase

    def draw_background(self, phase: int):
        """Desenha fundo da fase por textura ou cor sólida se arquivo faltar.
        Durante transição de era, usa a fase correta e aplica overlay preto de fade."""
        render_phase = self.transition_phase if self.transition_active else phase
        tid = self._bg_textures[render_phase] if render_phase < len(self._bg_textures) else 0
        if tid:
            self._draw_texture_bg(tid)
        else:
            self._draw_solid_fallback_bg(render_phase)

        # Overlay de fade preto por cima do fundo (alpha 0→1→0)
        if self.transition_active and self._trans_alpha > 0.0:
            self.draw_overlay(0.0, 0.0, 0.0, self._trans_alpha)

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
            a = 0.45 if player.is_flashing else 1.0 # opacidade do sprite (dano do player)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, tid)
            glColor4f(1.0, 1.0, 1.0, a)
            glBegin(GL_QUADS)
            x0, x1 = cx - half_w, cx + half_w
            y0, y1 = cy - half_h, cy + half_h
            glTexCoord2f(0, 0); glVertex2f(x0, y0) # desenha o sprite (no retangulo do sprite)
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

        radius = PLAYER_RADIUS # desenha o círculo do player caso não tenha sprite
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

    def draw_obstacle(self, obstacle, phase: int):
        """Renderiza obstáculo: espinho (triângulo) ou bloco (quad com detalhes)."""
        if obstacle.kind == 'spike':
            self._draw_spike(obstacle, phase)
        else:
            self._draw_block(obstacle, phase)

    def _draw_spike(self, obstacle, phase: int):
        c  = PHASE_COLORS[phase]["obstacle"]
        x, y = float(obstacle.position[0]), float(obstacle.position[1])
        w, h = obstacle.width, obstacle.height

        # Corpo principal — triângulo preenchido
        tip_x = x + w * 0.5
        tip_y = y + h

        # Sombra/corpo escuro primeiro
        r, g, b = c
        dark = (r * 0.55, g * 0.55, b * 0.55)
        glColor3f(*dark)
        glBegin(GL_TRIANGLES)
        glVertex2f(x,       y)
        glVertex2f(x + w,   y)
        glVertex2f(tip_x,   tip_y)
        glEnd()

        # Face iluminada (lado esquerdo mais claro)
        bright = (min(r * 1.5, 1.0), min(g * 1.5, 1.0), min(b * 1.5, 1.0))
        glBegin(GL_TRIANGLES)
        glColor3f(*c);      glVertex2f(x,       y)
        glColor3f(*bright); glVertex2f(tip_x,   tip_y)
        glColor3f(*c);      glVertex2f(x + w * 0.5, y)
        glEnd()

        # Contorno
        glColor4f(0.0, 0.0, 0.0, 0.7)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x,       y)
        glVertex2f(x + w,   y)
        glVertex2f(tip_x,   tip_y)
        glEnd()

        # Linha de destaque na ponta
        glColor4f(1.0, 1.0, 1.0, 0.55)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        glVertex2f(x,     y)
        glVertex2f(tip_x, tip_y)
        glEnd()

    def _draw_block(self, obstacle, phase: int):
        c  = PHASE_COLORS[phase]["obstacle"]
        x, y = float(obstacle.position[0]), float(obstacle.position[1])
        w, h = obstacle.width, obstacle.height
        w_render = w * (WINDOW_HEIGHT / WINDOW_WIDTH)
        r, g, b = c

        # Face principal
        glColor3f(*c)
        glBegin(GL_QUADS)
        glVertex2f(x,     y)
        glVertex2f(x + w_render, y)
        glVertex2f(x + w_render, y + h)
        glVertex2f(x,     y + h)
        glEnd()

        # Detalhe interno (quadrado menor)
        m  = min(w_render, h) * 0.18   
        ir = min(r * 0.5, 1.0)
        ig = min(g * 0.5, 1.0)
        ib = min(b * 0.5, 1.0)
        glColor4f(ir, ig, ib, 0.65)
        glBegin(GL_QUADS)
        glVertex2f(x + m,     y + m)
        glVertex2f(x + w_render - m, y + m)
        glVertex2f(x + w_render - m, y + h - m)
        glVertex2f(x + m,     y + h - m)
        glEnd()


        # Sombra no canto inferior-direito
        glColor4f(0.0, 0.0, 0.0, 0.35)
        glBegin(GL_LINES)
        glVertex2f(x + w_render - 0.004, y + h)
        glVertex2f(x + w_render - 0.004, y)
        glVertex2f(x,             y + 0.004)
        glVertex2f(x + w_render,         y + 0.004)
        glEnd()

        # Contorno externo
        glColor4f(0.0, 0.0, 0.0, 0.60)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x,     y)
        glVertex2f(x + w_render, y)
        glVertex2f(x + w_render, y + h)
        glVertex2f(x,     y + h)
        glEnd()

    def draw_texture_quad(self, tid: int, x: float, y: float,w: float, h: float, alpha: float = 1.0):
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

    def draw_finish_line(self, x: float):
        pole_w   = 0.012
        pole_top = 0.75     
        pole_bot = GROUND_TOP_Y

        # poste
        glColor3f(0.85, 0.85, 0.85)
        glBegin(GL_QUADS)
        glVertex2f(x,          pole_bot)
        glVertex2f(x + pole_w, pole_bot)
        glVertex2f(x + pole_w, pole_top)
        glVertex2f(x,          pole_top)
        glEnd()

        # Bandeirola (triângulo) no topo
        flag_w = 0.14
        flag_h = 0.09
        glColor3f(1.0, 0.85, 0.0)   # amarelo ouro
        glBegin(GL_TRIANGLES)
        glVertex2f(x + pole_w,           pole_top)
        glVertex2f(x + pole_w + flag_w,  pole_top - flag_h * 0.5)
        glVertex2f(x + pole_w,           pole_top - flag_h)
        glEnd()

        # borda da bandeirola
        glColor4f(0.6, 0.4, 0.0, 0.9)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x + pole_w,           pole_top)
        glVertex2f(x + pole_w + flag_w,  pole_top - flag_h * 0.5)
        glVertex2f(x + pole_w,           pole_top - flag_h)
        glEnd()

        # --- Faixa xadrez horizontal no nível do chão ---
        stripe_h = 0.055
        stripe_y = GROUND_TOP_Y - stripe_h
        cols     = 10
        col_w    = 0.035
        for i in range(cols):
            cx = x + i * col_w
            if i % 2 == 0:
                glColor4f(1.0, 1.0, 1.0, 0.95)
            else:
                glColor4f(0.05, 0.05, 0.05, 0.95)
            glBegin(GL_QUADS)
            glVertex2f(cx,         stripe_y)
            glVertex2f(cx + col_w, stripe_y)
            glVertex2f(cx + col_w, GROUND_TOP_Y)
            glVertex2f(cx,         GROUND_TOP_Y)
            glEnd()

        # Texto "META" acima da bandeirola
        glColor4f(1.0, 1.0, 1.0, 0.55)
        glLineWidth(2.5)
        glBegin(GL_LINES)
        glVertex2f(x + pole_w * 0.5, pole_bot)
        glVertex2f(x + pole_w * 0.5, pole_top)
        glEnd()

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