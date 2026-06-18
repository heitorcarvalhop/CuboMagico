"""
cube.py
-------
Representação 3D e lógica de estado do Cubo Mágico 3x3x3.

Cada peça visível do cubo (26 ao todo: 8 vértices + 12 arestas + 6 centros)
é um Entity da Ursina com uma malha (Mesh) colorida individualmente em cada
face. A posição de cada peça na grade 3x3x3 (-1, 0 ou 1 em cada eixo) É o
estado interno do cubo: não existe uma matriz de estado separada, a própria
cena 3D representa o estado, o que evita duplicação e bugs de sincronização.

Os 12 movimentos padrão (U, U', D, D', L, L', R, R', F, F', B, B') são
implementados girando, em torno de um pivô temporário, as 9 peças que
pertencem à camada correspondente.
"""
import random
from collections import deque

from ursina import Entity, Mesh, Vec3, Audio, color, curve, destroy, Func


# ---------------------------------------------------------------------------
# Esquema de cores oficial do cubo mágico
# ---------------------------------------------------------------------------
COLOR_WHITE = color.rgb32(255, 255, 255)
COLOR_YELLOW = color.rgb32(255, 213, 0)
COLOR_RED = color.rgb32(196, 30, 58)
COLOR_ORANGE = color.rgb32(255, 88, 0)
COLOR_BLUE = color.rgb32(0, 70, 173)
COLOR_GREEN = color.rgb32(0, 158, 96)
COLOR_BODY = color.black  # cor do "plástico" do cubo (faces internas)

# Letra de cada cor, no formato usado pela biblioteca de resolução cube_solver
# (que usa exatamente o mesmo esquema de cores que o nosso: U=branco, F=verde,
# R=vermelho, D=amarelo, B=azul, L=laranja)
COLOR_LETTER = {
    'top': 'W', 'bottom': 'Y', 'front': 'G', 'back': 'B', 'right': 'R', 'left': 'O',
}

# Lista com os 12 movimentos possíveis
MOVE_NAMES = ['U', "U'", 'D', "D'", 'L', "L'", 'R', "R'", 'F', "F'", 'B', "B'"]

# Definição geométrica de cada movimento: eixo de rotação, camada (-1/0/1)
# e sentido da rotação (+1 ou -1), aplicado ao pivô em torno da origem.
MOVES = {
    'U':  {'axis': 'y', 'layer': 1, 'dir': -1},
    "U'": {'axis': 'y', 'layer': 1, 'dir': 1},
    'D':  {'axis': 'y', 'layer': -1, 'dir': 1},
    "D'": {'axis': 'y', 'layer': -1, 'dir': -1},
    'R':  {'axis': 'x', 'layer': 1, 'dir': -1},
    "R'": {'axis': 'x', 'layer': 1, 'dir': 1},
    'L':  {'axis': 'x', 'layer': -1, 'dir': 1},
    "L'": {'axis': 'x', 'layer': -1, 'dir': -1},
    'F':  {'axis': 'z', 'layer': 1, 'dir': 1},
    "F'": {'axis': 'z', 'layer': 1, 'dir': -1},
    'B':  {'axis': 'z', 'layer': -1, 'dir': -1},
    "B'": {'axis': 'z', 'layer': -1, 'dir': 1},
}

FACES = ['U', 'D', 'L', 'R', 'F', 'B']

# Para cada face, a direção (no mundo) que aponta "para fora" dela.
FACE_WORLD_DIR = {
    'U': Vec3(0, 1, 0), 'D': Vec3(0, -1, 0),
    'L': Vec3(-1, 0, 0), 'R': Vec3(1, 0, 0),
    'F': Vec3(0, 0, 1), 'B': Vec3(0, 0, -1),
}

# Nome local da face de uma peça (usado em cubie.face_colors) -> letra da face do cubo
LOCAL_TO_FACE = {'top': 'U', 'bottom': 'D', 'left': 'L', 'right': 'R', 'front': 'F', 'back': 'B'}

