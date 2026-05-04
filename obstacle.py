"""Entidades de obstaculo e gerenciamento de spawn por sequencias pre-definidas por fase."""

import random
import numpy as np
from constants import (
    OBSTACLE_SPAWN_X, OBSTACLE_DESPAWN_X,
    COLLISION_TOLERANCE, GROUND_TOP_Y,
    SPAWN_JITTER,
)

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


def is_stair(seq: list) -> bool:
    return any(p['kind'] == 'block' and p['oy'] > 0.0 for p in seq)


def _starts_with_spike(seq: list) -> bool:
    if not seq:
        return False
    first = min(seq, key=lambda p: p['ox'])
    return first['kind'] == 'spike' and first['oy'] < 0.01


# FASE 0 - Futurista (0-35 s)
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


# FASE 1 - Era Moderna (35-65 s)
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


# FASE 2 - Revolucao Industrial (65-106 s)
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


# FASE 3 - Era Medieval (106-138 s)
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


# FASE 4 - Pre-Historia (138-168 s)
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