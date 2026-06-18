# Cubo Mágico 3D

Cubo mágico 3x3x3 interativo em 3D, feito em Python com [Ursina Engine](https://www.ursinaengine.org/), com resolução automática real (não é apenas o replay de um embaralhamento conhecido).

## Funcionalidades

- Cubo 3D completo (26 peças), com câmera orbitável (botão direito + arrastar) e zoom (roda do mouse)
- Embaralhamento aleatório com quantidade configurável (mínimo 20 movimentos)
- Resolução real do estado atual do cubo, usando o algoritmo de Thistlethwaite
- Resolução passo a passo ou automática
- Giro manual das faces pelo teclado (U/D/L/R/F/B, com SHIFT para o sentido invertido)
- Modo de visualização "explodido"
- Planificação 2D das 6 faces
- Salvar/carregar o estado do cubo em arquivo
- Controle de velocidade da animação e som dos giros

## Requisitos

- Python 3.10+
- Dependências em [requirements.txt](requirements.txt):
  - `ursina`
  - `cube-solver`

## Instalação

```bash
pip install -r requirements.txt
```

## Como executar

```bash
python main.py
```

Na primeira execução, o solver gera tabelas de apoio na pasta `tables/` (processo rápido, leva menos de 1 segundo).

## Controles

| Ação | Controle |
|---|---|
| Girar câmera | Botão direito do mouse + arrastar |
| Zoom | Roda do mouse |
| Girar face | Teclas `U` `D` `L` `R` `F` `B` (`SHIFT` inverte o sentido) |
| Embaralhar | Botão "1) Embaralhar" |
| Resolver | Botão "2) Resolver" |
| Resetar | Botão "3) Resetar" |
| Próximo movimento da solução | Botão "4) Próximo Movimento" |
| Resolver automaticamente | Botão "5) Resolver Automático" |

## Estrutura do projeto

- [main.py](main.py) — ponto de entrada, menu inicial e loop principal
- [cube.py](cube.py) — representação 3D e lógica de estado do cubo
- [controls.py](controls.py) — câmera e interface de usuário (botões, status, painéis)
- [solver.py](solver.py) — integração com a biblioteca de resolução `cube_solver`
