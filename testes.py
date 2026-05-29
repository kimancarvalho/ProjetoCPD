"""
Testes automaticos para as implementacoes de primos.py e gameoflife.py.

Cobertura:
    primos.py
        - is_prime: casos limite, primos conhecidos, nao primos
        - find_max_prime_sequential: validade do resultado, respeito pelo timeout
        - find_max_prime_parallel: validade do resultado, consistencia com sequencial

    gameoflife.py
        - count_neighbors: celula no centro, nas bordas e nos cantos
        - next_cell_state: todas as 4 regras do Game of Life
        - next_generation: geracao correcta de uma grelha conhecida
        - game_of_life_sequential: grelha vazia, padrao estavel, Glider
        - game_of_life_parallel: consistencia com a versao sequencial

Execucao:
    python testes.py
    python -m unittest testes -v
"""

import unittest
import time
import random

from primos import is_prime, find_max_prime_sequential, find_max_prime_parallel
from gameoflife import (
    count_neighbors,
    next_cell_state,
    next_generation,
    game_of_life_sequential,
    game_of_life_parallel,
)


# =============================================================================
# Testes de is_prime
# =============================================================================

class TestIsPrime(unittest.TestCase):
    """Testes unitarios para a funcao is_prime."""

    def test_numeros_menores_que_2_nao_sao_primos(self):
        """Numeros abaixo de 2 nunca sao primos por definicao."""
        for n in [-10, -1, 0, 1]:
            with self.subTest(n=n):
                self.assertFalse(is_prime(n))

    def test_casos_base_2_e_3(self):
        """O 2 e o 3 sao os dois primeiros primos."""
        self.assertTrue(is_prime(2))
        self.assertTrue(is_prime(3))

    def test_multiplos_de_2_nao_sao_primos(self):
        """Numeros pares maiores que 2 nunca sao primos."""
        for n in [4, 6, 8, 100, 1000]:
            with self.subTest(n=n):
                self.assertFalse(is_prime(n))

    def test_multiplos_de_3_nao_sao_primos(self):
        """Multiplos de 3 maiores que 3 nunca sao primos."""
        for n in [9, 15, 21, 99]:
            with self.subTest(n=n):
                self.assertFalse(is_prime(n))

    def test_primos_conhecidos(self):
        """Lista de primos conhecidos que a funcao deve identificar correctamente."""
        primos = [5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 97, 101, 997]
        for n in primos:
            with self.subTest(n=n):
                self.assertTrue(is_prime(n))

    def test_nao_primos_conhecidos(self):
        """Lista de compostos conhecidos que a funcao deve rejeitar."""
        compostos = [4, 6, 8, 9, 10, 12, 25, 49, 100, 1000]
        for n in compostos:
            with self.subTest(n=n):
                self.assertFalse(is_prime(n))

    def test_primo_grande(self):
        """Verificacao de um primo grande conhecido."""
        self.assertTrue(is_prime(999983))

    def test_composto_grande(self):
        """Verificacao de um composto grande conhecido (999983 + 1 = 999984)."""
        self.assertFalse(is_prime(999984))


# =============================================================================
# Testes de find_max_prime_sequential
# =============================================================================

class TestFindMaxPrimeSequential(unittest.TestCase):
    """Testes para a funcao find_max_prime_sequential."""

    def test_resultado_e_primo(self):
        """O valor devolvido deve ser um numero primo valido."""
        resultado = find_max_prime_sequential(timeout=2)
        self.assertTrue(is_prime(resultado),
                        f"O resultado {resultado} nao e primo")

    def test_resultado_maior_que_2(self):
        """Com qualquer timeout razoavel, deve encontrar um primo maior que 2."""
        resultado = find_max_prime_sequential(timeout=2)
        self.assertGreater(resultado, 2)

    def test_respeita_timeout(self):
        """A funcao nao deve demorar significativamente mais que o timeout."""
        TIMEOUT = 2
        t0      = time.monotonic()
        find_max_prime_sequential(timeout=TIMEOUT)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, TIMEOUT + 1.0,
                        f"Demorou {elapsed:.2f}s com timeout={TIMEOUT}s")

    def test_timeout_maior_encontra_primo_maior(self):
        """Com mais tempo, a versao sequencial deve encontrar um primo maior."""
        res_curto = find_max_prime_sequential(timeout=1)
        res_longo = find_max_prime_sequential(timeout=3)
        self.assertGreaterEqual(res_longo, res_curto)


