# CuboMagico

Representação 3D e lógica de estado do Cubo Mágico 3x3x3.

Cada peça visível do cubo (26 ao todo: 8 vértices + 12 arestas + 6 centros)
é um Entity da Ursina com uma malha (Mesh) colorida individualmente em cada
face. A posição de cada peça na grade 3x3x3 (-1, 0 ou 1 em cada eixo) É o
estado interno do cubo: não existe uma matriz de estado separada, a própria
cena 3D representa o estado, o que evita duplicação e bugs de sincronização.

Os 12 movimentos padrão (U, U', D, D', L, L', R, R', F, F', B, B') são
implementados girando, em torno de um pivô temporário, as 9 peças que
pertencem à camada correspondente.
