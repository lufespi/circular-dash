"""Constantes globais de configuração de janela, gameplay e renderização."""

# Janela
WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600
WINDOW_TITLE = "Circular Dash"

# Música de fundo (.wav): `main.py` procura esse caminho no CWD e na pasta do projeto.
# Use o nome exato do arquivo em `assets/`, ou "" para silenciar.
BG_MUSIC_PATH = "assets/Full-Version_-Ultiate-Destruction-by-RobTopGames-_-Geometry-Dash.wav"

# Player
PLAYER_RADIUS        = 0.05 # tamanho do círculo
PLAYER_X_NDC         = -0.6 # posição do círculo na tela eixo x
PLAYER_GROUND_Y      = -0.64  # posição do círculo no chão eixo y
PLAYER_SPRITE_HEIGHT_SCALE = 1.35 # Só o desenho do sprite: >1 deixa o personagem mais alto (colisão continua o círculo acima).
PLAYER_JUMP_VELOCITY = 2 # velocidade do pulo
GRAVITY              = -5.0 # aceleração da gravidade
MAX_LIVES            = 3 # número de vidas
INVINCIBILITY_DURATION = 2.0 # tempo de invencibilidade

# Obstáculos
OBSTACLE_WIDTH       = 0.08 # largura do obstáculo
OBSTACLE_HEIGHT      = 0.20 # altura do obstáculo
OBSTACLE_SPAWN_X     = 1.2 # posição de spawn do obstáculo eixo x
OBSTACLE_DESPAWN_X   = -1.4 # posição de despawn do obstáculo eixo x
COLLISION_TOLERANCE  = 0.015 # tolerância de colisão

# Chão (y NDC)
GROUND_TOP_Y    = -0.70   # = PLAYER_GROUND_Y - PLAYER_RADIUS
GROUND_BOTTOM_Y = -1.0 # posição do chão no eixo y

# Xadrez no chão (textura procedural em memória). False = só cor sólida por fase.
GROUND_CHECKER_ENABLED   = True
GROUND_CHECKER_REPEAT_U  = 14.0  # repetições do padrão na largura da tela (-1 .. 1)
GROUND_CHECKER_REPEAT_V  = 3.0   # repetições na altura da faixa de chão
GROUND_CHECKER_COLOR_A   = (0.13, 0.13, 0.22)  # quadrado A (RGB 0..1)
GROUND_CHECKER_COLOR_B   = (0.24, 0.24, 0.34)  # quadrado B
GROUND_CHECKER_TEX_SIZE  = 64   # textura quadrada gerada em pixels (múltiplo do nº de células)
GROUND_CHECKER_TEX_CELLS = 8    # xadrez 8x8 dentro da textura (repete com GL_REPEAT)

# Fases — thresholds em segundos
PHASE_TIME_THRESHOLDS = [0, 35, 65, 106, 135] # thresholds das fases
TOTAL_GAME_TIME       = 165   # 2:45 # tempo total do jogo

PHASE_NAMES = [
    "Futurista",
    "Era Moderna",
    "Revolução Industrial",
    "Era Medieval",
    "Pré-História",
]

PHASE_BG_IMAGES = [
    "assets/[BG]-FUTURIST-21x9.png",
    "assets/[BG]-MODERN-AGE-21x9.png",
    "assets/[BG]-INDUSTRIAL-REVOLUTION-21x9.png",
    "assets/[BG]-MEDIEVAL-21x9.png",
    "assets/[BG]-PRE-HISTORY-21x9.png",
]

PHASE_PERSONAGENS = [
    "assets/personagem-futurista.png",
    "assets/personagem-atual.png",
    "assets/personagem-industrial.png",
    "assets/personagem-medieval.png",
    "assets/personagem-pre-historia.png",
]
# velocidade de movimento da tela e intervalo de spawn dos obstáculos
PHASE_DIFFICULTY = [
    (0.40, 2.00), # velocidade de movimento da tela e intervalo de spawn dos obstáculos
    (0.52, 1.75),
    (0.64, 1.50),
    (0.76, 1.25),
    (0.88, 1.00),
]

# Por fase: cor sólida de fundo só se PNG não carregar; chão e obstáculo sempre usados.
PHASE_COLORS = [
    {"bg_fallback": (0.03, 0.06, 0.225),
     "ground": (0.00,0.06,0.58), "obstacle": (0.00, 0.80, 1.00)},
    {"bg_fallback": (0.475, 0.715, 0.925),
     "ground": (0.90, 0.40, 0.10), "obstacle": (0.90, 0.40, 0.10)},
    {"bg_fallback": (0.45, 0.44, 0.415),
     "ground": (0.72, 0.35, 0.10), "obstacle": (0.72, 0.35, 0.10)},
    {"bg_fallback": (0.09, 0.08, 0.08),
     "ground": (0.60, 0.28, 0.08), "obstacle": (0.60, 0.28, 0.08)},
    {"bg_fallback": (0.44, 0.15, 0.03),
     "ground": (0.80, 0.28, 0.05), "obstacle": (0.80, 0.28, 0.05)},
]

COLOR_PLAYER       = (0.20, 0.85, 1.00, 1.0)
COLOR_PLAYER_FLASH = (1.00, 1.00, 1.00, 1.0)

CIRCLE_SEGMENTS    = 32
BG_SCROLL_PARALLAX = 0.35   # bg rola a 35% da velocidade dos obstáculos

OBSTACLE_POOL_SIZE = 20
SPAWN_JITTER       = 0.15   # variação aleatória no timer de spawn
