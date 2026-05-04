"""Flags de desenvolvimento para alternar comportamentos em tempo de execução."""

DEBUG: dict = {
    "show_timer_text":     False,  # True = cronômetro MM:SS  |  False = barra de progresso
    "show_phase_progress": True,   # False = oculta a barra completamente
    "infinite_lives":      False,   # True = colisões não reduzem vidas nem encerram o jogo
}


def toggle(key: str) -> bool:
    """Inverte flag booleana e retorna o novo valor."""
    if key not in DEBUG:
        raise KeyError(f"Flag de debug desconhecida: {key!r}")
    DEBUG[key] = not DEBUG[key]
    return DEBUG[key]


def set_flag(key: str, value: bool) -> None:
    """Define flag booleana explicitamente."""
    if key not in DEBUG:
        raise KeyError(f"Flag de debug desconhecida: {key!r}")
    DEBUG[key] = bool(value)
