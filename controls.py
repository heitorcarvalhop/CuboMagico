"""
controls.py
-----------
Controle de câmera (orbitável com o mouse, zoom com a roda do mouse) e toda
a interface de usuário: botões, textos de status, campo de embaralhamento
personalizado, slider de velocidade, salvar/carregar estado, modo de
visualização "explodido", planificação 2D das faces e painel de
configurações (som).

Esse módulo conecta os botões à lógica pura do cubo (cube.py) e do
resolvedor (solver.py), sem conter regras do jogo em si. Toda a UI fica sob
`self.ui_root`, que pode ser escondida de uma vez (`set_visible`) enquanto o
menu inicial (main.py) está na tela.
"""
from ursina import Entity, Text, Button, Vec2, color, camera, window
from ursina.prefabs.editor_camera import EditorCamera
from ursina.prefabs.slider import Slider
from ursina.prefabs.input_field import InputField

import cube as cube_module
from solver import Solver

SAVE_FILE = 'cubo_estado.json'

LETTER_COLOR = {
    'W': cube_module.COLOR_WHITE, 'Y': cube_module.COLOR_YELLOW,
    'R': cube_module.COLOR_RED, 'O': cube_module.COLOR_ORANGE,
    'G': cube_module.COLOR_GREEN, 'B': cube_module.COLOR_BLUE,
}

FACE_BLOCK = {'U': (3, 0), 'L': (0, 3), 'F': (3, 3), 'R': (6, 3), 'B': (9, 3), 'D': (3, 6)}


