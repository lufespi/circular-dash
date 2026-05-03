"""Entidades de obstaculo e gerenciamento de spawn por sequencias pre-definidas por fase.

ANALISE FISICA COMPLETA
=======================

Constants: JUMP_VEL=1.5, GRAVITY=5.0, R=0.05, GROUND_TOP_Y=-0.70, PLAYER_GROUND_Y=-0.64
Tolerancia colisao: 0.015

Pulo:
  Duracao = 2 * 1.5 / 5.0           = 0.60 s
  Altura maxima (centro) = 1.5^2/10  = 0.225 NDC  (centro: -0.64 -> -0.415)
  Tempo acima de h=0.13 (espinho)    = 0.438 s   (t in [0.081, 0.519])
  Tempo dentro da snap zone do 2H    = 0.134 s   (t in [0.300, 0.434], vy<=0.05)

Velocidades por fase:
  P0: 0.40   P1: 0.52   P2: 0.64   P3: 0.76   P4: 0.88

Spawn intervals por fase:
  P0: 2.00   P1: 1.75   P2: 1.50   P3: 1.25   P4: 1.00

Espaco util por sequencia (interval * speed - 0.22 margem):
  P0: 0.58   P1: 0.69   P2: 0.74   P3: 0.73   P4: 0.66

GAPS RECALIBRADOS (para caber dentro do espaco util de cada fase):
  _J0=0.42  _J1=0.53  _J2=0.58  _J3=0.57  _J4=0.50
  _BJ=0.10  (gap bloco->espinho no topo, jogador tem vantagem de altura)

CLUSTER (passagem em UM pulo) - largura maxima do cluster:
  Cw_max = 0.438 * V - 0.10 (margem de 2*R)
  P0: 0.075   P1: 0.128   P2: 0.180   P3: 0.233   P4: 0.285

REGRAS DE DESIGN:
  - NUNCA espinho no topo de bloco no MESMO ox (jogador toca ao pousar)
  - Bloco 3H so via ESCADA (a partir de plataforma 1H, snap zone alcanca)
  - Bloco 2H pode ser pousado do chao (snap zone alcanca, pulo da margem)
  - Stair: pelo menos um bloco com oy>0 -> stair-guard ativa proxima sequencia
"""

import random
import numpy as np
from constants import (
    OBSTACLE_SPAWN_X, OBSTACLE_DESPAWN_X,
    COLLISION_TOLERANCE, GROUND_TOP_Y,
    SPAWN_JITTER,
)

# ---------------------------------------------------------------------------
# Dimensoes base
# ---------------------------------------------------------------------------
SPK_W = 0.08
SPK_H = 0.13
BLK_W = 0.13
BLK_H = 0.13

_S  = SPK_W
_B  = BLK_W
_H  = BLK_H
_G  = 0.04   # gap minimo (cluster, pecas coladas)

# Gaps recalibrados por fase
# Regra: ox_max <= ((interval - JITTER) - 0.50) * V
# Garante >= 0.50s de reacao entre o ultimo elem da seq e o proximo spawn
_J0 = 0.40   # P0 (V=0.40, interval=2.00, ox_max=0.54)
_J1 = 0.38   # P1 (ox_max=0.57)
_J2 = 0.36   # P2 (ox_max=0.54)
_J3 = 0.28   # P3 (ox_max=0.45) -- reduzido para evitar impossibilidade
_J4 = 0.12   # P4 (ox_max=0.30) -- fase rapida, sequencias curtas

# Gap bloco-espinho (jogador no topo do bloco tem vantagem vertical)
_BJ = 0.10

STOP_SPAWN_BEFORE_END = 9.0


def _spk(ox, oy=0.0, w=SPK_W, h=SPK_H):
    return dict(kind='spike', ox=ox, oy=oy, w=w, h=h)

def _blk(ox, oy=0.0, w=BLK_W, h=BLK_H):
    return dict(kind='block', ox=ox, oy=oy, w=w, h=h)


# ---------------------------------------------------------------------------
# Utilitarios - stair guard
# ---------------------------------------------------------------------------

def is_stair(seq: list) -> bool:
    return any(p['kind'] == 'block' and p['oy'] > 0.0 for p in seq)


def _starts_with_spike(seq: list) -> bool:
    if not seq:
        return False
    first = min(seq, key=lambda p: p['ox'])
    return first['kind'] == 'spike' and first['oy'] < 0.01


