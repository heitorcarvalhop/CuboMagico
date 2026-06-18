# Cubo Mágico 3D

Um Cubo Mágico (Rubik's Cube) 3x3x3 interativo, em 3D, escrito em Python com o
motor [Ursina](https://www.ursinaengine.org/). É possível girar a câmera com o
mouse, embaralhar o cubo, e resolvê-lo automaticamente ou passo a passo,
acompanhando a sequência de movimentos usada na solução.

## Como instalar

Requer **Python 3.10+**.

```bash
# 1. (recomendado) crie um ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. instale as dependências
pip install -r requirements.txt
```

As dependências são a biblioteca `ursina` (que por sua vez instala o
`panda3d`, motor 3D usado internamente) e a `cube-solver` (algoritmo de
resolução real do cubo).

## Como rodar

```bash
python main.py
```

Uma janela com o menu inicial será aberta; clique em **JOGAR** para entrar no
cubo mágico, com o cubo 3D no centro e os controles na lateral esquerda.

## Controles

**Câmera**
- Botão direito do mouse + arrastar: gira a câmera ao redor do cubo
- Roda do mouse: zoom in / zoom out

**Botões da interface**
1. **Embaralhar** — embaralha o cubo com a quantidade de movimentos definida
   no campo "Qtd. de embaralhar" (mínimo de 20 movimentos)
2. **Resolver** — calcula a sequência de movimentos que resolve o cubo
   (mostrada no painel "Solução", à direita) e prepara o modo de resolução
3. **Resetar** — volta o cubo instantaneamente ao estado resolvido
4. **Próximo Movimento** — executa apenas o próximo movimento da solução
   (permite acompanhar a resolução passo a passo)
5. **Resolver Automático** — executa todos os movimentos restantes da
   solução automaticamente, um após o outro, animados

**Outros controles**
- Campo "Qtd. de embaralhar": define quantos movimentos serão usados para
  embaralhar (mínimo 20)
- Slider "Velocidade da animação": controla a duração (em segundos) de cada
  movimento animado, tanto na resolução automática quanto manual
- "Salvar Estado" / "Carregar Estado": grava e recarrega o estado atual do
  cubo em `cubo_estado.json`
- "Modo Explodido": afasta visualmente as 26 peças do centro, facilitando ver
  como elas se encaixam (embaralhar/resolver ficam bloqueados enquanto
  estiver ativo — desative antes de continuar)
- "Ver em 2D": mostra a planificação das 6 faces (como um mapa do cubo aberto)
  na parte de baixo da tela, atualizada em tempo real
- "Configuracoes": liga/desliga o efeito sonoro ao girar as faces
- Teclas **U, D, L, R, F, B**: giram manualmente as faces Up, Down, Left,
  Right, Front e Back. Segure **Shift** para girar no sentido inverso
  (ex.: Shift+U = U')

## Como funciona a resolução

A resolução é **real**: o estado atual do cubo é lido diretamente da cena 3D
(posição e orientação de cada uma das 26 peças) e convertido para uma string
de 54 cores, no formato que o algoritmo de
[Thistlethwaite](https://www.jaapsch.net/puzzles/thistle.htm) entende. Isso
significa que o botão "Resolver" funciona em **qualquer** estado válido do
cubo — não só logo após um embaralhamento, mas também depois de mexer
manualmente pelo teclado ou de carregar um estado salvo.

Na primeira vez que o cubo é resolvido, a biblioteca gera (ou carrega, se já
existirem) pequenas tabelas de apoio na pasta `tables/` — isso leva menos de
1 segundo e só acontece uma vez por instalação.

## Estrutura do projeto

| Arquivo           | Responsabilidade                                                                 |
|--------------------|-----------------------------------------------------------------------------------|
| `main.py`          | Ponto de entrada: cria a janela, mostra o menu inicial e, ao clicar em "Jogar", instancia o cubo e a interface, loop principal |
| `cube.py`          | Representação 3D do cubo (peças, cores, malhas), os 12 movimentos e suas animações, modo explodido, embaralhamento, leitura do estado em facelets, salvar/carregar estado |
| `solver.py`        | Resolve o cubo de verdade (algoritmo de Thistlethwaite) e executa a solução passo a passo ou automaticamente |
| `controls.py`      | Câmera orbitável e toda a interface (botões, textos, slider, campo de texto, visualização 2D, configurações) |
| `requirements.txt` | Dependências do projeto (`ursina`, `cube-solver`)                                |

O estado do cubo é representado pela própria cena 3D: a posição e a
orientação de cada uma das 26 peças (não existe núcleo central visível, como
em um cubo mágico real) já constituem o estado interno — não há uma matriz
de estado duplicada para manter sincronizada.

## Solução de problemas

- **A janela não abre / erro de OpenGL**: atualize os drivers de vídeo. O
  Panda3D (motor usado pelo Ursina) precisa de OpenGL 3.0 ou superior.
- **Sem som**: o efeito sonoro é opcional; se o dispositivo de áudio não for
  encontrado, o programa continua funcionando normalmente, apenas sem som.
