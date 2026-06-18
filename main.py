"""
main.py
-------
Ponto de entrada do Cubo Magico 3D interativo.

Cria a janela Ursina, mostra o menu inicial e, ao clicar em "Jogar",
instancia o cubo 3D (cube.RubiksCube) e a interface de controle
(controls.CubeControls), iniciando o loop principal do jogo.

Para executar:
    python main.py
"""
from ursina import Ursina, Sky, DirectionalLight, AmbientLight, Entity, Text, Button, color, destroy, camera

import cube as cube_module
from cube import RubiksCube
from controls import CubeControls

app = Ursina(title='Cubo Magico 3D', borderless=False)

Sky(color=color.rgb32(18, 18, 28))
DirectionalLight(y=2, z=3, x=1, rotation=(45, -45, 0))
AmbientLight(color=color.rgba(0.45, 0.45, 0.45, 0.5))

cube_module.init_sound()

rubiks_cube = RubiksCube()
controls = CubeControls(rubiks_cube)

# o jogo começa escondido atrás do menu inicial (ver show_main_menu() abaixo)
rubiks_cube.enabled = False
controls.set_visible(False)

print('=' * 60)
print('CUBO MAGICO 3D')
print('Botoes: 1) Embaralhar  2) Resolver  3) Resetar')
print('        4) Proximo Movimento  5) Resolver Automatico')
print('Camera: botao direito + arrastar = girar | roda do mouse = zoom')
print('Teclas: U/D/L/R/F/B giram as faces (segure SHIFT para o sentido invertido)')
print('=' * 60)


def show_main_menu():
    """Mostra a tela inicial com o título e o botão "Jogar"."""
    menu = Entity(parent=camera.ui)
    Entity(parent=menu, model='quad', color=color.rgba(0, 0, 0, 0.96), scale=(0.78, 0.62), z=0.01)
    Text(parent=menu, text='CUBO MAGICO 3D', origin=(0, 0), position=(0, 0.21), scale=2.4,
         color=color.azure)
    Text(parent=menu, text='Cubo magico 3x3x3 interativo, com resolucao real',
         origin=(0, 0), position=(0, 0.14), scale=0.85, color=color.light_gray)
    Text(parent=menu,
         text=('- Embaralhe e resolva o cubo, automaticamente ou passo a passo\n'
               '- Gire a camera com o botao direito do mouse, zoom com a roda\n'
               '- Modo explodido e visualizacao 2D das faces\n'
               '- Teclas U/D/L/R/F/B giram as faces manualmente'),
         origin=(0, 0), position=(0, 0.0), scale=0.62, color=color.light_gray)

    def start():
        destroy(menu)
        rubiks_cube.enabled = True
        controls.set_visible(True)

    Button(parent=menu, text='JOGAR', scale=(0.26, 0.075), position=(0, -0.22),
           color=color.azure.tint(-.3), highlight_color=color.azure, text_size=1.0,
           on_click=start)
    return menu


show_main_menu()


def update():
    """Chamado pela Ursina a cada frame; mantém a UI sincronizada."""
    if controls.ui_root.enabled:
        controls.update()


def input(key):
    """Atalhos de teclado para girar faces manualmente (bonus / depuração)."""
    if not controls.ui_root.enabled:
        return  # ainda no menu inicial
    if rubiks_cube.animating or rubiks_cube.exploded:
        return
    base_keys = {'u': 'U', 'd': 'D', 'l': 'L', 'r': 'R', 'f': 'F', 'b': 'B'}
    k = key.replace('shift+', '')
    if k in base_keys:
        move = base_keys[k]
        if key.startswith('shift+'):
            move = cube_module.inverse_move(move)
        rubiks_cube.apply_move(move, duration=controls.move_duration, record=True)


app.run()