# =============================================================================
# Testes de find_max_prime_parallel
# =============================================================================

class TestFindMaxPrimeParallel(unittest.TestCase):
    """Testes para a funcao find_max_prime_parallel."""

    def test_resultado_e_primo(self):
        """O valor devolvido deve ser um numero primo valido."""
        resultado = find_max_prime_parallel(timeout=2, workers=2)
        self.assertTrue(is_prime(resultado),
                        f"O resultado {resultado} nao e primo")

    def test_resultado_maior_que_2(self):
        """Com qualquer timeout razoavel, deve encontrar um primo maior que 2."""
        resultado = find_max_prime_parallel(timeout=2, workers=2)
        self.assertGreater(resultado, 2)

    def test_respeita_timeout(self):
        """A funcao nao deve demorar significativamente mais que o timeout."""
        TIMEOUT = 2
        t0      = time.monotonic()
        find_max_prime_parallel(timeout=TIMEOUT, workers=2)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, TIMEOUT + 2.0,
                        f"Demorou {elapsed:.2f}s com timeout={TIMEOUT}s")

    def test_paralela_encontra_primo_maior_ou_igual_ao_sequencial(self):
        """A versao paralela deve encontrar um primo maior ou igual ao sequencial."""
        TIMEOUT  = 3
        WORKERS  = 4
        res_seq  = find_max_prime_sequential(timeout=TIMEOUT)
        res_par  = find_max_prime_parallel(timeout=TIMEOUT, workers=WORKERS)
        self.assertGreaterEqual(res_par, res_seq,
                                f"Paralela ({res_par}) < Sequencial ({res_seq})")

    def test_varios_workers(self):
        """A funcao deve funcionar correctamente com diferentes numeros de workers."""
        for workers in [1, 2, 4]:
            with self.subTest(workers=workers):
                resultado = find_max_prime_parallel(timeout=2, workers=workers)
                self.assertTrue(is_prime(resultado))



