"""Entidades de obstáculo e gerenciamento de spawn por sequências pré-definidas por fase.

Tipos:
  'spike'  — espinho triangular; qualquer toque tira vida.
  'block'  — bloco sólido; topo é superfície segura, lados/base tiram vida.

Cada sequência é lista de dicts:  kind, ox, oy, w, h
  ox  — offset X a partir do ponto de spawn (NDC)
  oy  — offset Y a partir do GROUND_TOP_Y (0 = chão, positivo = elevado)

Regra de composição visual:
  Blocos que devem ficar "colados" são representados como UMA peça maior:
    lado a lado  → _blk(ox, w=2*_B)   (bloco largo)
    empilhados   → _blk(ox, h=2*_H)   (bloco alto) / h=3*_H etc.

Seleção: round-robin por fase, com stair-guard — depois de uma sequência com
  plataforma elevada (oy > 0), o gerador pula automaticamente qualquer sequência
  cujo primeiro elemento seja um espinho ao nível do chão.
"""

import random
import numpy as np
from constants import (
    OBSTACLE_SPAWN_X, OBSTACLE_DESPAWN_X,
    COLLISION_TOLERANCE, GROUND_TOP_Y,
    SPAWN_JITTER,
)

# ---------------------------------------------------------------------------
# Dimensões base
# ---------------------------------------------------------------------------
SPK_W = 0.08
SPK_H = 0.13
BLK_W = 0.13
BLK_H = 0.13

_S  = SPK_W
_B  = BLK_W
_H  = BLK_H
_G  = 0.04    # gap entre peças distintas que se encostam
_J0 = 0.42    # gap extra-largo (P0 — iniciantes)
_J  = 0.30    # gap confortável (P1–P2)
_JM = 0.22    # gap médio      (P2–P3)
_JS = 0.14    # gap curto      (P3–P4)

# Física do jogador (espelhado de constants.py)
_JUMP_VEL    = 2.0
_GRAVITY_ABS = 5.0
JUMP_MAX_H   = (_JUMP_VEL ** 2) / (2 * _GRAVITY_ABS)   # ≈ 0.40 NDC

STOP_SPAWN_BEFORE_END = 9.0


def _spk(ox, oy=0.0, w=SPK_W, h=SPK_H):
    return dict(kind='spike', ox=ox, oy=oy, w=w, h=h)

def _blk(ox, oy=0.0, w=BLK_W, h=BLK_H):
    return dict(kind='block', ox=ox, oy=oy, w=w, h=h)


# ---------------------------------------------------------------------------
# Utilitários — stair guard
# ---------------------------------------------------------------------------

def is_stair(seq: list) -> bool:
    """True se a sequência contém um bloco com plataforma elevada (oy > 0).

    Após uma sequência de escadinha, o jogador pode estar em queda livre.
    Isso sinaliza ao gerador que a PRÓXIMA sequência não deve começar com
    um espinho ao nível do chão.
    """
    return any(p['kind'] == 'block' and p['oy'] > 0.0 for p in seq)


def _starts_with_spike(seq: list) -> bool:
    """True se o primeiro elemento da sequência (menor ox) é espinho no chão."""
    if not seq:
        return False
    first = min(seq, key=lambda p: p['ox'])
    return first['kind'] == 'spike' and first['oy'] < 0.01


# ===========================================================================
# FASE 0 — Futurista  (0–35 s)  ·  Muito Fácil
#
#  Regras:
#   • Espinhos sempre isolados — nunca dois lado a lado
#   • Nunca blocos empilhados na mesma coluna
#   • Escadinhas: máx. 2 degraus, regra 2H:1V
#     (cada degrau = bloco largo w=2×BW; subida = 1×BH)
#   • Gaps generosos: _J0 = 0.42 NDC entre obstáculos consecutivos
#
#  Ordem round-robin projetada para que staircases (idx 4 e 7) sejam
#  seguidas por sequências que NÃO começam com espinho (stair-guard de backup):
#    idx 4 (stair) → idx 5 (bloco+espinho distante, começa com bloco) ✓
#    idx 7 (stair) → wrap → idx 0 (bloco isolado) ✓
# ===========================================================================
SEQUENCES_P0 = [
    # 0 — Bloco isolado  (obstáculo mais simples)
    [_blk(0.0)],

    # 1 — Plataforma larga  (bloco 2× de largura, sem costura)
    [_blk(0.0, w=2*_B)],

    # 2 — Espinho isolado  (salto básico)
    [_spk(0.0)],

    # 2b — [GAP VAZIO — respiro para o jogador sem obstáculos]
    [],

    # 3 — Dois espinhos com gap extra-largo  (dois saltos independentes)
    [_spk(0.0), _spk(_S + _J0)],

    # 4 — Escadinha ascendente 2 degraus  ← STAIR
    #     Degrau 1 = bloco largo ao nível do chão
    #     Degrau 2 = bloco largo 1×BH acima, 2×BW à frente
    [
        _blk(0.0, w=2*_B),
        _blk(2*_B + _G, oy=_H, w=2*_B),
    ],

    # 5 — Bloco + espinho distante  (começa com bloco → seguro após stair idx 4)
    [_blk(0.0), _spk(_B + _J0)],

    # 6 — Escadinha 2 degraus + plataforma de aterrissagem  ← STAIR
    #     Bloco final serve de zona de pouso após a descida
    [
        _blk(0.0, w=2*_B),
        _blk(2*_B + _G, oy=_H, w=2*_B),
        _blk(4*_B + 2*_G + _J0),
    ],
    # wrap → idx 0 (bloco isolado) — seguro após stair ✓
]


