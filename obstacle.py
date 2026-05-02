"""Entidades de obstáculo e gerenciamento de spawn/pool.

Tipos de obstáculo:
  - 'spike'  : espinho triangular — qualquer toque tira vida
  - 'block'  : bloco sólido — pode pular EM CIMA (topo), lateral/inferior tira vida

Sequências pré-montadas são selecionadas por dificuldade (easy/medium/hard)
proporcional à fase atual. Cada peça da sequência é um dict:
    kind : 'spike' | 'block'
    ox   : offset X relativo ao início da sequência (NDC)
    oy   : offset Y a partir do GROUND_TOP_Y (0 = no chão, positivo = elevado)
    w    : largura (NDC)
    h    : altura (NDC)
"""

import random
import numpy as np
from constants import (
    OBSTACLE_SPAWN_X, OBSTACLE_DESPAWN_X,
    COLLISION_TOLERANCE, GROUND_TOP_Y,
    SPAWN_JITTER,
)

# ---------------------------------------------------------------------------
# Tamanhos base
# ---------------------------------------------------------------------------
SPIKE_W  = 0.07
SPIKE_H  = 0.12
BLOCK_W  = 0.09
BLOCK_H  = 0.09

# ---------------------------------------------------------------------------
# Fisica do jogador — espelhados de constants para calculo de passabilidade
# ---------------------------------------------------------------------------
_JUMP_VEL       = 2.0    # PLAYER_JUMP_VELOCITY
_GRAVITY_ABS    = 5.0    # abs(GRAVITY)
_RADIUS         = 0.05   # PLAYER_RADIUS

# Altura maxima de pulo: v²/(2g)
JUMP_MAX_HEIGHT  = (_JUMP_VEL ** 2) / (2 * _GRAVITY_ABS)   # aprox 0.40 NDC
# Margem de seguranca (82% da altura maxima)
SAFE_JUMP_HEIGHT = JUMP_MAX_HEIGHT * 0.82                   # aprox 0.328 NDC

# ---------------------------------------------------------------------------
# Helpers de criacao de pecas
# ---------------------------------------------------------------------------
def _spk(ox, oy=0.0, w=SPIKE_W, h=SPIKE_H):
    return dict(kind='spike', ox=ox, oy=oy, w=w, h=h)

def _blk(ox, oy=0.0, w=BLOCK_W, h=BLOCK_H):
    return dict(kind='block', ox=ox, oy=oy, w=w, h=h)

_G  = 0.04    # gap minimo entre pecas
_S  = SPIKE_W
_B  = BLOCK_W
_BH = BLOCK_H


# ===========================================================================
# SEQUENCIAS FACEIS  (fase 0-1)
# ===========================================================================
SEQUENCES_EASY = [
    # 1 espinho isolado
    [_spk(0.0)],
    # 1 bloco baixo
    [_blk(0.0)],
    # 2 espinhos com espaco entre eles (dois saltos curtos)
    [_spk(0.0), _spk(0.22)],
    # bloco + espinho separados
    [_blk(0.0), _spk(0.22)],
    # 2 blocos (plataforma curta para pousar)
    [_blk(0.0), _blk(_B + _G)],
    # espinho entre dois blocos (pula o bloco 1, aterrissa, pula o espinho)
    [_blk(0.0), _spk(0.14), _blk(0.25)],

    # Mini escadinha 2 degraus — sobe 1 bloco e cai do outro lado
    # Jogador pula no degrau (nível 1) e depois pula para frente
    [
        _blk(0.00),                    # degrau 1 base
        _blk(0.00, oy=_BH),            # degrau 1 topo (nivel 2)
        _blk(_B + _G),                  # degrau 2 base (mais a frente, nivel 1)
    ],

    # Ponte simples: bloco-espinho-bloco
    # Pula no bloco 1, pula o espinho do chão, pousa no bloco 2
    [
        _blk(0.00),
        _spk(_B + _G + 0.01),
        _blk(_B + _G + _S + _G),
    ],
]

