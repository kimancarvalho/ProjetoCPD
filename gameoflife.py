"""
Módulo para a simulação do Game of Life.

Versões sequencial e paralela (multiprocessing) da simulação,
operando sobre grelhas representadas como listas de listas.

Regras:
  - Célula viva com < 2 vizinhos vivos  → morre  (solidão)
  - Célula viva com 2 ou 3 vizinhos     → sobrevive
  - Célula viva com > 3 vizinhos vivos  → morre  (superpopulação)
  - Célula morta com exactamente 3 vizinhos vivos → nasce
  - A grelha NÃO é cíclica — células nas bordas têm menos vizinhos
"""

import multiprocessing


# =============================================================================
# Funções auxiliares
# =============================================================================

def count_neighbors(grid: list[list[int]], row: int, col: int,
                    rows: int, cols: int) -> int:
    """
    Conta o número de vizinhos vivos de uma célula.

    Considera os 8 vizinhos possíveis (horizontal, vertical e diagonal).
    A grelha não é cíclica — vizinhos fora dos limites são ignorados.

    Parâmetros:
        grid : grelha atual
        row  : linha da célula
        col  : coluna da célula
        rows : número total de linhas da grelha
        cols : número total de colunas da grelha

    Retorna:
        int: número de vizinhos vivos (0–8)
    """
    live = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue                        # ignorar a própria célula
            r, c = row + dr, col + dc
            if 0 <= r < rows and 0 <= c < cols: # ignorar fora dos limites
                live += grid[r][c]
    return live


def next_cell_state(current_state: int, live_neighbors: int) -> int:
    """
    Calcula o próximo estado de uma célula aplicando as regras do Game of Life.

    Parâmetros:
        current_state  : estado atual da célula (0 = morta, 1 = viva)
        live_neighbors : número de vizinhos vivos

    Retorna:
        int: próximo estado da célula (0 ou 1)
    """
    if current_state == 1:
        # Célula viva: sobrevive com 2 ou 3 vizinhos, morre nos restantes casos
        return 1 if live_neighbors in (2, 3) else 0
    else:
        # Célula morta: nasce com exactamente 3 vizinhos vivos
        return 1 if live_neighbors == 3 else 0


def next_generation(grid: list[list[int]], rows: int, cols: int) -> list[list[int]]:
    """
    Calcula o estado da grelha na geração seguinte.

    Aplica as regras do Game of Life a todas as células da grelha,
    produzindo uma nova grelha sem modificar a original.

    Parâmetros:
        grid : grelha atual
        rows : número de linhas
        cols : número de colunas

    Retorna:
        list[list[int]]: nova grelha com o estado da geração seguinte
    """
    return [
        [
            next_cell_state(grid[row][col], count_neighbors(grid, row, col, rows, cols))
            for col in range(cols)
        ]
        for row in range(rows)
    ]


# =============================================================================
# Versão sequencial
# =============================================================================

def game_of_life_sequential(grid: list[list[int]], generations: int) -> list[list[int]]:
    """
    Simula o Game of Life de forma sequencial durante `generations` gerações.

    Parâmetros:
        grid        : grelha inicial (lista de listas, 0 = morta, 1 = viva)
        generations : número de gerações a simular

    Retorna:
        list[list[int]]: estado final da grelha após todas as gerações
    """
    rows = len(grid)
    cols = len(grid[0])

    for _ in range(generations):
        grid = next_generation(grid, rows, cols)

    return grid


# =============================================================================
# Versão paralela — a implementar
# =============================================================================

def game_of_life_parallel(grid: list[list[int]], generations: int,
                          workers: int) -> list[list[int]]:
    """
    Simula o Game of Life em paralelo durante `generations` gerações.

    Parâmetros:
        grid        : grelha inicial (lista de listas, 0 = morta, 1 = viva)
        generations : número de gerações a simular
        workers     : número de processos worker a utilizar

    Retorna:
        list[list[int]]: estado final da grelha após todas as gerações
    """
    # TODO: implementar
    raise NotImplementedError


# =============================================================================
# Ponto de entrada — demonstração rápida da versão sequencial
# =============================================================================

if __name__ == "__main__":
    # Padrão clássico "Glider" — translada-se pela grelha a cada 4 gerações
    glider = [
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]

    GENERATIONS = 4

    def print_grid(g: list[list[int]], label: str) -> None:
        print(f"\n{label}")
        for row in g:
            print(" ".join("█" if c else "·" for c in row))

    print_grid(glider, "Geração 0 (inicial)")
    resultado = game_of_life_sequential(glider, GENERATIONS)
    print_grid(resultado, f"Geração {GENERATIONS} (após {GENERATIONS} gerações)")