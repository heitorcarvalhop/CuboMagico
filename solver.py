"""
solver.py
---------
Resolução real do Cubo Mágico: resolve QUALQUER estado válido do cubo, não
apenas o resultado de um embaralhamento conhecido (funciona também depois
de movimentos manuais de teclado, ou depois de carregar um estado salvo).

Usa o algoritmo de Thistlethwaite (via a biblioteca `cube_solver`), que
resolve o cubo em 4 fases reduzindo progressivamente o grupo de movimentos
permitidos. A solução não é a mais curta possível (como seria com o
algoritmo de Kociemba), mas é encontrada em milissegundos e usa tabelas de
apoio pequenas (poucos MB, gravadas em `tables/` na primeira execução),
enquanto o Kociemba exigiria tabelas de mais de 1 GB.

O estado do cubo é lido diretamente da cena 3D (`cube.RubiksCube.get_facelet_string`)
e convertido para o formato de 54 letras (W/G/R/Y/B/O) que a `cube_solver`
espera; a solução retornada (ex.: "U2 R' F ...") é convertida de volta para
a nossa notação de giros de 90 graus (ex.: ['U','U',"R'",'F']).
"""
from collections import deque

from cube_solver import Cube as SolverCube, Thistlethwaite

_solver = None


def _get_solver():
    """Cria o solver na primeira vez que for necessário (gera/carrega as
    tabelas de apoio em `tables/`, o que leva menos de 1 segundo)."""
    global _solver
    if _solver is None:
        _solver = Thistlethwaite()
    return _solver


def _parse_move_string(move_string):
    """Converte a notação da cube_solver ('U2 R' F ...') em uma lista de
    giros de 90 graus (ex.: ['U', 'U', "R'", 'F']), compatível com cube.MOVES."""
    moves = []
    for token in move_string.split():
        face, suffix = token[0], token[1:]
        if suffix == '2':
            moves.extend([face, face])
        elif suffix == "'":
            moves.append(face + "'")
        else:
            moves.append(face)
    return moves


class Solver:
    """Calcula e executa, passo a passo ou automaticamente, a solução real do cubo."""

    def __init__(self, cube):
        self.cube = cube
        self.queue = deque()   # movimentos da solução ainda não executados
        self.done = []         # movimentos da solução já executados
        self.error = None      # mensagem de erro, se o estado atual for inválido

    def compute(self):
        """Lê o estado atual do cubo (3D) e calcula a sequência que o resolve."""
        self.error = None
        self.queue.clear()
        self.done = []
        try:
            facelets = self.cube.get_facelet_string()
            solver_cube = SolverCube(repr=facelets)
            solution = _get_solver().solve(solver_cube)
            self.queue = deque(_parse_move_string(solution))
        except (ValueError, KeyError) as e:
            self.error = 'Estado do cubo inválido: não foi possível calcular uma solução.'
            print(self.error, f'({e})')
            return []

        print('Solução calculada:', ' '.join(self.queue) if self.queue else '(cubo já resolvido)')
        return list(self.queue)

    def pending(self):
        """Lista (sem remover) os movimentos que ainda faltam executar."""
        return list(self.queue)

    def has_pending(self):
        return len(self.queue) > 0

    def step(self, duration=0.3, on_complete=None, on_empty=None):
        """Executa apenas o próximo movimento da solução (modo manual / passo a passo)."""
        if not self.queue:
            if on_empty:
                on_empty()
            return None

        move = self.queue.popleft()
        finished = not self.queue
        print('Movimento da solução:', move)

        def _done(m):
            self.done.append(m)
            if finished:
                self.cube.history.clear()
            if on_complete:
                on_complete(m)

        self.cube.apply_move(move, duration=duration, on_complete=_done, record=False)
        return move

    def auto(self, duration=0.3, on_each=None, on_done=None):
        """Executa todos os movimentos pendentes da solução, um após o outro, automaticamente."""
        moves = list(self.queue)
        self.queue.clear()

        def _each(m):
            self.done.append(m)
            print('Movimento da solução:', m)
            if on_each:
                on_each(m)

        def _on_done():
            self.cube.history.clear()
            if on_done:
                on_done()

        self.cube.queue_moves(moves, duration=duration, on_each=_each, on_done=_on_done, record=False)
