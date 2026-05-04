"""Ponto de entrada do jogo e loop principal GLFW/OpenGL."""

import sys
import time

import glfw
from OpenGL.GL import *
from constants import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, BG_MUSIC_PATH
from game import GameState

game = None
last_time = 0.0


def _script_dir():
    s = __file__.replace("\\", "/")
    return s.rsplit("/", 1)[0] if "/" in s else "."


def _slash_join(base, tail):
    a = base.replace("\\", "/").rstrip("/")
    b = tail.replace("\\", "/").strip().lstrip("/")
    return f"{a}/{b}"


def _file_exists(path):
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


_PROJECT_ROOT = _script_dir()


def _resolved_music_path(): # normaliza o caminho da música de fundo
    if not BG_MUSIC_PATH.strip():
        return None
    rel = BG_MUSIC_PATH.strip()
    candidates = [rel.replace("\\", "/"), _slash_join(_PROJECT_ROOT, rel)]
    seen = set()
    for cand in candidates:
        cand = cand.replace("\\", "/")
        if cand in seen:
            continue
        seen.add(cand)
        if _file_exists(cand):
            return cand
    return None


def start_bg_music():
    """Toca WAV em loop no Windows (`winsound`); ignorado se path vazio ou inválido."""
    if sys.platform != "win32":
        return
    wav_path = _resolved_music_path()
    if wav_path is None:
        if BG_MUSIC_PATH.strip():
            alt = _slash_join(_PROJECT_ROOT, BG_MUSIC_PATH.strip())
            sys.stderr.write(
                f"[música] Arquivo não encontrado: {BG_MUSIC_PATH!r} "
                f"(Procure também em {alt})\n"
            )
        return
    import winsound

    winsound.PlaySound(
        wav_path,
        winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
    )


def stop_bg_music():
    if sys.platform != "win32":
        return
    try:
        import winsound

        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass


def key_callback(window, key, scancode, action, mods):
    """Encaminha eventos de teclado para o estado do jogo."""
    if key == glfw.KEY_SPACE  and action == glfw.PRESS:
        game.on_jump()
    if key == glfw.KEY_R      and action == glfw.PRESS:
        game.on_restart()
    if key == glfw.KEY_D      and action == glfw.PRESS:
        import debug
        debug.toggle("show_timer_text")   # alterna cronômetro MM:SS ↔ barra de progresso
        debug.toggle("infinite_lives")
    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(window, True)


def main():
    """Inicializa OpenGL e executa o loop principal até fechar a janela."""
    global game, last_time

    if not glfw.init():
        raise RuntimeError("Falha ao inicializar GLFW")

    glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)

    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Falha ao criar janela GLFW")

    glfw.make_context_current(window)
    glfw.set_key_callback(window, key_callback)
    glfw.swap_interval(1)   # vsync

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    start_bg_music()

    game      = GameState()
    last_time = time.time()

    while not glfw.window_should_close(window):
        now        = time.time()
        # Limita delta para evitar saltos grandes quando o app perde foco.
        delta      = min(now - last_time, 0.05)
        last_time  = now

        game.update(delta)

        glClear(GL_COLOR_BUFFER_BIT)
        game.render()

        glfw.swap_buffers(window)
        glfw.poll_events()

    stop_bg_music()
    glfw.terminate()


if __name__ == "__main__":
    main()