# ===========================================================================
# FASE 0 - Futurista (0-35 s) - Muito Facil [NAO ALTERAR]
# ===========================================================================
SEQUENCES_P0 = [
    [_blk(0.0)],
    [_blk(0.0, w=2*_B)],
    [_spk(0.0)],
    [],
    [_spk(0.0), _spk(_S + _J0)],
    [_blk(0.0, w=2*_B), _blk(2*_B + _G, oy=_H, w=2*_B)],
    [_blk(0.0), _spk(_B + _J0)],
    [_blk(0.0, w=2*_B), _blk(2*_B + _G, oy=_H, w=2*_B)],
]


# ===========================================================================
# FASE 1 - Era Moderna (35-65 s) - Facil-Medio
#
# V=0.52, interval=1.75s, ox_max=0.57 NDC, dist_pulo=0.312 NDC
# Plataforma aerea: oy=0.5H — forcado a pular por cima
# ===========================================================================
_P1_OY = 0.5 * _H

SEQUENCES_P1 = [
    [_spk(0.0)],
    [_spk(0.0), _spk(_S)],
    [_blk(0.0, w=2*_B)],
    [_spk(0.0), _spk(_S + _J1)],
    [_blk(0.0, oy=_P1_OY, w=2*_B)],
    [_blk(0.0), _spk(_B + _J1)],
    [_spk(0.0), _spk(_S), _spk(2*_S + _J1)],
    [_spk(0.0), _blk(_S + _J1)],
]


# ===========================================================================
# FASE 2 - Revolucao Industrial (65-106 s) - Medio
#
# V=0.64, interval=1.50s, ox_max=0.54 NDC, dist_pulo=0.384 NDC
# Plataformas aereas: oy=0.5H — jogador forcado a pular por cima
# (nao passa por baixo: espaco=0.065 < diametro=0.10)
# ===========================================================================
_P2_OY = 0.5 * _H   # altura da plataforma aerea da P2

SEQUENCES_P2 = [
    [_spk(0.0), _spk(_S)],
    [_blk(0.0, w=2*_B)],
    [_spk(0.0), _spk(_S + _J2)],
    [],
    [_blk(0.0, oy=_P2_OY, w=2*_B)],
    [_blk(0.0, w=2*_B), _blk(2*_B + _G, oy=_H, w=2*_B)],
    [_spk(0.0), _spk(_S + _J2), _spk(2*_S + _J2)],
    [_blk(0.0, oy=_P2_OY), _spk(_B + _J2)],
]


# ===========================================================================
# FASE 3 - Era Medieval (106-138 s) - Dificil
#
# V=0.76, interval=1.25s, ox_max=0.45 NDC, dist_pulo=0.456 NDC
# REGRAS:
#   - Blocos isolados: apenas 1H (topo=-0.57), jogador pula por cima
#   - Blocos 2H sozinhos: proibido (intransponivel do chao)
#   - Dois obstaculos separados: dist inicio->inicio deve ser > 0.456
#     Como ox_max=0.45 < 0.456, NAO e possivel ter 2 espinhos separados
#     -> usar clusters (colados) para multiplos espinhos
#   - Escada valida: bloco1H(ox=0) + bloco1H(oy=H, ox=B+G)
#     jogador pousa no 1o, pula e passa o 2o (base pulo=-0.345 > topo -0.44)
#   - Espinho apos bloco 1H: jogador esta em cima do bloco, tem vantagem
# idx 0 e 5 sao STAIR -> stair-guard ativa idx 1 e 6 (NON-SPIKE).
# ===========================================================================
SEQUENCES_P3 = [
    # 0 - Escada classica: bloco 1H + bloco 1H elevado (oy=H)  <- STAIR
    [
        _blk(0.0),
        _blk(_B + _G, oy=_H, h=_H),
    ],

    # 1 - Bloco 1H + espinho colado  (NON-SPIKE - seguro apos stair)
    #     jogador pousa no bloco e enfrenta espinho logo apos
    [
        _blk(0.0),
        _spk(_B + _G),
    ],

    # 2 - Cluster duplo de espinhos
    [
        _spk(0.0),
        _spk(_S),
    ],

    # 3 - Cluster duplo + bloco 1H colado
    [
        _spk(0.0),
        _spk(_S),
        _blk(2*_S + _G),
    ],

    # 4 - Espinho + bloco 1H colado (jogador pula o espinho e pousa no bloco)
    [
        _spk(0.0),
        _blk(_S + _G),
    ],

    # 5 - Escada larga: plataforma 2B + bloco 1H elevado (oy=H)  <- STAIR
    [
        _blk(0.0, w=2*_B),
        _blk(2*_B + _G, oy=_H, h=_H),
    ],

    # 6 - Bloco 1H simples  (NON-SPIKE - seguro apos stair)
    [_blk(0.0)],

    # 7 - Espinho simples
    [_spk(0.0)],
]


