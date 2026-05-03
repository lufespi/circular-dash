"""Flags de desenvolvimento para alternar comportamentos em tempo de execução.

Para alternar via teclado, adicione ao key_callback em main.py:

    if key == glfw.KEY_T and action == glfw.PRESS:
        import debug
        debug.toggle("show_timer_text")
        debug.toggle("infinite_lives")
"""

DEBUG: dict = {
    "show_timer_text":     False,  # True = cronômetro MM:SS  |  False = barra de progresso
    "show_phase_progress": True,   # False = oculta a barra completamente
    "infinite_lives":      False,   # True = colisões não reduzem vidas nem encerram o jogo
}


def toggle(key: str) -> bool:
    """Inverte flag booleana e retorna o novo valor.

    Exemplo:
        import debug
        debug.toggle("show_timer_text")   # alterna entre texto e barra a cada pressionamento
    """
    if key not in DEBUG:
        raise KeyError(f"Flag de debug desconhecida: {key!r}")
    DEBUG[key] = not DEBUG[key]
    return DEBUG[key]


def set_flag(key: str, value: bool) -> None:
    """Define flag booleana explicitamente.

    Exemplo:
        debug.set_flag("show_phase_progress", False)  # oculta a barra sem alternância
    """
    if key not in DEBUG:
        raise KeyError(f"Flag de debug desconhecida: {key!r}")
    DEBUG[key] = bool(value)