# ===========================================================================
# SEQUENCIAS MEDIAS  (fase 1-3)
# ===========================================================================
SEQUENCES_MEDIUM = [
    # 3 espinhos seguidos (salto unico longo)
    [_spk(0.0), _spk(_S + _G), _spk(2*(_S + _G))],

    # Torre alta — bloco com 2.5x a altura normal
    [_blk(0.0, h=_BH * 2.5)],

    # Escadinha 3 degraus ascendente
    # Jogador sobe: degrau1(altura 1) -> degrau2(altura 2) -> degrau3(altura 3)
    # e depois cai do outro lado (cada degrau e uma coluna de blocos)
    [
        # degrau 1 (coluna de 1 bloco)
        _blk(0.00),
        # degrau 2 (coluna de 2 blocos)
        _blk(_B + _G),
        _blk(_B + _G, oy=_BH),
        # degrau 3 (coluna de 3 blocos) — topo mais alto
        _blk(2*(_B + _G)),
        _blk(2*(_B + _G), oy=_BH),
        _blk(2*(_B + _G), oy=2*_BH),
    ],

    # Ponte com espinhos nas pontas
    # Pula nos 2 blocos do meio evitando os espinhos das bordas
    [
        _spk(0.00),
        _blk(_S + _G),
        _blk(_S + _G + _B + _G),
        _spk(_S + _G + 2*_B + 2*_G),
    ],

    # Ponte longa com espinho no topo do bloco do meio
    # Plataforma de 3 blocos; o do meio tem espinho em cima (precisa pular)
    [
        _blk(0.00),
        _blk(_B + _G),
        _spk(_B + _G, oy=_BH),            # espinho sobre o bloco central
        _blk(2*(_B + _G)),
    ],

    # Torre dupla (2 blocos empilhados)
    [_blk(0.0), _blk(0.0, oy=_BH)],

    # Espinho + torre + espinho
    [_spk(0.0), _blk(_S + _G, h=_BH * 2.0), _spk(_S + _G + _B + _G)],

    # Plataforma elevada: bloco no ar com espinhos embaixo nas laterais
    # (bloco elevado em cima de coluna de 2, espinhos no chao nas pontas)
    [
        _spk(0.00),
        _blk(_S + _G),
        _blk(_S + _G, oy=_BH),             # topo da coluna (pousa aqui)
        _spk(_S + _G + _B + _G),
    ],

    # Escadinha com espinhos entre os degraus (inspirada no desenho da entrega)
    # Jogador sobe degraus alternando com espinhos no chão entre eles
    [
        _blk(0.00),                              # degrau 1 (1 bloco)
        _spk(_B + _G),                           # espinho entre 1 e 2
        _blk(_B + _G + _S + _G),                # degrau 2 (1 bloco)
        _blk(_B + _G + _S + _G, oy=_BH),        # degrau 2 topo (2 blocos)
        _spk(_B + _G + _S + _G + _B + _G),      # espinho entre 2 e 3
        _blk(_B + _G + _S + _G + _B + _G + _S + _G),           # degrau 3 base
        _blk(_B + _G + _S + _G + _B + _G + _S + _G, oy=_BH),  # degrau 3 meio
        _blk(_B + _G + _S + _G + _B + _G + _S + _G, oy=2*_BH),# degrau 3 topo
    ],
]