# ===========================================================================
# FASE 4 - Pre-Historia (138-168 s) - Muito Dificil
#
# V=0.88, interval=1.00s, ox_max=0.30 NDC
# Gap entre obstaculos separados: _J4=0.12
# Sequencias muito curtas (max 2-3 elem). Cluster triplo cabe (ox=0.16).
# ===========================================================================
SEQUENCES_P4 = [
    # 0 - Cluster triplo (tres espinhos colados = um pulo longo)
    [
        _spk(0.0),
        _spk(_S),
        _spk(2*_S),
    ],

    # 1 - Torre 2H simples
    [_blk(0.0, h=2*_H)],

    # 2 - Cluster duplo (colados = um pulo so, unico viavel na P4)
    [
        _spk(0.0),
        _spk(_S),
    ],

    # 3 - Cluster duplo + bloco
    [
        _spk(0.0),
        _spk(_S),
        _blk(2*_S + _J4),
    ],

    # 4 - Espinho simples
    [_spk(0.0)],

    # 5 - Cluster triplo (sem bloco depois - cabe no ox_max)
    [
        _spk(0.0),
        _spk(_S),
        _spk(2*_S),
    ],

    # 6 - Espinho simples (variacao de ritmo)
    [_spk(0.0)],

    # 7 - Cluster duplo
    [
        _spk(0.0),
        _spk(_S),
    ],
]


SEQUENCES_PHASE = [
    SEQUENCES_P0,
    SEQUENCES_P1,
    SEQUENCES_P2,
    SEQUENCES_P3,
    SEQUENCES_P4,
]


# ---------------------------------------------------------------------------
# Classe de uma peca de obstaculo
# ---------------------------------------------------------------------------
class ObstaclePiece:
    def __init__(self):
        self.kind     = 'spike'
        self.position = np.array([OBSTACLE_DESPAWN_X - 2.0, GROUND_TOP_Y], dtype=float)
        self.width    = SPK_W
        self.height   = SPK_H
        self.active   = False

    def activate(self, kind: str, x: float, y: float, w: float, h: float):
        self.kind     = kind
        self.position = np.array([x, y], dtype=float)
        self.width    = w
        self.height   = h
        self.active   = True

    def update(self, dt: float, speed: float):
        if not self.active:
            return
        self.position[0] -= speed * dt
        if self.position[0] + self.width < OBSTACLE_DESPAWN_X:
            self.active = False

    @property
    def aabb(self):
        t  = COLLISION_TOLERANCE
        x0 = self.position[0] + t
        y0 = self.position[1] + t
        x1 = self.position[0] + self.width  - t
        y1 = self.position[1] + self.height - t
        return (x0, y0, x1, y1)


# ---------------------------------------------------------------------------
# Gerenciador
# ---------------------------------------------------------------------------
class ObstacleManager:
    POOL_SIZE = 80

    def __init__(self):
        self._pool          = [ObstaclePiece() for _ in range(self.POOL_SIZE)]
        self._spawn_timer   = 0.0
        self._seq_indices   = [0] * len(SEQUENCES_PHASE)
        self._last_was_stair = False

    def update(self, dt: float, speed: float, spawn_interval: float,
               phase: int, elapsed: float, total_time: float):
        for p in self._pool:
            p.update(dt, speed)

        if total_time - elapsed <= STOP_SPAWN_BEFORE_END:
            return

        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_sequence(phase)
            jitter = random.uniform(-SPAWN_JITTER, SPAWN_JITTER)
            self._spawn_timer = spawn_interval + jitter

    def _spawn_sequence(self, phase: int):
        pool = SEQUENCES_PHASE[min(phase, len(SEQUENCES_PHASE) - 1)]
        n    = len(pool)
        idx  = self._seq_indices[phase]

        if self._last_was_stair:
            for _ in range(n):
                if not _starts_with_spike(pool[idx % n]):
                    break
                idx += 1

        seq = pool[idx % n]
        self._seq_indices[phase] = (idx + 1) % n
        self._last_was_stair     = is_stair(seq)

        for piece in seq:
            x = OBSTACLE_SPAWN_X + piece['ox']
            y = GROUND_TOP_Y     + piece['oy']
            self._activate_piece(piece['kind'], x, y, piece['w'], piece['h'])

    def _activate_piece(self, kind, x, y, w, h):
        for p in self._pool:
            if not p.active:
                p.activate(kind, x, y, w, h)
                return

    def active_obstacles(self):
        return [p for p in self._pool if p.active]

    def reset(self):
        for p in self._pool:
            p.active = False
        self._spawn_timer    = 0.0
        self._seq_indices    = [0] * len(SEQUENCES_PHASE)
        self._last_was_stair = False