# Testes de count_neighbors
class TestCountNeighbors(unittest.TestCase):
    """Testes unitarios para a funcao count_neighbors."""

    def setUp(self):
        """Grelha de referencia 5x5 para os testes de vizinhanca."""
        self.grid = [
            [0, 1, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        self.rows = 5
        self.cols = 5

    def test_celula_centro_com_vizinhos(self):
        """Celula no centro da grelha com vizinhos conhecidos."""
        # Celula (1,1): vizinhos sao (0,0)=0,(0,1)=1,(0,2)=0,
        #               (1,0)=0,(1,2)=1,(2,0)=1,(2,1)=1,(2,2)=1 -> 5 vivos
        resultado = count_neighbors(self.grid, 1, 1, self.rows, self.cols)
        self.assertEqual(resultado, 5)

    def test_celula_canto_superior_esquerdo(self):
        """Celula no canto superior esquerdo tem apenas 3 vizinhos possiveis."""
        # Celula (0,0): vizinhos sao (0,1)=1,(1,0)=0,(1,1)=0 -> 1 vivo
        resultado = count_neighbors(self.grid, 0, 0, self.rows, self.cols)
        self.assertEqual(resultado, 1)

    def test_celula_canto_inferior_direito(self):
        """Celula no canto inferior direito tem apenas 3 vizinhos possiveis."""
        # Celula (4,4): vizinhos sao (3,3)=0,(3,4)=0,(4,3)=0 -> 0 vivos
        resultado = count_neighbors(self.grid, 4, 4, self.rows, self.cols)
        self.assertEqual(resultado, 0)

    def test_celula_borda_superior(self):
        """Celula na borda superior tem apenas 5 vizinhos possiveis."""
        # Celula (0,2): vizinhos sao (0,1)=1,(0,3)=0,(1,1)=0,(1,2)=1,(1,3)=0 -> 2 vivos
        resultado = count_neighbors(self.grid, 0, 2, self.rows, self.cols)
        self.assertEqual(resultado, 2)

    def test_grelha_completamente_viva(self):
        """Celula no centro de uma grelha totalmente viva tem 8 vizinhos vivos."""
        grid_viva = [[1] * 5 for _ in range(5)]
        resultado = count_neighbors(grid_viva, 2, 2, 5, 5)
        self.assertEqual(resultado, 8)

    def test_grelha_completamente_morta(self):
        """Qualquer celula numa grelha totalmente morta tem 0 vizinhos vivos."""
        grid_morta = [[0] * 5 for _ in range(5)]
        resultado  = count_neighbors(grid_morta, 2, 2, 5, 5)
        self.assertEqual(resultado, 0)



# Testes de next_cell_state
class TestNextCellState(unittest.TestCase):
    """Testes unitarios para as 4 regras do Game of Life."""

    def test_regra_solidao_menos_de_2_vizinhos(self):
        """Celula viva com 0 ou 1 vizinhos vivos morre por solidao."""
        for vizinhos in [0, 1]:
            with self.subTest(vizinhos=vizinhos):
                self.assertEqual(next_cell_state(1, vizinhos), 0)

    def test_regra_sobrevivencia_2_vizinhos(self):
        """Celula viva com 2 vizinhos vivos sobrevive."""
        self.assertEqual(next_cell_state(1, 2), 1)

    def test_regra_sobrevivencia_3_vizinhos(self):
        """Celula viva com 3 vizinhos vivos sobrevive."""
        self.assertEqual(next_cell_state(1, 3), 1)

    def test_regra_superpopulacao_mais_de_3_vizinhos(self):
        """Celula viva com 4 ou mais vizinhos vivos morre por superpopulacao."""
        for vizinhos in [4, 5, 6, 7, 8]:
            with self.subTest(vizinhos=vizinhos):
                self.assertEqual(next_cell_state(1, vizinhos), 0)

    def test_regra_reproducao_exactamente_3_vizinhos(self):
        """Celula morta com exactamente 3 vizinhos vivos nasce."""
        self.assertEqual(next_cell_state(0, 3), 1)

    def test_celula_morta_permanece_morta(self):
        """Celula morta com qualquer numero de vizinhos diferente de 3 permanece morta."""
        for vizinhos in [0, 1, 2, 4, 5, 6, 7, 8]:
            with self.subTest(vizinhos=vizinhos):
                self.assertEqual(next_cell_state(0, vizinhos), 0)



# Testes de next_generation
class TestNextGeneration(unittest.TestCase):
    """Testes para a funcao next_generation."""

    def test_grelha_vazia_permanece_vazia(self):
        """Uma grelha sem celulas vivas nao pode gerar novas celulas."""
        grid     = [[0] * 5 for _ in range(5)]
        esperado = [[0] * 5 for _ in range(5)]
        self.assertEqual(next_generation(grid, 5, 5), esperado)

    def test_bloco_2x2_e_estavel(self):
        """Um bloco 2x2 de celulas vivas e um padrao estavel -- nao muda."""
        grid = [
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 1, 1, 0],
            [0, 0, 0, 0],
        ]
        resultado = next_generation(grid, 4, 4)
        self.assertEqual(resultado, grid)

    def test_blinker_horizontal_para_vertical(self):
        """O Blinker horizontal deve tornar-se vertical apos 1 geracao."""
        blinker_h = [
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        blinker_v = [
            [0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        self.assertEqual(next_generation(blinker_h, 5, 5), blinker_v)



# Testes de game_of_life_sequential
class TestGameOfLifeSequential(unittest.TestCase):
    """Testes para a versao sequencial do Game of Life."""

    def test_grelha_vazia_permanece_vazia(self):
        """Uma grelha vazia deve permanecer vazia apos qualquer numero de geracoes."""
        grid     = [[0] * 10 for _ in range(10)]
        esperado = [[0] * 10 for _ in range(10)]
        resultado = game_of_life_sequential([row[:] for row in grid], 10)
        self.assertEqual(resultado, esperado)

    def test_bloco_2x2_e_estavel(self):
        """Um bloco 2x2 deve permanecer identico apos multiplas geracoes."""
        grid = [
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 1, 1, 0],
            [0, 0, 0, 0],
        ]
        resultado = game_of_life_sequential([row[:] for row in grid], 10)
        self.assertEqual(resultado, grid)

    def test_blinker_tem_periodo_2(self):
        """O Blinker deve regressar ao estado inicial apos 2 geracoes."""
        blinker = [
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        resultado = game_of_life_sequential([row[:] for row in blinker], 2)
        self.assertEqual(resultado, blinker)

    def test_glider_apos_4_geracoes(self):
        """O Glider deve deslocar-se uma posicao na diagonal apos 4 geracoes."""
        glider = [
            [0, 1, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        esperado = [
            [0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 1, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 0, 0],
        ]
        resultado = game_of_life_sequential([row[:] for row in glider], 4)
        self.assertEqual(resultado, esperado)

    def test_0_geracoes_devolve_grelha_original(self):
        """Com 0 geracoes, a grelha devolvida deve ser identica a original."""
        grid = [
            [0, 1, 0],
            [1, 0, 1],
            [0, 1, 0],
        ]
        resultado = game_of_life_sequential([row[:] for row in grid], 0)
        self.assertEqual(resultado, grid)



# Testes de game_of_life_parallel
class TestGameOfLifeParallel(unittest.TestCase):
    """Testes para a versao paralela do Game of Life."""

    def test_consistencia_com_sequencial_glider(self):
        """A versao paralela deve produzir o mesmo resultado que a sequencial no Glider."""
        glider = [
            [0, 1, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        res_seq = game_of_life_sequential([row[:] for row in glider], 4)
        res_par = game_of_life_parallel([row[:] for row in glider], 4, 2)
        self.assertEqual(res_seq, res_par)

    def test_consistencia_com_sequencial_grelha_aleatoria(self):
        """A versao paralela deve ser consistente com a sequencial numa grelha aleatoria."""
        random.seed(42)
        grid = [
            [1 if random.random() < 0.3 else 0 for _ in range(20)]
            for _ in range(20)
        ]
        res_seq = game_of_life_sequential([row[:] for row in grid], 10)
        res_par = game_of_life_parallel([row[:] for row in grid], 10, 4)
        self.assertEqual(res_seq, res_par)

    def test_varios_workers(self):
        """A versao paralela deve ser consistente com a sequencial para varios workers."""
        random.seed(99)
        grid = [
            [1 if random.random() < 0.3 else 0 for _ in range(20)]
            for _ in range(20)
        ]
        res_seq = game_of_life_sequential([row[:] for row in grid], 5)
        for workers in [1, 2, 4]:
            with self.subTest(workers=workers):
                res_par = game_of_life_parallel([row[:] for row in grid], 5, workers)
                self.assertEqual(res_seq, res_par,
                                 f"Inconsistencia com {workers} workers")

    def test_grelha_vazia_permanece_vazia(self):
        """A versao paralela deve manter uma grelha vazia sempre vazia."""
        grid     = [[0] * 10 for _ in range(10)]
        esperado = [[0] * 10 for _ in range(10)]
        resultado = game_of_life_parallel([row[:] for row in grid], 10, 2)
        self.assertEqual(resultado, esperado)

    def test_bloco_estavel(self):
        """A versao paralela deve manter um bloco 2x2 estavel."""
        grid = [
            [0, 0, 0, 0],
            [0, 1, 1, 0],
            [0, 1, 1, 0],
            [0, 0, 0, 0],
        ]
        resultado = game_of_life_parallel([row[:] for row in grid], 10, 2)
        self.assertEqual(resultado, grid)



# Ponto de entrada
if __name__ == "__main__":
    unittest.main(verbosity=2)