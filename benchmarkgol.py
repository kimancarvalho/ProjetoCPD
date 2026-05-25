"""
Benchmark de gameoflife.py — compara as versões sequencial e paralela
para diferentes números de workers, repetindo cada configuração várias
vezes para obter resultados estatisticamente fiáveis.

Os resultados são escritos num ficheiro txt com estatísticas resumidas.
"""

import time
import random
import statistics
import multiprocessing
from gameoflife import game_of_life_sequential, game_of_life_parallel


# Configuração

ROWS        = 500
COLS        = 500
GENERATIONS = 50
RUNS        = 5
SEED        = 42       # semente fixa — garante a mesma grelha em todas as corridas
OUTPUT_FILE = "benchmark_gameoflife.txt"

# Configurações de workers a testar
# cpu_count() é incluído dinamicamente para se adaptar à máquina
_cpus        = multiprocessing.cpu_count()
WORKERS_LIST = sorted(set([1, 2, 4, _cpus]))   # sem duplicados se cpu_count() < 4

# Utilitários

def make_grid(seed: int) -> list[list[int]]:
    """
    Gera uma grelha ROWS×COLS aleatória com ~30% de células vivas.

    Parâmetros:
        seed : semente para reprodutibilidade

    Retorna:
        list[list[int]]: grelha gerada
    """
    random.seed(seed)
    return [
        [1 if random.random() < 0.3 else 0 for _ in range(COLS)]
        for _ in range(ROWS)
    ]


def stats(values: list[float]) -> dict:
    """Calcula estatísticas básicas de uma lista de valores."""
    return {
        "min"   : min(values),
        "max"   : max(values),
        "média" : statistics.mean(values),
        "desvio": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def format_stats(s: dict, unit: str = "s") -> str:
    return (
        f"min={s['min']:.3f}{unit}  "
        f"max={s['max']:.3f}{unit}  "
        f"média={s['média']:.3f}{unit}  "
        f"desvio={s['desvio']:.3f}{unit}"
    )



# Benchmark
def run_sequential(grid_ref: list[list[int]], runs: int) -> list[float]:
    """
    Corre a versão sequencial `runs` vezes e devolve os tempos de execução.

    Parâmetros:
        grid_ref : grelha de referência (não é modificada — cada corrida usa uma cópia)
        runs     : número de repetições

    Retorna:
        list[float]: tempos de execução em segundos
    """
    times = []
    for i in range(1, runs + 1):
        print(f"  [SEQ] Corrida {i}/{runs}...", end=" ", flush=True)
        grid = [row[:] for row in grid_ref]   # cópia para não alterar o original
        t0   = time.monotonic()
        game_of_life_sequential(grid, GENERATIONS)
        elapsed = time.monotonic() - t0
        times.append(elapsed)
        print(f"{elapsed:.3f}s")
    return times


def run_parallel(grid_ref: list[list[int]], workers: int,
                 runs: int) -> tuple[list[float], bool]:
    """
    Corre a versão paralela `runs` vezes para um dado número de workers.

    Na primeira corrida valida que o resultado é idêntico à versão sequencial.

    Parâmetros:
        grid_ref : grelha de referência
        workers  : número de processos worker
        runs     : número de repetições

    Retorna:
        tuple[list[float], bool]: tempos de execução e flag de consistência
    """
    # Resultado de referência para validação (calculado uma vez)
    ref = game_of_life_sequential([row[:] for row in grid_ref], GENERATIONS)

    times      = []
    consistent = True
    for i in range(1, runs + 1):
        print(f"  [PAR workers={workers}] Corrida {i}/{runs}...", end=" ", flush=True)
        grid    = [row[:] for row in grid_ref]
        t0      = time.monotonic()
        result  = game_of_life_parallel(grid, GENERATIONS, workers)
        elapsed = time.monotonic() - t0
        times.append(elapsed)

        if result != ref:
            consistent = False

        print(f"{elapsed:.3f}s")
    return times, consistent



# Main

if __name__ == "__main__":

    grid_ref    = make_grid(SEED)
    live_cells  = sum(sum(row) for row in grid_ref)

    header = (
        f"BENCHMARK — gameoflife.py\n"
        f"Data              : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Grelha            : {ROWS}×{COLS}\n"
        f"Gerações          : {GENERATIONS}\n"
        f"Corridas por conf.: {RUNS}\n"
        f"Células vivas     : {live_cells} ({live_cells / (ROWS * COLS) * 100:.1f}%)\n"
        f"CPUs disponíveis  : {_cpus}\n"
        f"Workers testados  : {WORKERS_LIST}\n"
    )

    print(header)
    lines = [header]

    # Sequencial
    print("A correr versão SEQUENCIAL...")
    seq_times = run_sequential(grid_ref, RUNS)
    seq_stats = stats(seq_times)

    seq_block = (
        f"{'='*60}\n"
        f"  SEQUENCIAL\n"
        f"{'='*60}\n"
        + "\n".join(f"  Corrida {i+1} : {t:.3f}s" for i, t in enumerate(seq_times))
        + f"\n  {'-'*40}\n"
        f"  {format_stats(seq_stats)}\n"
    )
    print()
    lines.append(seq_block)

    # Paralela (vários workers)
    par_results = {}   # workers  (times, consistent)

    for w in WORKERS_LIST:
        print(f"A correr versão PARALELA com {w} worker(s)...")
        times, consistent = run_parallel(grid_ref, w, RUNS)
        par_results[w]    = (times, consistent)
        print()

    # Construir bloco de resultados paralelos
    par_block = f"{'='*60}\n  PARALELA\n{'='*60}\n"

    for w, (times, consistent) in par_results.items():
        s       = stats(times)
        speedup = seq_stats["média"] / s["média"]
        par_block += (
            f"\n  Workers = {w}  |  Consistente: {'SIM' if consistent else 'NÃO'}\n"
            + "\n".join(f"  Corrida {i+1} : {t:.3f}s" for i, t in enumerate(times))
            + f"\n  {'-'*40}\n"
            f"  {format_stats(s)}\n"
            f"  Speedup vs sequencial: {speedup:.2f}x\n"
        )

    lines.append(par_block)

    # Tabela resumo
    summary = (
        f"{'='*60}\n"
        f"  RESUMO\n"
        f"{'='*60}\n"
        f"  {'Configuração':<20} {'Média (s)':>10} {'Speedup':>10} {'Consistente':>12}\n"
        f"  {'-'*54}\n"
        f"  {'Sequencial':<20} {seq_stats['média']:>10.3f} {'—':>10} {'—':>12}\n"
    )
    for w, (times, consistent) in par_results.items():
        s       = stats(times)
        speedup = seq_stats["média"] / s["média"]
        summary += (
            f"  {f'Paralela ({w}w)':<20} {s['média']:>10.3f} "
            f"{speedup:>10.2f}x {'SIM' if consistent else 'NÃO':>12}\n"
        )

    lines.append(summary)
    print(summary)

    # Escrever ficheiro
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Resultados escritos em '{OUTPUT_FILE}'")