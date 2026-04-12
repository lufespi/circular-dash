# Circular Dash — Implementation Plan



## Context



Trabalho da disciplina de Computação Gráfica (UNISC, Prof. Rafael Peiter). O jogo é um clone inspirado no Geometry Dash chamado "Circular Dash", feito em Python com PyOpenGL + GLFW. O personagem é um círculo (daí o nome) que se mantém em X fixo enquanto a tela rola da direita para a esquerda. O jogador só pode pular (espaço) para desviar de obstáculos. A entrega é 03/05/2026.



**Restrição crítica:** A estrutura do programa deve seguir o padrão visto em aula (init GLFW → callbacks → loop principal com `update` + `render` usando delta time). Destoar disso desconta pontos.



---



## Bibliotecas permitidas



`PyOpenGL_accelerate`, `glfw`, `Pillow (PIL)`, `time`, `numpy`, `random`



---



## Estrutura de arquivos



```

circular-dash/

├── main.py          # GLFW init, window, callbacks, game loop (estrutura da aula)

├── game.py          # GameState: orquestra todos os subsistemas

├── player.py        # Player: física (gravidade, pulo), vidas, invencibilidade

├── obstacle.py      # Obstacle + ObstacleManager (pool de objetos, spawn aleatório)

├── level.py         # LevelManager: fases, velocidade, intervalo de spawn

├── collision.py     # Funções de detecção: círculo vs AABB

├── renderer.py      # Renderer: todos os glBegin/glEnd (círculo, quad, textura)

├── hud.py           # HUD: texto via Pillow → textura OpenGL, ícones de vida

└── constants.py     # Variáveis públicas de configuração (como o prof pede)

```



---



## constants.py — Variáveis públicas (requisito do professor)



```python

# Janela

WINDOW_WIDTH, WINDOW_HEIGHT = 800, 600

WINDOW_TITLE = "Circular Dash"



# Player

PLAYER_RADIUS        = 0.05    # NDC

PLAYER_X_NDC         = -0.6

PLAYER_GROUND_Y      = -0.7

PLAYER_JUMP_VELOCITY = 1.4     # NDC/s

GRAVITY              = -3.0    # NDC/s²

MAX_LIVES            = 3

INVINCIBILITY_DURATION = 2.0   # s



# Obstáculos

OBSTACLE_WIDTH       = 0.08

OBSTACLE_HEIGHT      = 0.15

OBSTACLE_SPAWN_X     = 1.2

OBSTACLE_DESPAWN_X   = -1.4

COLLISION_TOLERANCE  = 0.02



# Fases (dificuldade)

BASE_SCROLL_SPEED         = 0.4

SPEED_INCREMENT           = 0.12

BASE_SPAWN_INTERVAL       = 2.0

SPAWN_INTERVAL_DECREMENT  = 0.25

PHASE_SCORE_THRESHOLDS    = [0, 10, 25, 45, 70]



# Cores (RGBA)

COLOR_BG_TOP    = (0.05, 0.05, 0.20, 1.0)

COLOR_BG_BOTTOM = (0.10, 0.10, 0.35, 1.0)

COLOR_PLAYER    = (0.20, 0.80, 1.00, 1.0)

COLOR_OBSTACLE  = (1.00, 0.35, 0.15, 1.0)

COLOR_GROUND    = (0.15, 0.15, 0.30, 1.0)

```



Todas as coordenadas em NDC (-1 a +1). Evita conversões pixel↔NDC espalhadas pelo código.



---



## main.py — Estrutura da aula (GLFW)



```python

import glfw, time

from OpenGL.GL import *

from game import GameState

from constants import *



game = None

last_time = 0.0



def key_callback(window, key, scancode, action, mods):

    if key == glfw.KEY_SPACE  and action == glfw.PRESS: game.on_jump()

    if key == glfw.KEY_R      and action == glfw.PRESS: game.on_restart()

    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:

        glfw.set_window_should_close(window, True)



def main():

    global game, last_time

    glfw.init()

    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, None, None)

    glfw.make_context_current(window)

    glfw.set_key_callback(window, key_callback)

    glEnable(GL_BLEND)

    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)



    game = GameState()

    last_time = time.time()



    while not glfw.window_should_close(window):

        now   = time.time()

        delta = now - last_time

        last_time = now



        game.update(delta)

        glClear(GL_COLOR_BUFFER_BIT)

        game.render()



        glfw.swap_buffers(window)

        glfw.poll_events()



    glfw.terminate()

```



Callbacks são shims finos que delegam para `GameState`. Nenhuma lógica mora nos callbacks.



---



## game.py — GameState



```

update(dt):

  1. level_manager.update(score)

  2. player.update(dt)

  3. obstacle_manager.update(dt, scroll_speed, spawn_interval)

  4. check_collisions() → player.take_hit() → se lives==0: running=False

  5. score += scroll_speed * dt * SCORE_SCALE



render():

  1. renderer.draw_background()

  2. renderer.draw_ground()

  3. obstacle_manager.render(renderer)

  4. renderer.draw_player(player)

  5. hud.render(score, lives, phase, renderer)

  6. Se não running: renderer.draw_game_over_overlay()

```