class CubeControls:
    """Monta a UI lateral e liga os botões às ações do cubo/resolvedor."""

    def __init__(self, rubiks_cube):
        self.cube = rubiks_cube
        self.solver = Solver(self.cube)
        self.move_duration = 0.35
        self.solving_mode = False
        self.error_message = None
        self.sound_on = True

        camera.position = (0, 0, -14)
        self.editor_camera = EditorCamera(rotation_speed=200, zoom_speed=6, rotate_key='right mouse')
        self.editor_camera.rotation = (25, -35, 0)

        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        self.ui_root = Entity(parent=camera.ui)

        panel = Entity(parent=self.ui_root, position=window.top_left + Vec2(0.03, -0.04))

        Text(parent=panel, text='CUBO MAGICO 3D', scale=1.6, position=(0, 0), color=color.azure)

        y = -0.06

        def add_button(label, handler):
            nonlocal y
            b = Button(parent=panel, text=label, scale=(0.30, 0.045), position=(0.15, y),
                       color=color.dark_gray, highlight_color=color.gray, text_size=0.65,
                       on_click=handler)
            y -= 0.06
            return b

        self.btn_scramble = add_button('1) Embaralhar', self.on_scramble)
        self.btn_solve = add_button('2) Resolver', self.on_solve)
        self.btn_reset = add_button('3) Resetar', self.on_reset)
        self.btn_next = add_button('4) Proximo Movimento', self.on_next_move)
        self.btn_auto = add_button('5) Resolver Automatico', self.on_auto_solve)

        y -= 0.015
        Text(parent=panel, text='Qtd. de embaralhar (min. 20):', position=(0, y), scale=0.7)
        y -= 0.05
        self.scramble_field = InputField(parent=panel, default_value='20', limit_content_to='0123456789',
                                          position=(0.12, y), scale=(0.22, 0.045))
        y -= 0.07

        Text(parent=panel, text='Velocidade da animacao:', position=(0, y), scale=0.7)
        y -= 0.05
        self.speed_slider = Slider(parent=panel, min=0.05, max=0.8, default=self.move_duration, step=0.05,
                                    dynamic=True, position=(0.0, y), text='seg/mov')
        self.speed_slider.on_value_changed = self._on_speed_changed
        y -= 0.08

        self.btn_save = add_button('Salvar Estado', self.on_save)
        self.btn_load = add_button('Carregar Estado', self.on_load)
        self.btn_explode = add_button('Modo Explodido: OFF', self.on_toggle_explode)
        self.btn_flat = add_button('Ver em 2D: OFF', self.on_toggle_flat_view)
        self.btn_settings = add_button('Configuracoes', self.on_toggle_settings)

        self._build_flat_view()
        self._build_settings_panel()

        info = Entity(parent=self.ui_root, position=window.top_right + Vec2(-0.40, -0.04))
        self.status_text = Text(parent=info, text='Estado: Resolvido', position=(0, 0),
                                 color=color.lime, scale=1.1)
        self.current_move_text = Text(parent=info, text='Movimento atual: -', position=(0, -0.05), scale=0.85)
        self.scramble_text = Text(parent=info, text='Embaralhamento: -', position=(0, -0.10), scale=0.7,
                                   wordwrap=45)
        self.solution_text = Text(parent=info, text='Solucao: -', position=(0, -0.22), scale=0.7, wordwrap=45)

        Text(parent=self.ui_root, text='Botao direito + arrastar: girar camera   |   Roda do mouse: zoom',
             position=window.bottom_left + Vec2(0.03, 0.03), scale=0.65, color=color.gray)

    def _build_flat_view(self):
        """Cria (escondido por padrão) o painel com a planificação 2D das 6 faces."""
        cell = 0.024
        bg_w, bg_h = 12 * cell + 0.04, 9 * cell + 0.04
        self.flat_view_panel = Entity(parent=self.ui_root, position=(0, -0.33), enabled=False)
        Entity(parent=self.flat_view_panel, model='quad', color=color.rgba(0, 0, 0, 0.92),
               scale=(bg_w, bg_h), z=0.01)
        self.flat_squares = {}
        for face, (col0, row0) in FACE_BLOCK.items():
            for i in range(9):
                row, col = col0 + (i % 3), row0 + (i // 3)
                x = (row - 5.5) * cell
                y = (4 - col) * cell
                sq = Entity(parent=self.flat_view_panel, model='quad', color=color.black,
                            position=(x, y), scale=cell * 0.9)
                self.flat_squares[(face, i)] = sq

    def _update_flat_view(self):
        facelets = self.cube.get_facelet_string()
        idx = 0
        for face in cube_module.SOLVER_FACE_ORDER:
            for i in range(9):
                self.flat_squares[(face, i)].color = LETTER_COLOR.get(facelets[idx], color.black)
                idx += 1

    def _build_settings_panel(self):
        """Cria (escondido por padrão) o painel de configurações."""
        self.settings_panel = Entity(parent=self.ui_root, position=(0, 0.1), enabled=False)
        Entity(parent=self.settings_panel, model='quad', color=color.rgba(0, 0, 0, 0.97),
               scale=(0.52, 0.3), z=0.01)
        Text(parent=self.settings_panel, text='CONFIGURACOES', position=(-0.22, 0.11), scale=1.1,
             color=color.azure)
        self.btn_sound = Button(parent=self.settings_panel, text='Som: ON', scale=(0.3, 0.05),
                                 position=(0, 0.02), color=color.dark_gray, highlight_color=color.gray,
                                 text_size=0.7, on_click=self.on_toggle_sound)
        Text(parent=self.settings_panel,
             text='Velocidade e quantidade de embaralhar:\nuse os controles do painel principal.',
             position=(-0.22, -0.06), scale=0.6, color=color.light_gray)
        Button(parent=self.settings_panel, text='Fechar', scale=(0.18, 0.045), position=(0, -0.115),
               color=color.dark_gray, highlight_color=color.gray, text_size=0.7,
               on_click=self.on_toggle_settings)

    def _on_speed_changed(self):
        self.move_duration = round(self.speed_slider.value, 2)

    @staticmethod
    def _set_text(text_entity, value):
        """Só reatribui Text.text quando o conteúdo muda de fato: Text.text
        reconstrói a malha do texto inteira a cada atribuição, e este método
        é chamado todo quadro pelo update(), então evitamos trabalho à toa."""
        if text_entity.text != value:
            text_entity.text = value

    def _refresh_status(self, current_move=None):
        if self.error_message:
            self.status_text.color = color.red
            self._set_text(self.status_text, f'Erro: {self.error_message}')
            return
        if self.cube.exploded:
            self.status_text.color = color.cyan
            self._set_text(self.status_text, 'Estado: Modo Explodido (desative para embaralhar/resolver)')
            return
        if self.cube.animating:
            state = 'Resolvendo...' if self.solving_mode else 'Embaralhando...'
            self.status_text.color = color.yellow
        elif self.cube.is_solved():
            state = 'Resolvido'
            self.status_text.color = color.lime
            self.solving_mode = False
        else:
            state = 'Embaralhado'
            self.status_text.color = color.orange
        self._set_text(self.status_text, f'Estado: {state}')

        if current_move:
            self._set_text(self.current_move_text, f'Movimento atual: {current_move}')

        self._set_text(self.scramble_text,
                        'Embaralhamento: ' + (' '.join(self.cube.history) if self.cube.history else '-'))

        pending = self.solver.pending()
        self._set_text(self.solution_text, 'Solucao: ' + (' '.join(pending) if pending else '-'))

    def on_scramble(self):
        if self.cube.animating or self.cube.exploded:
            return
        try:
            n = int(self.scramble_field.text)
        except (ValueError, TypeError):
            n = 20
        n = max(20, n)
        self.solving_mode = False
        self.error_message = None
        self.solver.queue.clear()
        self.current_move_text.text = 'Movimento atual: -'

        def each(move):
            self._refresh_status(current_move=move)

        def done():
            self._refresh_status()
            print('Embaralhamento concluido.')

        self.cube.scramble(n=n, duration=0.15, on_each=each, on_done=done)
        self._refresh_status()

    def _try_compute_solution(self):
        """Calcula a solução e trata o caso de estado inválido. Devolve True se há
        uma solução pronta para ser executada (mesmo que vazia, cubo já resolvido)."""
        self.solver.compute()
        if self.solver.error:
            self.error_message = self.solver.error
            self._refresh_status()
            return False
        self.error_message = None
        return True

    def on_solve(self):
        if self.cube.animating:
            return
        self.solving_mode = True
        if not self._try_compute_solution():
            return
        self._refresh_status()
        if not self.solver.has_pending():
            print('O cubo ja esta resolvido.')

    def on_next_move(self):
        if self.cube.animating or self.cube.exploded:
            return
        if not self.solving_mode or not self.solver.has_pending():
            if not self._try_compute_solution():
                return
            self.solving_mode = True
            if not self.solver.has_pending():
                self._refresh_status()
                return

        def done(move):
            self._refresh_status(current_move=move)

        def empty():
            self._refresh_status()

        self.solver.step(duration=self.move_duration, on_complete=done, on_empty=empty)
        self._refresh_status()

    def on_auto_solve(self):
        if self.cube.animating or self.cube.exploded:
            return
        if not self.solving_mode or not self.solver.has_pending():
            if not self._try_compute_solution():
                return
        self.solving_mode = True

        def each(move):
            self._refresh_status(current_move=move)

        def done():
            self._refresh_status()
            print('Cubo resolvido!')

        if not self.solver.has_pending():
            self._refresh_status()
            return

        self.solver.auto(duration=self.move_duration, on_each=each, on_done=done)
        self._refresh_status()

    def on_reset(self):
        self.cube.reset_instant()
        self.solver.queue.clear()
        self.solver.done.clear()
        self.solving_mode = False
        self.error_message = None
        self.current_move_text.text = 'Movimento atual: -'
        self._refresh_status()
        print('Cubo resetado para o estado resolvido.')

    def on_save(self):
        self.cube.save_to_file(SAVE_FILE)
        print(f'Estado salvo em {SAVE_FILE}')

    def on_load(self):
        try:
            self.cube.load_from_file(SAVE_FILE)
            self.solver.queue.clear()
            self.solving_mode = False
            self.error_message = None
            self._refresh_status()
            print(f'Estado carregado de {SAVE_FILE}')
        except FileNotFoundError:
            print(f'Nenhum estado salvo encontrado ({SAVE_FILE}).')

    def on_toggle_explode(self):
        if self.cube.animating:
            return
        exploded = not self.cube.exploded
        self.cube.set_exploded(exploded)
        self._set_text(self.btn_explode, f'Modo Explodido: {"ON" if exploded else "OFF"}')
        if exploded and self.flat_view_panel.enabled:
            self.flat_view_panel.enabled = False
            self._set_text(self.btn_flat, 'Ver em 2D: OFF')
        self._refresh_status()

    def on_toggle_flat_view(self):
        if self.cube.exploded:
            return
        visible = not self.flat_view_panel.enabled
        self.flat_view_panel.enabled = visible
        self._set_text(self.btn_flat, f'Ver em 2D: {"ON" if visible else "OFF"}')
        if visible:
            self._update_flat_view()
        self._refresh_status()

    def on_toggle_settings(self):
        self.settings_panel.enabled = not self.settings_panel.enabled

    def on_toggle_sound(self):
        self.sound_on = not self.sound_on
        cube_module.set_sound_enabled(self.sound_on)
        self._set_text(self.btn_sound, f'Som: {"ON" if self.sound_on else "OFF"}')

    def set_visible(self, visible):
        """Mostra/esconde toda a UI do jogo de uma vez (usado pelo menu inicial)."""
        self.ui_root.enabled = visible

    def update(self):
        """Chamado pela Ursina a cada quadro: mantém o status (e a visão 2D,
        se estiver visível) sincronizados durante animações."""
        self._refresh_status()
        if self.flat_view_panel.enabled and not self.cube.exploded:
            self._update_flat_view()