# Para cada face, as coordenadas de grade (x,y,z) das 9 peças que a compõem,
# na ordem padrão usada por bibliotecas de resolução (linha a linha, de cima
# para baixo e da esquerda para a direita, olhando para a face pelo lado de
# fora com U para cima). Essa convenção foi conferida contra a tabela oficial
# de adjacência de cantos do algoritmo de Kociemba (cornerFacelet).
FACELET_GRID = {
    'U': [(-1, 1, -1), (0, 1, -1), (1, 1, -1),
          (-1, 1, 0), (0, 1, 0), (1, 1, 0),
          (-1, 1, 1), (0, 1, 1), (1, 1, 1)],
    'L': [(-1, 1, -1), (-1, 1, 0), (-1, 1, 1),
          (-1, 0, -1), (-1, 0, 0), (-1, 0, 1),
          (-1, -1, -1), (-1, -1, 0), (-1, -1, 1)],
    'F': [(-1, 1, 1), (0, 1, 1), (1, 1, 1),
          (-1, 0, 1), (0, 0, 1), (1, 0, 1),
          (-1, -1, 1), (0, -1, 1), (1, -1, 1)],
    'R': [(1, 1, 1), (1, 1, 0), (1, 1, -1),
          (1, 0, 1), (1, 0, 0), (1, 0, -1),
          (1, -1, 1), (1, -1, 0), (1, -1, -1)],
    'B': [(1, 1, -1), (0, 1, -1), (-1, 1, -1),
          (1, 0, -1), (0, 0, -1), (-1, 0, -1),
          (1, -1, -1), (0, -1, -1), (-1, -1, -1)],
    'D': [(-1, -1, 1), (0, -1, 1), (1, -1, 1),
          (-1, -1, 0), (0, -1, 0), (1, -1, 0),
          (-1, -1, -1), (0, -1, -1), (1, -1, -1)],
}

# Ordem de faces esperada pela biblioteca de resolução (cube_solver)
SOLVER_FACE_ORDER = 'ULFRBD'


def inverse_move(move):
    """Retorna o movimento inverso. Ex.: 'U' -> "U'", "R'" -> 'R'."""
    return move[:-1] if move.endswith("'") else move + "'"


# ---------------------------------------------------------------------------
# Som (efeito simples ao girar uma face)
# ---------------------------------------------------------------------------
_click_sound = None
_sound_enabled = True


def init_sound():
    """Carrega o efeito sonoro. Deve ser chamado depois de Ursina() existir."""
    global _click_sound
    try:
        _click_sound = Audio('square', volume=0.12, pitch=2.2, loop=False, autoplay=False)
    except Exception:
        _click_sound = None


def set_sound_enabled(enabled):
    global _sound_enabled
    _sound_enabled = enabled


def play_click_sound():
    if _sound_enabled and _click_sound is not None:
        try:
            _click_sound.play()
        except Exception:
            pass


def _cubie_mesh(face_colors):
    """Gera um Mesh de cubo com uma cor independente em cada uma das 6 faces."""
    faces = {
        'right':  [Vec3(.5, -.5, -.5), Vec3(.5, .5, -.5), Vec3(.5, .5, .5), Vec3(.5, -.5, .5)],
        'left':   [Vec3(-.5, -.5, .5), Vec3(-.5, .5, .5), Vec3(-.5, .5, -.5), Vec3(-.5, -.5, -.5)],
        'top':    [Vec3(-.5, .5, -.5), Vec3(-.5, .5, .5), Vec3(.5, .5, .5), Vec3(.5, .5, -.5)],
        'bottom': [Vec3(-.5, -.5, .5), Vec3(-.5, -.5, -.5), Vec3(.5, -.5, -.5), Vec3(.5, -.5, .5)],
        'front':  [Vec3(-.5, -.5, .5), Vec3(.5, -.5, .5), Vec3(.5, .5, .5), Vec3(-.5, .5, .5)],
        'back':   [Vec3(.5, -.5, -.5), Vec3(-.5, -.5, -.5), Vec3(-.5, .5, -.5), Vec3(.5, .5, -.5)],
    }
    vertices, triangles, vcolors = [], [], []
    for name, verts in faces.items():
        base = len(vertices)
        vertices.extend(verts)
        face_color = face_colors.get(name, COLOR_BODY)
        vcolors.extend([face_color] * 4)
        triangles.extend([base, base + 1, base + 2, base + 2, base + 3, base])
    return Mesh(vertices=vertices, triangles=triangles, colors=vcolors, mode='triangle')


