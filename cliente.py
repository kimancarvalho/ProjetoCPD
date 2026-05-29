"""
Cliente RPC para invocacao remota das funcionalidades de computacao paralela.

Implementa um cliente JSON-RPC 2.0 sobre sockets TCP que se liga ao servidor
e disponibiliza um menu dinamico construido automaticamente por introspeção
remota via list_methods.

O menu dinamico adapta-se automaticamente as operacoes disponiveis no servidor,
sem necessidade de hardcoding. Os parametros sao recolhidos interactivamente
e validados antes do envio.

O campo 'id' em cada pedido permite correlacionar cada pedido com a resposta
correspondente, o que e essencial em cenarios onde um cliente pode ter
multiplos pedidos em curso simultaneamente.
"""

import socket
import json
import ast


class RPCClient:
    """
    Cliente RPC sobre sockets TCP com menu dinamico por introspeção remota.

    Establece uma ligacao TCP persistente com o servidor e mantem-na aberta
    durante toda a sessao do cliente. Cada pedido e numerado com um id
    incremental que permite correlacionar pedidos com respostas.

    O menu dinamico e construido automaticamente invocando list_methods
    no servidor, sem qualquer hardcoding das operacoes disponiveis.
    """

    def __init__(self, host: str = 'localhost', port: int = 8000) -> None:
        """
        Inicializa o cliente e establece a ligacao TCP com o servidor.

        Parametros:
            host : endereco do servidor
            port : porto do servidor
        """
        self.host       = host
        self.port       = port
        self.sock       = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.request_id = 0
        self.sock.connect((self.host, self.port))
        print(f"[CLIENTE] Ligado ao servidor em {self.host}:{self.port}")

    def invocar(self, metodo: str, params) -> object:
        """
        Envia um pedido JSON-RPC ao servidor e devolve o resultado.

        Serializa o pedido em JSON, envia pelo socket, recebe a resposta
        e deserializa. O campo 'id' e incrementado a cada pedido para
        permitir correlacao entre pedidos e respostas.

        Parametros:
            metodo : nome da funcao a invocar no servidor
            params : parametros da funcao (lista, dict ou misto)

        Retorna:
            object: resultado devolvido pelo servidor

        Lanca:
            ConnectionError : se o socket nao estiver ligado
            RuntimeError    : se o servidor devolver um erro
        """
        if not self.sock:
            raise ConnectionError("Socket nao esta ligado ao servidor.")

        self.request_id += 1

        pedido = {
            "jsonrpc": "2.0",
            "method" : metodo,
            "params" : params,
            "id"     : self.request_id,
        }

        self.sock.sendall(json.dumps(pedido).encode('utf-8'))

        dados    = self.sock.recv(65536)
        resposta = json.loads(dados.decode('utf-8'))

        if "result" in resposta:
            return resposta["result"]
        elif "error" in resposta:
            raise RuntimeError(f"Erro do servidor: {resposta['error']}")

        raise RuntimeError("Resposta invalida do servidor.")

    def menu_dinamico(self) -> None:
        """
        Apresenta um menu interactivo construido automaticamente por introspeção remota.

        Invoca list_methods no servidor para obter a lista de operacoes
        disponiveis, os seus parametros e descricoes. O menu e reconstruido
        a cada iteracao para reflectir eventuais alteracoes no servidor.

        Os argumentos obrigatorios sao recolhidos interactivamente. Os
        argumentos opcionais (com valor por defeito) podem ser omitidos
        premindo Enter, caso em que o servidor usa o valor por defeito.
        """
        try:
            metodos = self.invocar("list_methods", [])
        except Exception as e:
            print(f"[CLIENTE] Erro ao obter metodos do servidor: {e}")
            return

        while True:
            print("\n Menu Dinamico ")
            for i, m in enumerate(metodos, start=1):
                args_obrig = [a for a in m["args"] if "=" not in a]
                args_opcio = [a for a in m["args"] if "=" in a]

                partes = []
                if args_obrig:
                    partes.append(", ".join(args_obrig))
                if args_opcio:
                    partes.append("[" + ", ".join(args_opcio) + "]")
                indicador = "(" + ", ".join(partes) + ")"

                print(f"  {i}. {m['name']}{indicador}")
                print(f"     {m['description']}")

            print("  0. Sair")

            escolha = input("\nEscolha uma funcao (numero): ").strip()

            if escolha == "0":
                print("[CLIENTE] A terminar sessao.")
                self.sock.close()
                break

            if not escolha.isdigit() or not (1 <= int(escolha) <= len(metodos)):
                print("Opcao invalida.")
                continue

            metodo     = metodos[int(escolha) - 1]
            args_obrig = [a for a in metodo["args"] if "=" not in a]
            args_opcio = [a for a in metodo["args"] if "=" in a]

            argumentos         = []
            argumentos_nomeados = {}

            # Recolher argumentos obrigatorios
            for nome_arg in args_obrig:
                val = input(f"  {nome_arg} = ").strip()
                try:
                    argumentos.append(ast.literal_eval(val))
                except (ValueError, SyntaxError):
                    argumentos.append(val)

            # Recolher argumentos opcionais
            for arg_def in args_opcio:
                nome_arg = arg_def.split("=")[0]
                val      = input(f"  {arg_def} (Enter para usar valor por defeito): ").strip()
                if val != "":
                    try:
                        argumentos_nomeados[nome_arg] = ast.literal_eval(val)
                    except (ValueError, SyntaxError):
                        argumentos_nomeados[nome_arg] = val

            # Construir params e invocar
            if argumentos and argumentos_nomeados:
                params = {"__args__": argumentos, **argumentos_nomeados}
            elif argumentos_nomeados:
                params = argumentos_nomeados
            else:
                params = argumentos

            try:
                resultado = self.invocar(metodo["name"], params)
                print(f"\n  Resultado: {resultado}")
            except Exception as e:
                print(f"\n  Erro: {e}")

    def __getattr__(self, nome: str):
        """
        Permite invocar metodos remotos como se fossem metodos locais do cliente.

        Por exemplo: client.find_max_prime(5) e equivalente a
        client.invocar('find_max_prime', (5,))

        Parametros:
            nome : nome do metodo remoto a invocar

        Retorna:
            callable: funcao que envia o pedido ao servidor
        """
        def metodo(*args, **kwargs):
            if args and kwargs:
                return self.invocar(nome, {"__args__": args, **kwargs})
            elif kwargs:
                return self.invocar(nome, kwargs)
            else:
                return self.invocar(nome, args)
        return metodo


# Ponto de entrada
if __name__ == "__main__":
    cliente = RPCClient()
    print("\n A iniciar menu dinamico ")
    cliente.menu_dinamico()