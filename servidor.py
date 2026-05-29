"""
Servidor RPC para exposicao remota das funcionalidades de computacao paralela.

Implementa um servidor JSON-RPC 2.0 sobre sockets TCP que disponibiliza
remotamente as funcoes implementadas em primos.py e gameoflife.py.

Operacoes disponibilizadas:
    find_max_prime(timeout, workers)  : procura o maior primo em tempo limitado
    is_prime(n)                       : verifica se um numero e primo
    game_of_life(grid, generations)   : simula o Game of Life
    list_methods()                    : lista as operacoes disponiveis

O servidor aceita multiplos clientes em simultaneo, lancando uma thread
dedicada por cada ligacao recebida. A escolha de threads em vez de processos
e adequada porque cada thread passa a maior parte do tempo bloqueada em
operacoes de rede (I/O bound), libertando o GIL naturalmente e permitindo
verdadeiro atendimento concorrente sem o overhead de criacao de processos.

O registo das funcoes e feito automaticamente por introspeção, sem
hardcoding dos nomes ou assinaturas.
"""

import socket
import json
import inspect
import threading
import multiprocessing
import sys

from primos import is_prime, find_max_prime_parallel
from gameoflife import game_of_life_parallel



# Funcoes expostas remotamente
#
# Estas funcoes constituem a API publica do servidor. Sao registadas
# automaticamente pelo mecanismo de introspeção e expostas aos clientes.
# As docstrings sao utilizadas pelo cliente para construir o menu dinamico.


def find_max_prime(timeout: int, workers: int = multiprocessing.cpu_count()) -> int:
    """Procura o maior numero primo possivel durante timeout segundos."""
    return find_max_prime_parallel(timeout, workers)


def verificar_primo(n: int) -> bool:
    """Verifica se o numero n e primo. Devolve True se for primo, False caso contrario."""
    return is_prime(n)


def game_of_life(tamanho: int, generations: int,
                 workers: int = multiprocessing.cpu_count()) -> dict:
    """Simula o Game of Life numa grelha quadrada tamanho x tamanho e devolve celulas vivas e tempo."""
    import random
    import time

    random.seed()
    grid = [
        [1 if random.random() < 0.3 else 0 for _ in range(tamanho)]
        for _ in range(tamanho)
    ]

    celulas_iniciais = sum(sum(row) for row in grid)

    t0        = time.monotonic()
    resultado = game_of_life_parallel(grid, generations, workers)
    elapsed   = time.monotonic() - t0

    celulas_finais = sum(sum(row) for row in resultado)

    return {
        "tamanho"         : tamanho,
        "geracoes"        : generations,
        "workers"         : workers,
        "celulas_iniciais": celulas_iniciais,
        "celulas_finais"  : celulas_finais,
        "tempo_execucao"  : round(elapsed, 3),
    }



# Servidor RPC