# ===========================================================================
# FASE 1 — Era Moderna  (35–65 s)  ·  Fácil-Médio
#
#  Novidades: torres h=2×BH (peça única), combo bloco+espinho no topo,
#             escadinha 3 colunas crescentes (1H→2H→3H), gaps reduzidos.
#
#  Nenhuma sequência tem oy > 0 → is_stair sempre False → stair-guard inativo.
#  Ordering: índices 0–3 iniciam com bloco (tranquilos); 4–7 com espinho.
# ===========================================================================
SEQUENCES_P1 = [
    # 0 — Torre 2×BH  (peça única, sem costura)
    [_blk(0.0, h=2*_H)],

    # 1 — Bloco + espinho no topo  (combo; jogador pula o conjunto inteiro)
    [_blk(0.0), _spk(0.0, oy=_H)],

    # 2 — Escadinha 3 colunas crescentes  (1H → 2H → 3H)
    [
        _blk(0.0),
        _blk(_B + _G, h=2*_H),
        _blk(2*(_B + _G), h=3*_H),
    ],

    # 3 — Torre 2×BH + espinho depois  (começa com bloco)
    [_blk(0.0, h=2*_H), _spk(_B + _J)],

    # 4 — 3 espinhos com gap médio  ← SPIKE
    [_spk(0.0), _spk(_S + 0.22), _spk(2*_S + 0.44)],

    # 5 — 2 espinhos próximos + bloco distante  ← SPIKE
    [_spk(0.0), _spk(_S + _G), _blk(2*_S + 2*_G + _J)],

    # 6 — Espinho + torre(2H) + espinho  ← SPIKE
    [_spk(0.0), _blk(_S + _G, h=2*_H), _spk(_S + _G + _B + _G)],

    # 7 — Espinho + escadinha 3 colunas  ← SPIKE
    [_spk(0.0), _blk(_S + _J, h=2*_H), _blk(_S + _J + _B + _G, h=3*_H)],
]


# ===========================================================================
# FASE 2 — Revolução Industrial  (65–106 s)  ·  Médio
#
#  Torres máx. 2.5×BH; gaps _JM=0.22; 1 respiro vazio; ~4 SPIKE-starters.
#  Progressão: respiro → single → combos torre/spike → labirinto simples.
# ===========================================================================
SEQUENCES_P2 = [
    # 0 — Respiro  (sem obstáculos — transição suave ao entrar em P2)
    [],

    # 1 — Torre 2.5×BH  (peça única, máximo desta fase)
    [_blk(0.0, h=_H * 2.5)],

    # 2 — Bloco + espinho a _JM de gap
    [_blk(0.0), _spk(_B + _JM)],

    # 3 — Torre(2H) + espinho _G + bloco  (3 elementos, NON-SPIKE)
    [_blk(0.0, h=2*_H), _spk(_B + _G), _blk(_B + _G + _S + _JM)],

    # 4 — Espinho + torre(2H) + espinho  ← SPIKE
    [_spk(0.0), _blk(_S + _G, h=2*_H), _spk(_S + _G + _B + _G)],

    # 5 — Par próximo + bloco a _JM  ← SPIKE
    [_spk(0.0), _spk(_S + _G), _blk(2*_S + 2*_G + _JM)],

    # 6 — Ponte: spike–bloco–bloco–spike  ← SPIKE
    [
        _spk(0.0),
        _blk(_S + _G), _blk(_S + _G + _B + _G),
        _spk(_S + _G + 2*_B + 2*_G),
    ],

    # 7 — 3 espinhos com gap _JM entre cada  ← SPIKE
    [_spk(0.0), _spk(_S + _JM), _spk(2*_S + 2*_JM)],
]