---



## player.py — Física



- `position = np.array([PLAYER_X_NDC, PLAYER_GROUND_Y])` — vetor numpy

- `velocity = np.array([0.0, 0.0])`

- `update(dt)`: `velocity[1] += GRAVITY * dt` → `position += velocity * dt` → clamp no chão

- `jump()`: só aplica se `on_ground=True` → `velocity[1] = PLAYER_JUMP_VELOCITY`

- `take_hit()`: ignora se `inv_timer > 0`; senão `lives -= 1`, ativa invencibilidade

- `is_flashing`: alterna a cada 0.1s durante invencibilidade (feedback visual)



---



## obstacle.py — Pool + Spawn aleatório



**Obstacle:** `position: np.ndarray`, `width`, `height`, `active`

- `update(dt, speed)`: `position[0] -= speed * dt`

- `aabb`: retorna `(x+t, y+t, x+w-t, y+h-t)` com tolerância de colisão



**ObstacleManager:** pool fixo de 20 `Obstacle`

- `update(dt, speed, spawn_interval)`: move ativos, verifica timer de spawn

- `_spawn()`: pega objeto inativo do pool → `random.uniform(-0.04, 0.06)` para variação de altura

- Jitter de timing: timer reinicia em `random.uniform(-0.2, 0.1)` para ritmo irregular

- Fase 3+: `random.random() < 0.15` pula spawn (cria gap)



---



## level.py — Fases e dificuldade



```python

def update(self, score):

    # Descobre nova fase pelos thresholds

    # Se fase mudou → recalcula scroll_speed e spawn_interval



scroll_speed   = BASE_SCROLL_SPEED   + SPEED_INCREMENT        * (phase - 1)

spawn_interval = BASE_SPAWN_INTERVAL - SPAWN_INTERVAL_DECREMENT * (phase - 1)

spawn_interval = max(0.4, spawn_interval)  # piso mínimo

```



| Fase | Score | Velocidade | Intervalo |

|------|-------|-----------|-----------|

| 1    | 0     | 0.40      | 2.00s     |

| 2    | 10    | 0.52      | 1.75s     |

| 3    | 25    | 0.64      | 1.50s     |

| 4    | 45    | 0.76      | 1.25s     |

| 5    | 70    | 0.88      | 1.00s     |



---



## collision.py



```python

def circle_aabb_collision(center: np.ndarray, radius, aabb) -> bool:

    cx, cy = center

    x0, y0, x1, y1 = aabb

    closest = np.array([np.clip(cx, x0, x1), np.clip(cy, y0, y1)])

    diff = center - closest

    return float(diff @ diff) < radius * radius

```



Teste círculo vs AABB via ponto mais próximo (np.clip). Correto para o personagem circular.



---



## renderer.py — Pipeline OpenGL (fixed-function, estilo aula)



- `draw_background()`: `GL_QUADS` com cor por vértice (gradiente)

- `draw_ground()`: quad retangular

- `draw_circle(cx, cy, r, color, flash)`: `GL_TRIANGLE_FAN` com `CIRCLE_SEGMENTS=32`

- `draw_obstacle(ob)`: quad colorido

- `draw_texture_quad(tex_id, x, y, w, h)`: `GL_QUADS` com `glTexCoord2f` (UV invertido PIL↔OpenGL)



---



## hud.py — Texto com Pillow → Textura OpenGL



Pipeline: `string` → `PIL Image (RGBA)` → `img.tobytes("raw","RGBA")` → `glTexImage2D`



- Texturas de score e fase são regeneadas **somente quando o valor muda** (dirty flag)

- Ícones de vida: 3 círculos OpenGL no canto superior direito (cheios = vida, cinza = perdida)



---



## Critérios de avaliação cobertos



| Critério | Arquivo(s) | Mecanismo |

|----------|-----------|-----------|

| Personagem se movimenta (1 pt) | `player.py` | gravidade + integração euler + pulo |

| Colisão (1 pt) | `collision.py` | circle vs AABB com `np.clip` |

| Vidas + game over (2 pts) | `player.py`, `hud.py` | `take_hit()`, invencibilidade, ícones |

| Fases aleatórias + dificuldade (3 pts) | `obstacle.py`, `level.py` | pool + `random`, thresholds de fase |

| Apresentação (3 pts) | todos | gradiente, flash, HUD completo |



---



## Verificação / Como testar



1. `pip install PyOpenGL PyOpenGL_accelerate glfw Pillow numpy`

2. `python main.py` — janela deve abrir com fundo gradiente e círculo no chão

3. Pressionar **Espaço** → player pula e retorna ao chão

4. Aguardar ~2s → obstáculo aparece da direita e rola para a esquerda

5. Colidir com obstáculo → player pisca (invencibilidade), vida diminui no HUD

6. 3 colisões → tela de game over

7. Pressionar **R** → reinicia

8. Atingir score 10 → velocidade aumenta visivelmente (fase 2)

