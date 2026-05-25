"""
Benchmark de primos.py — corre as versões sequencial e paralela 10 vezes cada
e escreve os resultados num ficheiro txt com estatísticas resumidas.
"""

import time
import statistics
import multiprocessing
from primos import find_max_prime_sequential, find_max_prime_parallel


# Configuração


RUNS        = 10
TIMEOUT     = 5   # segundos por corrida
WORKERS     = multiprocessing.cpu_count()
OUTPUT_FILE = "benchmark_resultados.txt"

# Utilitários

def run_benchmark(label: str, fn, runs: int) -> list[int]:
    """Corre `fn` `runs` vezes, imprime progresso e devolve lista de resultados."""
    results = []
    for i in range(1, runs + 1):
        print(f"  [{label}] Corrida {i}/{runs}...", end=" ", flush=True)
        t0 = time.monotonic()
        primo = fn()
        elapsed = time.monotonic() - t0
        print(f"primo={primo}  ({elapsed:.2f}s)")
        results.append(primo)
    return results


def stats(values: list[int]) -> dict:
    return {
        "min"    : min(values),
        "max"    : max(values),
        "média"  : statistics.mean(values),
        "mediana": statistics.median(values),
        "desvio" : statistics.stdev(values) if len(values) > 1 else 0,
    }


def format_block(label: str, results: list[int], s: dict) -> str:
    lines = [f"{'=' * 60}", f"  {label}", f"{'=' * 60}"]
    for i, v in enumerate(results, 1):
        lines.append(f"  Corrida {i:>2} : {v:>15,}")
    lines.append(f"  {'-'*40}")
    lines.append(f"  Mínimo   : {s['min']:>15,}")
    lines.append(f"  Máximo   : {s['max']:>15,}")
    lines.append(f"  Média    : {s['média']:>15,.1f}")
    lines.append(f"  Mediana  : {s['mediana']:>15,.1f}")
    lines.append(f"  Desvio   : {s['desvio']:>15,.1f}")
    return "\n".join(lines)



# Main


if __name__ == "__main__":

    header = (
        f"BENCHMARK — primos.py\n"
        f"Data           : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Timeout        : {TIMEOUT}s por corrida\n"
        f"Corridas       : {RUNS}\n"
        f"CPUs           : {WORKERS}\n"
    )

    print(header)

    # Sequencial
    print("A correr versão SEQUENCIAL...")
    seq_results = run_benchmark(
        "SEQ", lambda: find_max_prime_sequential(TIMEOUT), RUNS
    )

    print()

    # Paralela
    print(f"A correr versão PARALELA ({WORKERS} workers)...")
    par_results = run_benchmark(
        "PAR", lambda: find_max_prime_parallel(TIMEOUT, WORKERS), RUNS
    )

    # Estatísticas
    seq_stats = stats(seq_results)
    par_stats = stats(par_results)
    speedup   = par_stats["média"] / seq_stats["média"]

    comparison = (
        f"\n{'='*60}\n"
        f"  COMPARAÇÃO  (média paralela / média sequencial)\n"
        f"{'='*60}\n"
        f"  Speedup médio : {speedup:.2f}x\n"
        f"  (a versão paralela encontrou primos em média {speedup:.2f}x maiores)"
    )

    # Escrever ficheiro
    output = "\n".join([
        header,
        format_block(f"SEQUENCIAL  (1 worker, timeout={TIMEOUT}s)", seq_results, seq_stats),
        format_block(f"PARALELA    ({WORKERS} workers, timeout={TIMEOUT}s)", par_results, par_stats),
        comparison,
    ])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(comparison)
    print(f"\nResultados escritos em '{OUTPUT_FILE}'")