# ===========================================================================
# FASE 3 — Era Medieval  (106–138 s)  ·  Difícil
#
#  Torres máx. 3×BH; gaps _JS=0.14; ~5 SPIKE-starters.
#  idx 0 é escadinha com plataforma elevada (oy=_H > 0) → stair-guard ativo.
#  idx 1 NON-SPIKE por design: seguro após stair na ordenação round-robin.
# ===========================================================================
SEQUENCES_P3 = [
    # 0 — Plataforma elevada descendente  ← STAIR  (bloco oy=_H → chão + espinho)
    #     is_stair=True → stair-guard previne spike-starter na próxima sequência.
    [
        _blk(0.0, oy=_H, w=2*_B),
        _blk(2*_B + _G),
        _spk(3*_B + _G + _JS),
    ],

    # 1 — Escadinha crescente 1H→2H→3H + espinho  (NON-SPIKE — seguro após stair)
    [
        _blk(0.0),
        _blk(_B + _G, h=2*_H),
        _blk(2*(_B + _G), h=3*_H),
        _spk(3*(_B + _G)),
    ],

    # 2 — Torre(3H) + espinho _JS + torre(2H)  (NON-SPIKE)
    [_blk(0.0, h=3*_H), _spk(_B + _JS), _blk(_B + _JS + _S + _G, h=2*_H)],

    # 3 — Espinho + torre(3H) + espinho  ← SPIKE
    [_spk(0.0), _blk(_S + _G, h=3*_H), _spk(_S + _G + _B + _G)],

    # 4 — Labirinto alternado spike-blk-spike-blk  ← SPIKE
    [
        _spk(0.0), _blk(_S + _G),
        _spk(_S + _G + _B + _G),
        _blk(2*_S + _B + 3*_G),
    ],

    # 5 — Torres 2H alternadas com espinhos entre elas  ← SPIKE  (5 elementos)
    [
        _spk(0.0),
        _blk(_S + _G, h=2*_H),
        _spk(_S + _G + _B + _G),
        _blk(2*_S + _B + 3*_G, h=2*_H),
        _spk(2*_S + 2*_B + 4*_G),
    ],

    # 6 — Par de espinhos + torre(3H)  ← SPIKE
    [_spk(0.0), _spk(_S + _G), _blk(2*_S + 2*_G + _JS, h=3*_H)],

    # 7 — Espinhões largos (w=0.10) + bloco de fuga  ← SPIKE
    [
        _spk(0.0,                  w=0.10, h=0.14),
        _blk(0.10 + _G),
        _spk(0.10 + _G + _B + _G, w=0.10, h=0.14),
    ],
]


# ===========================================================================
# FASE 4 — Pré-História  (138–168 s)  ·  Muito Difícil
#
#  Sem oy>0 (nenhuma plataforma elevada); gaps _JS=0.14; ~6 SPIKE-starters.
#  3–6 elementos por seq; espinhões w=0.10 em seq 6; sem respiros.
# ===========================================================================
SEQUENCES_P4 = [
    # 0 — Descida 3H→2H→1H + espinhos duplos  (NON-SPIKE)
    [
        _blk(0.0, h=3*_H),
        _blk(_B + _G, h=2*_H),
        _blk(2*(_B + _G)),
        _spk(3*(_B + _G)), _spk(3*(_B + _G) + _S + _G),
    ],

    # 1 — Par de espinhos + torre(3H)  ← SPIKE
    [_spk(0.0), _spk(_S + _G), _blk(2*_S + 2*_G, h=3*_H)],

    # 2 — Escadinha densa 1H→2H→3H + espinho  (NON-SPIKE, gaps mínimos _G)
    [
        _blk(0.0),
        _blk(_B + _G, h=2*_H),
        _blk(2*(_B + _G), h=3*_H),
        _spk(3*(_B + _G)),
    ],

    # 3 — Labirinto 5 elementos spike-blk alternado  ← SPIKE
    [
        _spk(0.0),
        _blk(_S + _G),
        _spk(_S + _G + _B + _G),
        _blk(2*_S + _B + 3*_G),
        _spk(2*_S + 2*_B + 4*_G),
    ],

    # 4 — Torre(3H) flanqueada por pares de espinhos  ← SPIKE
    [
        _spk(0.0), _spk(_S + _G),
        _blk(2*_S + 2*_G, h=3*_H),
        _spk(2*_S + 2*_G + _B + _G), _spk(3*_S + 2*_G + _B + 2*_G),
    ],

    # 5 — 4 espinhos consecutivos  ← SPIKE
    [_spk(0.0), _spk(_S + _G), _spk(2*(_S + _G)), _spk(3*(_S + _G))],

    # 6 — Espinhões largos (w=0.10) + bloco de fuga  ← SPIKE
    [
        _spk(0.0,                  w=0.10, h=0.14),
        _blk(0.10 + _G),
        _spk(0.10 + _G + _B + _G, w=0.10, h=0.14),
    ],

    # 7 — Sequência mista máxima (6 elementos)  ← SPIKE
    [
        _spk(0.0),
        _blk(_S + _G, h=2*_H),
        _spk(_S + _G + _B + _G), _spk(_S + _G + _B + _G + _S + _G),
        _blk(_S + _G + _B + 3*_G + 2*_S, h=3*_H),
        _spk(_S + _G + 2*_B + 4*_G + 2*_S),
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
# Classe de uma peça de obstáculo
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
        # Round-robin: índice independente por fase
        self._seq_indices   = [0] * len(SEQUENCES_PHASE)
        # Stair-guard: True se a última sequência continha plataforma elevada
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

        # Stair-guard: pula sequências que começam com espinho se o jogador
        # pode estar em queda livre após uma plataforma elevada.
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