class RubiksCube(Entity):
    """Cubo mágico 3x3x3 jogável em 3D: contém as 26 peças e os movimentos."""

    SPACING = 1.02   # distância entre os centros das peças (gera as frestas pretas)
    GAP_SCALE = 0.95  # escala de cada peça (menor que SPACING -> aparecem frestas)
    EXPLODE_FACTOR = 0.8  # afastamento extra de cada peça no modo "explodido"

    def __init__(self):
        super().__init__()
        self.cubies = []           # as 26 peças (Entities)
        self.history = []          # movimentos realizados desde o último estado resolvido
        self.animating = False     # True enquanto alguma animação de giro está rodando
        self.exploded = False      # True enquanto o modo de visualização "explodido" está ativo
        self._highlight = None
        self._generation = 0       # incrementado a cada reset, para invalidar animações antigas em andamento
        self._build()

    # ----------------------------------------------------------------- build
    def _build(self):
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                for z in (-1, 0, 1):
                    if x == 0 and y == 0 and z == 0:
                        continue  # núcleo interno não existe fisicamente no cubo real
                    face_colors = {}
                    if x == 1:
                        face_colors['right'] = COLOR_RED
                    if x == -1:
                        face_colors['left'] = COLOR_ORANGE
                    if y == 1:
                        face_colors['top'] = COLOR_WHITE
                    if y == -1:
                        face_colors['bottom'] = COLOR_YELLOW
                    if z == 1:
                        face_colors['front'] = COLOR_GREEN
                    if z == -1:
                        face_colors['back'] = COLOR_BLUE

                    cubie = Entity(
                        parent=self,
                        model=_cubie_mesh(face_colors),
                        position=Vec3(x, y, z) * self.SPACING,
                        scale=self.GAP_SCALE,
                        double_sided=True,
                    )
                    cubie.grid_origin = Vec3(x, y, z)  # posição "resolvida" original
                    cubie.face_colors = face_colors    # nomes locais coloridos ('top', 'right', ...)
                    self.cubies.append(cubie)

    def reset_instant(self):
        """Reconstrói o cubo no estado resolvido, sem animação.

        Pode ser chamado mesmo com um movimento em andamento: o contador
        `_generation` é incrementado para que o callback de finalização de
        qualquer animação antiga em andamento perceba que suas peças já
        não existem mais e não tente mexer nelas (ver `apply_move`).
        """
        self._generation += 1
        for c in self.cubies:
            destroy(c)
        self.cubies.clear()
        self.history.clear()
        self.animating = False
        self._hide_highlight()
        self._build()

    def set_exploded(self, exploded, duration=0.4):
        """Ativa/desativa o modo de visualização 'explodido', afastando cada
        peça do centro proporcionalmente à sua posição atual na grade (então
        funciona em qualquer estado, não só no cubo resolvido). É puramente
        visual: a posição usada pela lógica dos movimentos continua sendo a
        posição "real" (sem o afastamento), por isso giros não devem ser
        feitos enquanto o cubo está explodido (ver `CubeControls`)."""
        # usa a escala ATUAL (antes da troca) para recuperar a coordenada de
        # grade corretamente, já que a posição de uma peça explodida usa uma
        # escala diferente da posição normal (SPACING simples)
        old_scale = self.SPACING + (self.EXPLODE_FACTOR if self.exploded else 0.0)
        new_scale = self.SPACING + (self.EXPLODE_FACTOR if exploded else 0.0)
        for c in self.cubies:
            gx = round(c.x / old_scale)
            gy = round(c.y / old_scale)
            gz = round(c.z / old_scale)
            target = Vec3(gx, gy, gz) * new_scale
            c.animate_position(target, duration=duration, curve=curve.in_out_quad)
        self.exploded = exploded

    # ------------------------------------------------------------- consultas
    def is_solved(self):
        """Verifica se toda peça está na posição e orientação originais.

        Só checamos a orientação das faces que realmente têm uma cor pintada
        (`cubie.face_colors`). Isso importa para as peças de centro: elas têm
        só 1 face colorida, então podem girar em torno do próprio eixo (ex.:
        depois de um número ímpar de giros U) sem que isso seja visível no
        cubo real — checar um eixo sem cor (como `forward` de um centro)
        causaria falsos negativos.
        """
        for c in self.cubies:
            pos = c.position / self.SPACING
            if round(pos.x) != c.grid_origin.x or round(pos.y) != c.grid_origin.y or round(pos.z) != c.grid_origin.z:
                return False
            local_dirs = {
                'right': c.right, 'left': -c.right,
                'top': c.up, 'bottom': -c.up,
                'front': c.forward, 'back': -c.forward,
            }
            for local_name in c.face_colors:
                current = local_dirs[local_name].normalized()
                expected = FACE_WORLD_DIR[LOCAL_TO_FACE[local_name]]
                if current.dot(expected) < 0.99:
                    return False
        return True

    def _layer_cubies(self, axis, layer):
        return [c for c in self.cubies if round(getattr(c, axis) / self.SPACING) == layer]

    def _cubie_at(self, x, y, z):
        for c in self.cubies:
            pos = c.position / self.SPACING
            if round(pos.x) == x and round(pos.y) == y and round(pos.z) == z:
                return c
        return None

    @staticmethod
    def _facelet_letter(cubie, world_dir):
        """Descobre qual face LOCAL da peça está atualmente voltada para a
        direção `world_dir` do mundo, e devolve a letra da cor pintada nela."""
        local_dirs = {
            'right': cubie.right, 'left': -cubie.right,
            'top': cubie.up, 'bottom': -cubie.up,
            'front': cubie.forward, 'back': -cubie.forward,
        }
        best_name, best_dot = None, -2
        for name, vec in local_dirs.items():
            d = vec.normalized().dot(world_dir)
            if d > best_dot:
                best_dot, best_name = d, name
        return COLOR_LETTER[best_name] if best_name in cubie.face_colors else None

    def get_facelet_string(self):
        """Lê o estado atual do cubo como uma string de 54 letras (W/G/R/Y/B/O),
        no formato e na ordem de faces (U,L,F,R,B,D) esperados pela biblioteca
        de resolução `cube_solver`."""
        chars = []
        for face in SOLVER_FACE_ORDER:
            world_dir = FACE_WORLD_DIR[face]
            for (x, y, z) in FACELET_GRID[face]:
                cubie = self._cubie_at(x, y, z)
                chars.append(self._facelet_letter(cubie, world_dir))
        return ''.join(chars)

    # --------------------------------------------------------------- giros
    def _show_highlight(self, axis, layer):
        size = 3.05 * self.SPACING
        thin = 0.05
        scales = {'x': Vec3(thin, size, size), 'y': Vec3(size, thin, size), 'z': Vec3(size, size, thin)}
        pos = Vec3(0, 0, 0)
        setattr(pos, axis, layer * self.SPACING)
        self._highlight = Entity(parent=self, model='cube', color=color.cyan, position=pos,
                                  scale=scales[axis], unlit=True)
        self._highlight.alpha = 0.30

    def _hide_highlight(self):
        if self._highlight is not None:
            destroy(self._highlight)
            self._highlight = None

    def apply_move(self, move, duration=0.3, on_complete=None, sound=True, record=False):
        """Executa um único movimento (ex.: 'U', "R'"), animando a face em 90 graus."""
        info = MOVES[move]
        axis, layer, direction = info['axis'], info['layer'], info['dir']
        layer_cubies = self._layer_cubies(axis, layer)
        generation = self._generation
        self.animating = True

        if record:
            self.history.append(move)

        pivot = Entity(parent=self)
        for c in layer_cubies:
            c.world_parent = pivot

        self._show_highlight(axis, layer)
        if sound:
            play_click_sound()

        angle = direction * 90
        rotation_attr = f'rotation_{axis}'

        def _finish():
            if generation != self._generation:
                # o cubo foi resetado enquanto este movimento ainda animava;
                # as peças desta camada já foram destruídas pelo reset, então
                # só descartamos o pivô órfão e não chamamos on_complete
                # (isso encerra naturalmente qualquer fila de movimentos antiga).
                destroy(pivot)
                return
            for c in layer_cubies:
                c.world_parent = self
                c.x = round(c.x / self.SPACING) * self.SPACING
                c.y = round(c.y / self.SPACING) * self.SPACING
                c.z = round(c.z / self.SPACING) * self.SPACING
                c.rotation_x = round(c.rotation_x / 90) * 90
                c.rotation_y = round(c.rotation_y / 90) * 90
                c.rotation_z = round(c.rotation_z / 90) * 90
            destroy(pivot)
            self._hide_highlight()
            self.animating = False
            if on_complete:
                on_complete(move)

        if duration > 0:
            # Encadeia o callback de finalização na PRÓPRIA Sequence da animação
            # (em vez de um invoke() paralelo) para garantir que _finish() só
            # rode depois que a rotação tiver realmente sido aplicada ao pivô,
            # mesmo em quadros lentos ou com durações muito curtas.
            sequence = pivot.animate(rotation_attr, angle, duration=duration, curve=curve.in_out_quad)
            sequence.append(Func(_finish))
        else:
            setattr(pivot, rotation_attr, angle)
            _finish()

    def queue_moves(self, moves, duration=0.3, on_each=None, on_done=None, sound=True, record=False):
        """Executa uma sequência de movimentos, um após o outro, sem travar a interface."""
        pending = deque(moves)

        def _step():
            if not pending:
                self.animating = False
                if on_done:
                    on_done()
                return
            self.animating = True
            move = pending.popleft()

            def _complete(m):
                if on_each:
                    on_each(m)
                _step()

            self.apply_move(move, duration=duration, on_complete=_complete, sound=sound, record=record)

        _step()

    # ------------------------------------------------------------ embaralhar
    def scramble(self, n=20, duration=0.15, on_each=None, on_done=None):
        """Embaralha o cubo com `n` movimentos aleatórios (mínimo 20) e guarda o histórico."""
        n = max(20, int(n))
        moves = []
        last_face = None
        for _ in range(n):
            face = random.choice(FACES)
            while face == last_face:
                face = random.choice(FACES)
            last_face = face
            move = face if random.random() < 0.5 else face + "'"
            moves.append(move)

        self.history.extend(moves)
        print('Embaralhando:', ' '.join(moves))
        self.queue_moves(moves, duration=duration, on_each=on_each, on_done=on_done, record=False)
        return moves

    # ------------------------------------------------------------ persistência
    def to_state(self):
        return [{'p': [c.x, c.y, c.z], 'r': [c.rotation_x, c.rotation_y, c.rotation_z]} for c in self.cubies]

    def from_state(self, state):
        for c, s in zip(self.cubies, state):
            c.position = Vec3(*s['p'])
            c.rotation = Vec3(*s['r'])
        self.history.clear()

    def save_to_file(self, path):
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'state': self.to_state(), 'history': self.history}, f, indent=2)

    def load_from_file(self, path):
        import json
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        self.from_state(data['state'])
        self.history = data.get('history', [])