class RPCServer:
    """
    Servidor RPC sobre sockets TCP com suporte a multiplos clientes concorrentes.

    Regista automaticamente por introspeção todas as funcoes publicas definidas
    neste modulo (que nao comecam por '_' e nao pertencem a modulos importados).
    Cada cliente e atendido numa thread dedicada, permitindo atendimento
    simultaneo sem bloqueio do loop principal de aceitacao de ligacoes.
    """

    def __init__(self, host: str = 'localhost', port: int = 8000) -> None:
        """
        Inicializa o servidor e regista automaticamente as funcoes disponiveis.

        Parametros:
            host : endereco de escuta do servidor
            port : porto de escuta do servidor
        """
        self.host  = host
        self.port  = port
        self.funcs = {}
        self._registar_funcoes()

    def _registar_funcoes(self) -> None:
        """
        Regista automaticamente todas as funcoes publicas deste modulo.

        Usa introspeção para identificar as funcoes definidas localmente,
        excluindo funcoes privadas (prefixo '_') e funcoes importadas de
        outros modulos, garantindo que apenas a API publica e exposta.
        """

        modulo_actual = sys.modules[__name__]
        for nome, func in inspect.getmembers(modulo_actual, inspect.isfunction):
            if nome.startswith('_'):
                continue
            if func.__module__ != __name__:
                continue
            self._registar(nome, func)

    def _registar(self, nome: str, func) -> None:
        """
        Regista uma funcao no dicionario de funcoes disponiveis.

        Parametros:
            nome : nome pelo qual a funcao sera invocada remotamente
            func : referencia para a funcao a registar
        """
        self.funcs[nome] = func
        print(f"[SERVIDOR] Metodo registado: {nome}")

    def _list_methods(self) -> list:
        """
        Constroi a lista de metadados de todas as funcoes registadas.

        Usa introspeção para obter automaticamente o nome, parametros
        e descricao de cada funcao, sem necessidade de hardcoding.

        Retorna:
            list: lista de dicionarios com name, args e description
        """
        funcoes = []
        for nome, func in self.funcs.items():
            sig        = inspect.signature(func)
            parametros = []
            for p in sig.parameters.values():
                if p.default != inspect.Parameter.empty:
                    parametros.append(f"{p.name}={p.default!r}")
                else:
                    parametros.append(p.name)
            funcoes.append({
                "name"       : nome,
                "args"       : parametros,
                "description": inspect.getdoc(func) or "",
            })
        return funcoes

    def _processar_pedido(self, pedido_json: str) -> str:
        """
        Processa um pedido JSON-RPC: faz o parsing, despacha para a funcao
        correcta e devolve a resposta serializada em JSON.

        O dispatch suporta tres formas de parametros:
            lista   : func(*args)
            dict    : func(**kwargs)
            misto   : func(*args, **kwargs) via chave especial '__args__'

        Parametros:
            pedido_json : pedido recebido do cliente em formato JSON

        Retorna:
            str: resposta serializada em JSON com 'result' ou 'error'
        """
        pedido = None
        try:
            pedido = json.loads(pedido_json)

            metodo = pedido.get("method")
            params = pedido.get("params", {})
            req_id = pedido.get("id")

            # list_methods e tratado directamente pelo servidor
            # e nao precisa de estar registado como funcao
            if metodo == "list_methods":
                return json.dumps({
                    "jsonrpc": "2.0",
                    "result" : self._list_methods(),
                    "id"     : req_id,
                })

            # Validar se o metodo existe
            func = self.funcs.get(metodo)
            if not func:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error"  : f"Metodo '{metodo}' nao encontrado.",
                    "id"     : req_id,
                })

            # Dispatch dinamico com suporte a lista, dict e misto
            if isinstance(params, dict) and '__args__' in params:
                args   = params.pop('__args__')
                result = func(*args, **params)
            elif isinstance(params, dict):
                result = func(**params)
            elif isinstance(params, list):
                result = func(*params)
            else:
                result = func(params)

            return json.dumps({
                "jsonrpc": "2.0",
                "result" : result,
                "id"     : req_id,
            })

        except json.JSONDecodeError:
            return json.dumps({
                "jsonrpc": "2.0",
                "error"  : "Pedido JSON invalido.",
                "id"     : None,
            })
        except TypeError as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "error"  : f"Parametros incorrectos: {e}",
                "id"     : pedido.get("id") if pedido else None,
            })
        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "error"  : str(e),
                "id"     : pedido.get("id") if pedido else None,
            })

    def _thread_cliente(self, conn: socket.socket, addr: tuple) -> None:
        """
        Funcao executada pela thread dedicada a cada cliente.

        Mantém a ligacao aberta enquanto o cliente enviar pedidos,
        processando cada um e devolvendo a resposta correspondente.
        A ligacao e encerrada quando o cliente se desliga (recv devolve b'').

        Parametros:
            conn : socket da ligacao com o cliente
            addr : endereco do cliente (host, port)
        """
        print(f"[SERVIDOR] Ligacao de {addr}")
        with conn:
            while True:
                try:
                    dados = conn.recv(4096)
                    if not dados:
                        print(f"[SERVIDOR] Cliente {addr} desligou-se.")
                        break
                    pedido = dados.decode('utf-8')
                    print(f"[SERVIDOR] Pedido de {addr}: {pedido}")
                    resposta = self._processar_pedido(pedido)
                    print(f"[SERVIDOR] Resposta para {addr}: {resposta}")
                    conn.sendall(resposta.encode('utf-8'))
                except ConnectionResetError:
                    print(f"[SERVIDOR] Ligacao com {addr} encerrada abruptamente.")
                    break
                except Exception as e:
                    print(f"[SERVIDOR] Erro com cliente {addr}: {e}")
                    break

    def start(self) -> None:
        """
        Inicia o servidor e entra no loop principal de aceitacao de ligacoes.

        Para cada cliente que se liga, lanca uma thread dedicada que gere
        a comunicacao de forma independente, permitindo atendimento simultaneo
        de multiplos clientes sem bloquear o loop principal.
        """
        print(f"[SERVIDOR] A escutar em {self.host}:{self.port} ...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(
                    target=self._thread_cliente,
                    args=(conn, addr),
                    daemon=True,
                )
                thread.start()
                print(f"[SERVIDOR] Thread lancada para {addr}. "
                      f"Clientes activos: {threading.active_count() - 1}")



# Ponto de entrada
if __name__ == "__main__":
    servidor = RPCServer()
    servidor.start()
