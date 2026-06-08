from database import criar_tabelas
from services import (
    garantir_primeiro_porteiro,
    autenticar_service,
    inserir_pessoa_service,
    listar_pessoas_service,
    listar_por_tipo_service,
    listar_dentro_service,
    buscar_pessoa_service,
    editar_pessoa_service,
    remover_pessoa_service,
    registrar_entrada_service,
    registrar_saida_service,
    relatorio_por_dia_service,
)

TIPOS_VALIDOS = {"morador", "visitante", "prestador", "entregador"}


def cadastrar():
    print("\n=== CADASTRAR ===")
    nome = input("Nome: ").strip()
    documento = input("Documento: ").strip()
    tipo = input("Tipo (morador/visitante/prestador/entregador): ").strip().lower()

    quadra = None
    lote = None
    if tipo == "morador":
        quadra = input("Quadra: ").strip()
        lote = input("Lote: ").strip()

    ok, msg = inserir_pessoa_service(nome, documento, tipo, quadra, lote)
    print(msg)


def listar():
    pessoas = listar_pessoas_service()
    print("\n=== LISTA ===")
    if not pessoas:
        print("Nenhuma pessoa cadastrada.")
        return

    for p in pessoas:
        print(f"{p['nome']} | {p['documento']} | {p['tipo']} | {p['quadra_lote'] or '-'} | {p['status']}")


def listar_por_tipo():
    print("\n=== LISTAR POR TIPO ===")
    tipo = input("Tipo (morador/visitante/prestador/entregador): ").strip().lower()
    ok, msg, lista = listar_por_tipo_service(tipo)
    if not ok:
        print(msg)
        return

    if not lista:
        print("Nenhuma pessoa desse tipo.")
        return

    for p in lista:
        print(f"{p['nome']} | {p['documento']} | {p['tipo']} | {p['quadra_lote'] or '-'} | {p['status']}")


def pessoas_dentro():
    lista = listar_dentro_service()
    print("\n=== PESSOAS DENTRO ===")
    if not lista:
        print("Ninguém está dentro.")
        return

    for p in lista:
        print(f"{p['nome']} | {p['documento']} | {p['tipo']} | {p['quadra_lote'] or '-'}")


def registrar_entrada(porteiro: str):
    print("\n=== ENTRADA ===")
    documento = input("Documento: ").strip()

    pessoa = buscar_pessoa_service(documento)
    if not pessoa:
        print("Pessoa não encontrada.")
        return

    quadra = None
    lote = None
    if pessoa["tipo"] != "morador":
        quadra = input("Quadra do destino: ").strip()
        lote = input("Lote do destino: ").strip()

    ok, msg = registrar_entrada_service(documento, quadra, lote, porteiro)
    print(msg)


def registrar_saida(porteiro: str):
    print("\n=== SAÍDA ===")
    documento = input("Documento: ").strip()
    ok, msg = registrar_saida_service(documento, porteiro)
    print(msg)


def editar():
    print("\n=== EDITAR ===")
    documento = input("Documento da pessoa: ").strip()

    p = buscar_pessoa_service(documento)
    if not p:
        print("Pessoa não encontrada.")
        return

    print(f"Atual: {p['nome']} | {p['tipo']} | {p['quadra_lote'] or '-'}")

    nome = input("Novo nome (enter mantém): ").strip()
    tipo = input("Novo tipo (enter mantém): ").strip().lower()
    quadra_lote = input("Novo Quadra|Lote (enter mantém / vazio remove): ")

    if nome == "":
        nome = ""
    if tipo == "":
        tipo = ""

    # se usuário só der enter aqui, vamos passar None para "manter"
    if quadra_lote == "":
        quadra_lote = None
    else:
        # se ele digitar espaços, remove
        quadra_lote = quadra_lote.strip()
        if quadra_lote == "":
            quadra_lote = ""

    ok, msg = editar_pessoa_service(documento, nome, tipo, quadra_lote)
    print(msg)


def remover():
    print("\n=== REMOVER ===")
    documento = input("Documento da pessoa: ").strip()

    p = buscar_pessoa_service(documento)
    if not p:
        print("Pessoa não encontrada.")
        return

    confirma = input(f"Confirma remover {p['nome']}? (s/n): ").strip().lower()
    if confirma != "s":
        print("Cancelado.")
        return

    ok, msg = remover_pessoa_service(documento)
    print(msg)


def relatorio():
    print("\n=== HISTÓRICO POR DIA ===")
    data = input("Data (AAAA-MM-DD): ").strip()

    ok, msg, eventos = relatorio_por_dia_service(data)
    if not ok:
        print(msg)
        return

    if not eventos:
        print("Nenhum evento.")
        return

    for e in eventos:
        print(
            f"{e['data_hora']} | {e['acao']} | {e['nome']} | {e['documento']} | {e['tipo']} | "
            f"porteiro: {e['porteiro']} | destino: {e['destino'] or '-'}"
        )


def menu():
    criar_tabelas()
    garantir_primeiro_porteiro()

    porteiro = None
    while porteiro is None:
        ok, msg, user = autenticar_service()
        print(msg)
        if ok:
            porteiro = user

    while True:
        print("\n===== MENU =====")
        print("1 - Cadastrar")
        print("2 - Listar")
        print("3 - Listar por tipo")
        print("4 - Entrada")
        print("5 - Saída")
        print("6 - Pessoas dentro")
        print("7 - Histórico por dia")
        print("8 - Editar")
        print("9 - Remover")
        print("0 - Sair")

        op = input("Escolha: ").strip()

        if op == "1":
            cadastrar()
        elif op == "2":
            listar()
        elif op == "3":
            listar_por_tipo()
        elif op == "4":
            registrar_entrada(porteiro)
        elif op == "5":
            registrar_saida(porteiro)
        elif op == "6":
            pessoas_dentro()
        elif op == "7":
            relatorio()
        elif op == "8":
            editar()
        elif op == "9":
            remover()
        elif op == "0":
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    menu()