"""
Módulo para a procura do maior número primo possível dentro de um limite temporal.

Implementa versões sequencial e paralela (multiprocessing) para pesquisa de primos.
"""

import time
import multiprocessing
import multiprocessing.sharedctypes
import multiprocessing.synchronize

# =============================================================================
# Função de verificar primalidade fornecida pelo enunciado
# =============================================================================

def is_prime(n: int) -> bool:
    """
    Verifica se um número inteiro é primo.

    Utiliza divisão experimental otimizada, testando apenas divisores da forma
    6k ± 1, o que reduz o número de divisões necessárias para ~n/3.

    Parâmetros:
        n (int): O número a verificar.

    Retorna:
        bool: True se n é primo, False caso contrário.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    divisor = 5
    while divisor * divisor <= n:
        if n % divisor == 0 or n % (divisor + 2) == 0:
            return False
        divisor += 6
    return True


# =============================================================================
# Versão sequencial
# =============================================================================

def find_max_prime_sequential(timeout: int) -> int:
    """
    Procura o maior número primo possível durante, no máximo, `timeout` segundos,
    utilizando uma abordagem sequencial.

    A pesquisa começa no número 2 e avança de forma contínua, testando cada
    candidato com is_prime(). O melhor resultado encontrado é mantido e
    atualizado sempre que um novo primo é descoberto.

    A terminação ocorre quando o tempo limite é atingido. Nesse momento,
    o loop é interrompido e o maior primo encontrado até então é devolvido.

    Parâmetros:
        timeout (int): Duração máxima da pesquisa, em segundos.

    Retorna:
        int: O maior número primo encontrado dentro do limite temporal.
             Devolve 2 se o tempo não for suficiente para encontrar qualquer primo.
    """
    best = 2          # Menor primo — garante que há sempre um resultado válido
    candidate = 3     # Começamos no 3; o 2 já está coberto pelo valor inicial
    deadline = time.monotonic() + timeout

    "Monotonic() ao invés de time() porque monotonic não é afetado por ajustes do sistema (DST, NTP)"
    while time.monotonic() < deadline:
        if is_prime(candidate):
            best = candidate
        # Avançamos de 2 em 2 para saltar os pares (todos os pares > 2 não são primos)
        candidate += 2

    return best


# =============================================================================
# Versão paralela
# =============================================================================

# Tamanho de cada bloco de candidatos atribuído a um worker de cada vez.
# Valor empiricamente ajustado: grande o suficiente para amortizar o overhead
# de IPC, pequeno o suficiente para manter os workers equilibrados.
BLOCK_SIZE = 100_000


def _worker(
        next_block: multiprocessing.sharedctypes.Synchronized,  # contador atómico do próximo bloco
        best: multiprocessing.sharedctypes.Synchronized,  # maior primo global encontrado
        stop_event: multiprocessing.synchronize.Event,  # sinaliza o fim do timeout
        block_size: int,  # número de candidatos por bloco
) -> None:
    """
    Função executada por cada processo worker.

    Cada worker opera num ciclo de três fases:
      1. Reservar o próximo bloco via contador atómico (operação com lock).
      2. Pesquisar o bloco de forma autónoma, do maior para o menor candidato
         (só ímpares), parando no primeiro primo encontrado — que é
         garantidamente o maior do bloco.
      3. Atualizar o melhor resultado global se o primo encontrado for maior
         (operação com lock).

    O ciclo repete-se até o `stop_event` ser ativado pelo processo principal.

    Parâmetros:
        next_block  : Value('Q') — índice do próximo bloco a processar.
        best        : Value('Q') — maior primo encontrado por qualquer worker.
        stop_event  : Event — quando ativo, o worker termina após o bloco atual.
        block_size  : número de candidatos (ímpares) por bloco.
    """
    while not stop_event.is_set():

        # ── Fase 1: reservar o próximo bloco atomicamente ──────────────────
        with next_block.get_lock():
            block_index = next_block.value
            next_block.value += 1

        # Converter índice em intervalo real de candidatos ímpares.
        # O espaço de pesquisa começa em 3 (primeiro ímpar > 2).
        # Cada bloco cobre `block_size` ímpares, logo o passo real é block_size * 2.
        block_start = 3 + block_index * block_size * 2  # primeiro ímpar do bloco
        block_end = block_start + (block_size - 1) * 2  # último ímpar do bloco

        # ── Fase 2: pesquisar do maior para o menor ─────────────────────────
        block_best = None
        candidate = block_end
        while candidate >= block_start:
            if stop_event.is_set():  # ← parar a meio do bloco se o tempo acabou
                return
            if is_prime(candidate):
                block_best = candidate
                break  # maior primo do bloco encontrado — sair
            candidate -= 2  # só ímpares

        # ── Fase 3: atualizar o melhor global (com lock) ────────────────────
        if block_best is not None:
            with best.get_lock():
                if block_best > best.value:
                    best.value = block_best


def find_max_prime_parallel(timeout: int, workers: int) -> int:
    """
    Procura o maior número primo possível durante, no máximo, `timeout` segundos,
    utilizando `workers` processos em paralelo.

    Estratégia — blocos dinâmicos com contador atómico:
      - O espaço de pesquisa é dividido em blocos de BLOCK_SIZE candidatos ímpares.
      - Um contador atómico (`next_block`) distribui blocos sob demanda: cada
        worker reserva o próximo bloco livre de forma atómica e trabalha nele
        de forma completamente autónoma, sem mais comunicação até ao fim do bloco.
      - Dentro de cada bloco, a pesquisa é feita do maior para o menor candidato,
        parando no primeiro primo encontrado (o maior do bloco), o que reduz o
        trabalho médio por bloco aproximadamente a metade.
      - O maior primo global é mantido em `best` (Value com lock), atualizado
        por qualquer worker que encontre um valor superior.
      - A terminação é coordenada via `stop_event`: o processo principal aguarda
        o timeout e depois sinaliza todos os workers para pararem.

    Parâmetros:
        timeout (int) : Duração máxima da pesquisa, em segundos.
        workers (int) : Número de processos worker a lançar.

    Retorna:
        int: O maior número primo encontrado dentro do limite temporal.
    """
    # Objetos partilhados entre processos
    next_block = multiprocessing.Value('Q', 0)  # 'Q' = unsigned long long (64 bits)
    best = multiprocessing.Value('Q', 2)  # começa em 2 (menor primo válido)
    stop_event = multiprocessing.Event()

    # Lançar os workers
    pool = [
        multiprocessing.Process(
            target=_worker,
            args=(next_block, best, stop_event, BLOCK_SIZE),
            daemon=True,  # garantia extra: morrem se o processo pai morrer
        )
        for _ in range(workers)
    ]
    for p in pool:
        p.start()

    # Processo principal aguarda o timeout e sinaliza a paragem
    time.sleep(timeout)
    stop_event.set()

    # Aguardar que todos os workers terminem o bloco atual
    for p in pool:
        p.join()

    return best.value


# =============================================================================
# Ponto de entrada — comparação sequencial vs paralela
# =============================================================================

if __name__ == "__main__":
    TIMEOUT = 5  # segundos
    WORKERS = multiprocessing.cpu_count()

    print(f"CPUs disponíveis: {WORKERS}\n")

    print(f"[Sequencial] A correr durante {TIMEOUT}s...")
    t0 = time.monotonic()
    res_seq = find_max_prime_sequential(TIMEOUT)
    t1 = time.monotonic()
    print(f"  Maior primo : {res_seq}  ({len(str(res_seq))} algarismos)  [{t1 - t0:.2f}s]\n")

    print(f"[Paralela] A correr durante {TIMEOUT}s com {WORKERS} workers...")
    t0 = time.monotonic()
    res_par = find_max_prime_parallel(TIMEOUT, WORKERS)
    t1 = time.monotonic()
    print(f"  Maior primo : {res_par}  ({len(str(res_par))} algarismos)  [{t1 - t0:.2f}s]\n")

    speedup = res_par / res_seq
    print(f"Rácio paralela/sequencial : {speedup:.2f}x  (primo {speedup:.2f}x maior)")