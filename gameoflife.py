"""
Módulo para a simulação do Game of Life.

Implementação das versões sequencial e paralela (multiprocessing),
operando sobre grelhas representadas como listas de listas Python.

Regras:
  - Célula viva com < 2 vizinhos vivos  → morre  (solidão)
  - Célula viva com 2 ou 3 vizinhos     → sobrevive
  - Célula viva com > 3 vizinhos vivos  → morre  (superpopulação)
  - Célula morta com exactamente 3 vizinhos vivos → nasce
  - A grelha é acíclica — células nas bordas têm menos vizinhos
"""

import multiprocessing



# Funções auxiliares
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



# Versão sequencial


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



# Versão paralela


def _compute_slice(grid: list[list[int]], row_start: int, row_end: int,
                   rows: int, cols: int) -> list[list[int]]:
    """
    Calcula o próximo estado de um subconjunto de linhas da grelha.

    Recebe a grelha completa da geração atual (apenas leitura) e calcula
    o estado seguinte apenas para as linhas em [row_start, row_end[.
    Como a grelha completa está disponível, as células de fronteira acedem
    correctamente aos vizinhos de linhas pertencentes a outros workers.

    Parâmetros:
        grid      : grelha completa da geração atual (só leitura)
        row_start : primeira linha a calcular (inclusivo)
        row_end   : última linha a calcular (exclusivo)
        rows      : número total de linhas da grelha
        cols      : número total de colunas da grelha

    Retorna:
        list[list[int]]: linhas calculadas [row_start, row_end[
    """
    return [
        [
            next_cell_state(grid[row][col], count_neighbors(grid, row, col, rows, cols))
            for col in range(cols)
        ]
        for row in range(row_start, row_end)
    ]


def game_of_life_parallel(grid: list[list[int]], generations: int,
                          workers: int) -> list[list[int]]:
    """
    Simula o Game of Life em paralelo durante gerações.

    Estratégia — divisão por linhas com Pool e starmap:
      - A grelha é dividida em `workers` fatias horizontais de linhas.
      - Em cada geração, o Pool distribui as fatias pelos workers via starmap,
        que bloqueia até todos terminarem — garantindo sincronização automática
        entre gerações.
      - Cada worker recebe a grelha completa para leitura, eliminando o problema
        de fronteira: as células de borda acedem correctamente aos vizinhos de
        linhas pertencentes a outros workers.
      - As fatias calculadas são reunidas por concatenação para formar a grelha
        completa da geração seguinte.
      - O Pool é criado uma única vez e reutilizado em todas as gerações,
        evitando o overhead de criar e destruir processos repetidamente.

    Parâmetros:
        grid        : grelha inicial (lista de listas, 0 = morta, 1 = viva)
        generations : número de gerações a simular
        workers     : número de processos worker a utilizar

    Retorna:
        list[list[int]]: estado final da grelha após todas as gerações
    """
    rows  = len(grid)
    cols  = len(grid[0])
    chunk = rows // workers

    # Calcular os intervalos de linhas para cada worker.
    # O último worker apanha as linhas restantes quando rows % workers != 0.
    slices = [
        (i * chunk, (i + 1) * chunk if i < workers - 1 else rows)
        for i in range(workers)
    ]

    with multiprocessing.Pool(processes=workers) as pool:
        for _ in range(generations):
            # Construir lista de tarefas - cada tupla é desempacotada pelo starmap
            tasks = [
                (grid, row_start, row_end, rows, cols)
                for row_start, row_end in slices
            ]

            # Executar em paralelo - bloqueia até todos os workers terminarem
            # garantindo sincronização automática entre gerações
            fatias = pool.starmap(_compute_slice, tasks)

            # Reunir as fatias por ordem para reconstruir a grelha completa
            grid = [row for fatia in fatias for row in fatia]

    return grid


# Ponto de entrada: demonstração rápida da versão sequencial

if __name__ == "__main__":
    import time
    import random

    # Grelha 500×500 gerada aleatoriamente com ~30% de células vivas
    # (densidade típica para comportamento interessante no Game of Life)
    ROWS        = 500
    COLS        = 500
    GENERATIONS = 50
    WORKERS     = multiprocessing.cpu_count()
    SEED        = 42   # semente fixa para reprodutibilidade dos resultados

    random.seed(SEED)
    grid = [
        [1 if random.random() < 0.3 else 0 for _ in range(COLS)]
        for _ in range(ROWS)
    ]

    print(f"Grelha: {ROWS}×{COLS}  |  Gerações: {GENERATIONS}  |  Workers: {WORKERS}")
    print(f"Células vivas iniciais: {sum(sum(row) for row in grid)}\n")

    # Sequencial
    t0      = time.monotonic()
    res_seq = game_of_life_sequential([row[:] for row in grid], GENERATIONS)
    t_seq   = time.monotonic() - t0
    print(f"[Sequencial] {t_seq:.3f}s")

    # Paralela
    t0      = time.monotonic()
    res_par = game_of_life_parallel([row[:] for row in grid], GENERATIONS, WORKERS)
    t_par   = time.monotonic() - t0
    print(f"[Paralela]   {t_par:.3f}s  (workers={WORKERS})")

    # Validar consistência e speedup
    print(f"\nResultados idênticos : {res_seq == res_par}")
    print(f"Speedup              : {t_seq / t_par:.2f}x")