# ===========================================================================
# SEQUENCIAS DIFICEIS  (fase 3-4)
# ===========================================================================
SEQUENCES_HARD = [
    # 4 espinhos em 2 pares — gap no meio permite um duplo salto curto
    # (par 1: 2 espinhos próximos; pouso; par 2: mais 2 espinhos)
    [
        _spk(0.0), _spk(_S + _G),
        _spk(2*_S + 3*_G),                # gap maior entre os pares
        _spk(3*_S + 4*_G),
    ],

    # Escadinha 4 degraus com espinho apos a descida
    [
        # degrau 1
        _blk(0.00),
        # degrau 2
        _blk(_B+_G), _blk(_B+_G, oy=_BH),
        # degrau 3
        _blk(2*(_B+_G)), _blk(2*(_B+_G), oy=_BH), _blk(2*(_B+_G), oy=2*_BH),
        # espinho logo apos a descida
        _spk(3*(_B+_G)),
    ],

    # Labirinto espinho-bloco-espinho-bloco
    [_spk(0.0), _blk(_S+_G), _spk(_S+_G+_B+_G), _blk(2*_S+_B+3*_G)],

    # Ponte difícil: blocos com espinhos EM CIMA (precisa pular sobre eles)
    [
        _spk(0.00),
        _blk(_S+_G),       _spk(_S+_G, oy=_BH),
        _blk(_S+_G+_B+_G), _spk(_S+_G+_B+_G, oy=_BH),
        _spk(_S+_G+2*_B+2*_G),
    ],

    # Corredor: espinhos + torre alta no fim (pula os espinhos, despista a torre)
    [_spk(0.0), _spk(_S+_G), _blk(2*(_S+_G), h=_BH*3.0)],

    # Degraus alternados com espinhos no chao entre eles
    [
        _spk(0.00),
        _blk(_S+_G), _blk(_S+_G, oy=_BH),
        _spk(_S+_G+_B+_G),
        _blk(2*_S+_B+3*_G), _blk(2*_S+_B+3*_G, oy=_BH),
        _spk(2*_S+2*_B+4*_G),
    ],

    # Quatro espinhos com bloco de fuga no centro
    [
        _spk(0.0), _spk(_S+_G),
        _blk(2*(_S+_G)),
        _spk(2*(_S+_G)+_B+_G), _spk(3*_S+_B+3*_G),
    ],

    # Torre tripla com espinhos nas duas laterais
    [
        _spk(0.00),
        _blk(_S+_G, h=_BH*3),
        _spk(_S+_G+_B+_G),
    ],

    # Escadinha descendente (desce 3 niveis) + espinho no fim
    # (blocos decrecem em altura — jogador cai de plataforma em plataforma)
    [
        # plataforma alta (3 blocos)
        _blk(0.00), _blk(0.00, oy=_BH), _blk(0.00, oy=2*_BH),
        # plataforma media (2 blocos) a frente
        _blk(_B+_G), _blk(_B+_G, oy=_BH),
        # plataforma baixa (1 bloco) a frente
        _blk(2*(_B+_G)),
        # espinho no chao logo depois
        _spk(3*(_B+_G)),
    ],

    # Dois espinhos largos com bloco de fuga no meio (difícil mas passável)
    [
        _spk(0.0, w=0.10, h=0.14),
        _blk(0.10 + _G),
        _spk(0.10 + _G + _B + _G, w=0.10, h=0.14),
    ],
]

ALL_SEQUENCES = {
    'easy':   SEQUENCES_EASY,
    'medium': SEQUENCES_MEDIUM,
    'hard':   SEQUENCES_HARD,
}

# Distribuicao de dificuldade por fase (easy, medium, hard)
PHASE_DIFFICULTY_DIST = [
    (0.80, 0.20, 0.00),
    (0.55, 0.35, 0.10),
    (0.25, 0.50, 0.25),
    (0.10, 0.38, 0.52),
    (0.00, 0.20, 0.80),
]

# Para de spawnar X segundos antes do fim (deixa a tela limpa para a linha de chegada)
STOP_SPAWN_BEFORE_END = 9.0


# ---------------------------------------------------------------------------
# Classe de uma peca de obstaculo
# ---------------------------------------------------------------------------
class ObstaclePiece:
    def __init__(self):
        self.kind     = 'spike'
        self.position = np.array([OBSTACLE_DESPAWN_X - 2.0, GROUND_TOP_Y], dtype=float)
        self.width    = SPIKE_W
        self.height   = SPIKE_H
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
        self._pool        = [ObstaclePiece() for _ in range(self.POOL_SIZE)]
        self._spawn_timer = 0.0

    def update(self, dt: float, speed: float, spawn_interval: float,
               phase: int, elapsed: float, total_time: float):
        for p in self._pool:
            p.update(dt, speed)

        # Para de spawnar perto do fim
        if total_time - elapsed <= STOP_SPAWN_BEFORE_END:
            return

        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_sequence(phase)
            jitter = random.uniform(-SPAWN_JITTER, SPAWN_JITTER)
            self._spawn_timer = spawn_interval + jitter

    # ------------------------------------------------------------------ #
    def _pick_difficulty(self, phase: int) -> str:
        dist = PHASE_DIFFICULTY_DIST[min(phase, len(PHASE_DIFFICULTY_DIST) - 1)]
        r = random.random()
        if r < dist[0]:            return 'easy'
        elif r < dist[0]+dist[1]:  return 'medium'
        else:                      return 'hard'

    def _spawn_sequence(self, phase: int):
        difficulty = self._pick_difficulty(phase)
        seq = random.choice(ALL_SEQUENCES[difficulty])
        if not self._is_passable(seq):
            seq = [_spk(0.0)]
        for piece in seq:
            x = OBSTACLE_SPAWN_X + piece['ox']
            y = GROUND_TOP_Y     + piece['oy']
            self._activate_piece(piece['kind'], x, y, piece['w'], piece['h'])

    def _is_passable(self, seq: list) -> bool:
        for p in seq:
            if p['oy'] + p['h'] > SAFE_JUMP_HEIGHT:
                return False
        return True

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
        self._spawn_timer = 0.0