from __future__ import annotations

import os
import re
import uuid
import shutil
import hashlib
import binascii
from datetime import datetime, timedelta
from pathlib import Path

from database import (
    inserir_condominio, listar_condominios, buscar_condominio,
    buscar_condominio_por_slug, atualizar_condominio, contar_condominios,
    inserir_pessoa, listar_pessoas, contar_pessoas, listar_pessoas_por_tipo,
    listar_dentro, contar_dentro, buscar_pessoa, buscar_pessoas_por_nome,
    editar_pessoa, remover_pessoa, atualizar_status,
    registrar_historico, relatorio_por_data,
    contar_entradas_hoje, contar_saidas_hoje, ultimas_movimentacoes,
    esta_autorizado, autorizar_documento, revogar_documento,
    contar_superadmins, contar_usuarios_condominio,
    inserir_usuario, buscar_usuario, listar_usuarios_condominio,
    listar_todos_usuarios, atualizar_usuario, remover_usuario,
    registrar_log_admin, listar_log_admin,
    inserir_veiculo, listar_veiculos, buscar_veiculo, listar_veiculos_dentro,
    atualizar_status_veiculo, editar_veiculo, remover_veiculo,
    registrar_historico_veiculo, relatorio_veiculos_por_data, contar_veiculos_dentro,
    inserir_qrcode, buscar_qrcode, listar_qrcodes, marcar_qrcode_usado,
    DB_PATH,
)

TIPOS_VALIDOS  = {"morador", "visitante", "prestador", "entregador"}
PERFIS_COND    = {"sindico", "admin", "porteiro"}
PERFIS_VALIDOS = {"superadmin"} | PERFIS_COND


# ================================================================
# HELPERS
# ================================================================

def _hash_senha(senha: str, salt_bytes: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt_bytes, 120_000)
    return binascii.hexlify(dk).decode("ascii")


def _gerar_slug(nome: str) -> str:
    s = nome.lower().strip()
    for src, dst in [("áàãâä","a"),("éèêë","e"),("íìîï","i"),("óòõôö","o"),("úùûü","u"),("ç","c")]:
        for c in src:
            s = s.replace(c, dst)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def montar_destino(quadra: str | None, lote: str | None) -> str | None:
    if quadra and lote:
        return f"{quadra.strip().upper()}|{lote.strip().upper()}"
    return None


# ================================================================
# BOOT
# ================================================================

def garantir_superadmin() -> None:
    if contar_superadmins() > 0:
        return
    print("\n⚠️  Criando superadmin padrão  →  usuário: admin  /  senha: admin123")
    print("     TROQUE A SENHA APÓS O PRIMEIRO LOGIN!\n")
    salt = os.urandom(16)
    inserir_usuario(
        condominio_id=None,
        usuario="admin",
        senha_hash=_hash_senha("admin123", salt),
        salt=binascii.hexlify(salt).decode("ascii"),
        perfil="superadmin",
    )


# ================================================================
# AUTENTICAÇÃO
# ================================================================

def autenticar_login_service(usuario: str, senha: str) -> tuple[bool, str, dict | None]:
    row = buscar_usuario(usuario)
    if not row:
        return False, "Usuário ou senha inválidos.", None
    if not row["ativo"]:
        return False, "Usuário desativado.", None

    if row["perfil"] != "superadmin" and row["condominio_id"]:
        cond = buscar_condominio(row["condominio_id"])
        if not cond or not cond["ativo"]:
            return False, "Condomínio inativo. Entre em contato com o suporte.", None

    salt = binascii.unhexlify(row["salt"])
    if _hash_senha(senha, salt) != row["senha_hash"]:
        return False, "Usuário ou senha inválidos.", None

    return True, f"Bem-vindo, {usuario}", {
        "usuario": row["usuario"],
        "perfil":  row["perfil"],
        "condominio_id": row["condominio_id"],
    }


def trocar_senha_service(usuario: str, senha_atual: str, nova_senha: str) -> tuple[bool, str]:
    ok, _, _ = autenticar_login_service(usuario, senha_atual)
    if not ok:
        return False, "Senha atual incorreta."
    if len(nova_senha) < 4:
        return False, "Nova senha muito curta."
    salt = os.urandom(16)
    atualizar_usuario(usuario, _hash_senha(nova_senha, salt), binascii.hexlify(salt).decode("ascii"), None, None)
    return True, "Senha alterada com sucesso."


# ================================================================
# REGISTRO DE CONDOMÍNIO
# ================================================================

def registrar_condominio_service(
    nome_cond: str, endereco: str | None,
    usuario_sindico: str, senha_sindico: str,
) -> tuple[bool, str]:
    nome_cond       = (nome_cond or "").strip()
    usuario_sindico = (usuario_sindico or "").strip()
    senha_sindico   = (senha_sindico or "").strip()

    if not nome_cond or not usuario_sindico or not senha_sindico:
        return False, "Todos os campos são obrigatórios."
    if len(senha_sindico) < 4:
        return False, "Senha deve ter pelo menos 4 caracteres."
    if buscar_usuario(usuario_sindico):
        return False, "Esse nome de usuário já está em uso."

    slug_base = _gerar_slug(nome_cond)
    slug, n = slug_base, 1
    while buscar_condominio_por_slug(slug):
        slug = f"{slug_base}-{n}"; n += 1

    cond_id = inserir_condominio(nome_cond, endereco, slug)

    salt = os.urandom(16)
    inserir_usuario(
        condominio_id=cond_id,
        usuario=usuario_sindico,
        senha_hash=_hash_senha(senha_sindico, salt),
        salt=binascii.hexlify(salt).decode("ascii"),
        perfil="sindico",
    )

    registrar_log_admin(cond_id, usuario_sindico, "registro_condominio", nome_cond)
    return True, "Condomínio cadastrado com sucesso!"


# ================================================================
# CONDOMÍNIOS
# ================================================================

def listar_condominios_service():
    rows = listar_condominios()
    result = []
    for r in rows:
        d = dict(r)
        d["total_usuarios"] = contar_usuarios_condominio(d["id"])
        d["total_pessoas"]  = contar_pessoas(d["id"])
        result.append(d)
    return result


def buscar_condominio_service(condominio_id: int):
    row = buscar_condominio(condominio_id)
    return dict(row) if row else None


def atualizar_condominio_service(
    condominio_id: int, nome: str, endereco: str | None,
    ativo: int, usuario_acao: str,
) -> tuple[bool, str]:
    if not buscar_condominio(condominio_id):
        return False, "Condomínio não encontrado."
    atualizar_condominio(condominio_id, nome, endereco, ativo)
    registrar_log_admin(condominio_id, usuario_acao, "edicao_condominio", nome)
    return True, "Condomínio atualizado."


# ================================================================
# PESSOAS
# ================================================================

def inserir_pessoa_service(
    condominio_id: int, nome: str, documento: str, tipo: str,
    quadra: str | None, lote: str | None,
    foto: str | None = None, usuario_acao: str | None = None,
) -> tuple[bool, str]:
    nome = (nome or "").strip()
    documento = (documento or "").strip()
    tipo = (tipo or "").strip().lower()

    if not nome or not documento:
        return False, "Nome e documento são obrigatórios."
    if tipo not in TIPOS_VALIDOS:
        return False, "Tipo inválido."

    destino = montar_destino(quadra, lote)
    if tipo == "morador" and not destino:
        return False, "Morador precisa de quadra e lote."
    if buscar_pessoa(condominio_id, documento):
        return False, "Já existe uma pessoa com esse documento."

    inserir_pessoa(condominio_id, nome, documento, tipo, destino, foto)
    if usuario_acao:
        registrar_log_admin(condominio_id, usuario_acao, "cadastro_pessoa", f"{nome} ({documento})")
    return True, "Pessoa cadastrada com sucesso."


def listar_pessoas_service(condominio_id: int, limit: int | None = None, offset: int | None = None):
    return [dict(r) for r in listar_pessoas(condominio_id, limit=limit, offset=offset)]


def contar_pessoas_service(condominio_id: int) -> int:
    return contar_pessoas(condominio_id)


def listar_por_tipo_service(condominio_id: int, tipo: str):
    tipo = (tipo or "").strip().lower()
    if tipo not in TIPOS_VALIDOS:
        return False, "Tipo inválido.", []
    return True, "OK", [dict(r) for r in listar_pessoas_por_tipo(condominio_id, tipo)]


def listar_dentro_service(condominio_id: int):
    return [dict(r) for r in listar_dentro(condominio_id)]


def buscar_pessoa_service(condominio_id: int, documento: str):
    row = buscar_pessoa(condominio_id, (documento or "").strip())
    return dict(row) if row else None


def buscar_por_nome_service(condominio_id: int, nome: str):
    if not (nome or "").strip():
        return []
    return [dict(r) for r in buscar_pessoas_por_nome(condominio_id, nome.strip())]


def editar_pessoa_service(
    condominio_id: int, documento: str, nome: str, tipo: str,
    quadra_lote: str | None, foto: str | None = None,
    usuario_acao: str | None = None,
) -> tuple[bool, str]:
    documento = (documento or "").strip()
    nome = (nome or "").strip()
    tipo = (tipo or "").strip().lower()

    p = buscar_pessoa(condominio_id, documento)
    if not p:
        return False, "Pessoa não encontrada."
    if tipo and tipo not in TIPOS_VALIDOS:
        return False, "Tipo inválido."

    if quadra_lote is not None:
        quadra_lote = quadra_lote.strip() or None

    nome_f = nome if nome else p["nome"]
    tipo_f = tipo if tipo else p["tipo"]
    ql_f   = quadra_lote if quadra_lote is not None else p["quadra_lote"]

    editar_pessoa(condominio_id, documento, nome_f, tipo_f, ql_f, foto)
    if usuario_acao:
        registrar_log_admin(condominio_id, usuario_acao, "edicao_pessoa", f"{nome_f} ({documento})")
    return True, "Pessoa atualizada com sucesso."


def remover_pessoa_service(condominio_id: int, documento: str, usuario_acao: str | None = None) -> tuple[bool, str]:
    p = buscar_pessoa(condominio_id, (documento or "").strip())
    if not p:
        return False, "Pessoa não encontrada."
    if p["status"] == "DENTRO":
        return False, "Pessoa está DENTRO. Registre a saída primeiro."
    if usuario_acao:
        registrar_log_admin(condominio_id, usuario_acao, "remocao_pessoa", f"{p['nome']} ({documento})")
    remover_pessoa(condominio_id, documento)
    return True, "Pessoa removida."


# ================================================================
# ENTRADA / SAÍDA
# ================================================================

def registrar_entrada_service(
    condominio_id: int, documento: str,
    quadra: str | None, lote: str | None, porteiro: str,
) -> tuple[bool, str, dict | None]:
    documento = (documento or "").strip()
    pessoa = buscar_pessoa(condominio_id, documento)
    if not pessoa:
        return False, "Pessoa não encontrada.", None
    if pessoa["status"] == "DENTRO":
        return False, "Pessoa já está DENTRO.", None

    destino = montar_destino(quadra, lote)
    if destino and pessoa["tipo"] != "morador":
        if not esta_autorizado(condominio_id, documento, destino):
            return False, "Documento NÃO autorizado para esse destino.", None

    atualizar_status(condominio_id, documento, "DENTRO")
    registrar_historico(condominio_id, documento, "entrada", destino, porteiro)
    return True, "Entrada registrada.", dict(pessoa)


def registrar_saida_service(
    condominio_id: int, documento: str, porteiro: str,
) -> tuple[bool, str, dict | None]:
    documento = (documento or "").strip()
    pessoa = buscar_pessoa(condominio_id, documento)
    if not pessoa:
        return False, "Pessoa não encontrada.", None
    if pessoa["status"] != "DENTRO":
        return False, "Pessoa já está FORA.", None

    atualizar_status(condominio_id, documento, "FORA")
    registrar_historico(condominio_id, documento, "saida", None, porteiro)
    return True, "Saída registrada.", dict(pessoa)


# ================================================================
# VEÍCULOS
# ================================================================

def cadastrar_veiculo_service(
    condominio_id: int, placa: str, modelo: str | None,
    cor: str | None, empresa: str | None,
    pessoa_documento: str | None, usuario_acao: str | None = None,
) -> tuple[bool, str]:
    placa = (placa or "").strip().upper()
    if not placa:
        return False, "Placa é obrigatória."
    if buscar_veiculo(condominio_id, placa):
        return False, "Veículo já cadastrado."
    inserir_veiculo(condominio_id, placa, modelo, cor, empresa, pessoa_documento)
    if usuario_acao:
        registrar_log_admin(condominio_id, usuario_acao, "cadastro_veiculo", placa)
    return True, "Veículo cadastrado com sucesso."


def listar_veiculos_service(condominio_id: int):
    return [dict(r) for r in listar_veiculos(condominio_id)]


def buscar_veiculo_service(condominio_id: int, placa: str):
    row = buscar_veiculo(condominio_id, placa)
    return dict(row) if row else None


def listar_veiculos_dentro_service(condominio_id: int):
    return [dict(r) for r in listar_veiculos_dentro(condominio_id)]


def editar_veiculo_service(
    condominio_id: int, placa: str, modelo: str | None,
    cor: str | None, empresa: str | None,
    pessoa_documento: str | None, usuario_acao: str | None = None,
) -> tuple[bool, str]:
    placa = (placa or "").strip().upper()
    if not buscar_veiculo(condominio_id, placa):
        return False, "Veículo não encontrado."
    editar_veiculo(condominio_id, placa, modelo, cor, empresa, pessoa_documento)
    if usuario_acao:
        registrar_log_admin(condominio_id, usuario_acao, "edicao_veiculo", placa)
    return True, "Veículo atualizado."


def remover_veiculo_service(condominio_id: int, placa: str, usuario_acao: str | None = None) -> tuple[bool, str]:
    placa = (placa or "").strip().upper()
    v = buscar_veiculo(condominio_id, placa)
    if not v:
        return False, "Veículo não encontrado."
    if v["status"] == "DENTRO":
        return False, "Veículo está DENTRO. Registre a saída primeiro."
    if usuario_acao:
        registrar_log_admin(condominio_id, usuario_acao, "remocao_veiculo", placa)
    remover_veiculo(condominio_id, placa)
    return True, "Veículo removido."


def entrada_veiculo_service(
    condominio_id: int, placa: str,
    destino: str | None, porteiro: str,
) -> tuple[bool, str, dict | None]:
    placa = (placa or "").strip().upper()
    v = buscar_veiculo(condominio_id, placa)
    if not v:
        return False, "Veículo não cadastrado.", None
    if v["status"] == "DENTRO":
        return False, "Veículo já está DENTRO.", None
    atualizar_status_veiculo(condominio_id, placa, "DENTRO")
    registrar_historico_veiculo(condominio_id, placa, "entrada", destino, porteiro)
    return True, "Entrada do veículo registrada.", dict(v)


def saida_veiculo_service(
    condominio_id: int, placa: str, porteiro: str,
) -> tuple[bool, str, dict | None]:
    placa = (placa or "").strip().upper()
    v = buscar_veiculo(condominio_id, placa)
    if not v:
        return False, "Veículo não encontrado.", None
    if v["status"] != "DENTRO":
        return False, "Veículo já está FORA.", None
    atualizar_status_veiculo(condominio_id, placa, "FORA")
    registrar_historico_veiculo(condominio_id, placa, "saida", None, porteiro)
    return True, "Saída do veículo registrada.", dict(v)


def relatorio_veiculos_service(condominio_id: int, data_iso: str):
    data_iso = (data_iso or "").strip()
    if not data_iso:
        return False, "Data obrigatória.", []
    rows = relatorio_veiculos_por_data(condominio_id, data_iso)
    return True, "OK", [dict(r) for r in rows]


# ================================================================
# QR CODE
# ================================================================

def gerar_qrcode_service(
    condominio_id: int, nome_visitante: str,
    documento_visitante: str | None, destino: str | None,
    criado_por: str, horas_validade: int = 24,
) -> tuple[bool, str, str | None]:
    nome_visitante = (nome_visitante or "").strip()
    if not nome_visitante:
        return False, "Nome do visitante é obrigatório.", None

    token = str(uuid.uuid4())
    expira_em = (datetime.now() + timedelta(hours=horas_validade)).isoformat(timespec="seconds")
    inserir_qrcode(condominio_id, token, nome_visitante, documento_visitante, destino, criado_por, expira_em)
    registrar_log_admin(condominio_id, criado_por, "geracao_qrcode", f"{nome_visitante} → {destino or 'sem destino'}")
    return True, "QR Code gerado.", token


def validar_qrcode_service(token: str, porteiro: str, condominio_id: int) -> tuple[bool, str, dict | None]:
    row = buscar_qrcode(token)
    if not row:
        return False, "QR Code inválido.", None
    if int(row["condominio_id"]) != condominio_id:
        return False, "QR Code não pertence a este condomínio.", None
    if row["usado"]:
        return False, "QR Code já foi utilizado.", None

    expira = datetime.fromisoformat(row["expira_em"])
    if datetime.now() > expira:
        return False, "QR Code expirado.", None

    marcar_qrcode_usado(token)

    # Registra entrada automática se visitante tiver documento
    if row["documento_visitante"]:
        p = buscar_pessoa(condominio_id, row["documento_visitante"])
        if p and p["status"] == "FORA":
            atualizar_status(condominio_id, row["documento_visitante"], "DENTRO")
            registrar_historico(condominio_id, row["documento_visitante"], "entrada", row["destino"], porteiro)

    return True, f"Acesso liberado para {row['nome_visitante']}.", dict(row)


def listar_qrcodes_service(condominio_id: int):
    rows = listar_qrcodes(condominio_id)
    agora = datetime.now().isoformat(timespec="seconds")
    result = []
    for r in rows:
        d = dict(r)
        d["expirado"] = d["expira_em"] < agora
        result.append(d)
    return result


# ================================================================
# DASHBOARD
# ================================================================

def dashboard_service(condominio_id: int) -> dict:
    cond = buscar_condominio(condominio_id)
    return {
        "condominio":            dict(cond) if cond else None,
        "total_pessoas":         contar_pessoas(condominio_id),
        "dentro_agora":          contar_dentro(condominio_id),
        "veiculos_dentro":       contar_veiculos_dentro(condominio_id),
        "entradas_hoje":         contar_entradas_hoje(condominio_id),
        "saidas_hoje":           contar_saidas_hoje(condominio_id),
        "ultimas_movimentacoes": [dict(r) for r in ultimas_movimentacoes(condominio_id, 10)],
    }


def dashboard_superadmin_service() -> dict:
    conds = listar_condominios()
    return {
        "total_condominios":    len(conds),
        "condominios_ativos":   sum(1 for c in conds if c["ativo"]),
        "condominios_inativos": sum(1 for c in conds if not c["ativo"]),
        "condominios":          [dict(c) for c in conds],
    }


# ================================================================
# RELATÓRIO
# ================================================================

def relatorio_por_dia_service(condominio_id: int, data_iso: str):
    data_iso = (data_iso or "").strip()
    if not data_iso:
        return False, "Data obrigatória.", []
    return True, "OK", [dict(r) for r in relatorio_por_data(condominio_id, data_iso)]


# ================================================================
# BACKUP
# ================================================================

def fazer_backup_service() -> tuple[bool, str, str | None]:
    try:
        backup_dir = DB_PATH.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"portaria_backup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_path)

        # Mantém só os últimos 7 backups
        backups = sorted(backup_dir.glob("portaria_backup_*.db"))
        for old in backups[:-7]:
            old.unlink()

        return True, "Backup realizado com sucesso.", str(backup_path.name)
    except Exception as e:
        return False, f"Erro ao fazer backup: {e}", None


def listar_backups_service() -> list:
    backup_dir = DB_PATH.parent / "backups"
    if not backup_dir.exists():
        return []
    backups = sorted(backup_dir.glob("portaria_backup_*.db"), reverse=True)
    return [{"nome": b.name, "tamanho_kb": round(b.stat().st_size / 1024, 1)} for b in backups]


# ================================================================
# USUÁRIOS
# ================================================================

def criar_usuario_service(
    condominio_id: int, usuario: str, senha: str, perfil: str,
    criado_por: str | None = None,
) -> tuple[bool, str]:
    usuario = (usuario or "").strip()
    senha   = (senha   or "").strip()

    if not usuario or not senha:
        return False, "Usuário e senha são obrigatórios."
    if perfil not in PERFIS_COND:
        return False, "Perfil inválido."
    if len(senha) < 4:
        return False, "Senha muito curta."
    if buscar_usuario(usuario):
        return False, "Usuário já existe."

    salt = os.urandom(16)
    inserir_usuario(condominio_id, usuario, _hash_senha(senha, salt),
                    binascii.hexlify(salt).decode("ascii"), perfil)
    if criado_por:
        registrar_log_admin(condominio_id, criado_por, "criacao_usuario", f"{usuario} ({perfil})")
    return True, "Usuário criado com sucesso."


def listar_usuarios_service(condominio_id: int):
    return [dict(r) for r in listar_usuarios_condominio(condominio_id)]


def editar_usuario_service(
    condominio_id: int, usuario: str, nova_senha: str | None,
    perfil: str | None, ativo: int | None,
    editado_por: str | None = None,
) -> tuple[bool, str]:
    row = buscar_usuario(usuario)
    if not row:
        return False, "Usuário não encontrado."
    if row["condominio_id"] != condominio_id:
        return False, "Sem permissão."
    if perfil and perfil not in PERFIS_COND:
        return False, "Perfil inválido."

    senha_hash = salt_hex = None
    if nova_senha and nova_senha.strip():
        salt = os.urandom(16)
        senha_hash = _hash_senha(nova_senha.strip(), salt)
        salt_hex   = binascii.hexlify(salt).decode("ascii")

    atualizar_usuario(usuario, senha_hash, salt_hex, perfil, ativo)
    if editado_por:
        registrar_log_admin(condominio_id, editado_por, "edicao_usuario", usuario)
    return True, "Usuário atualizado."


def remover_usuario_service(
    condominio_id: int, usuario: str, removido_por: str | None = None,
) -> tuple[bool, str]:
    row = buscar_usuario(usuario)
    if not row:
        return False, "Usuário não encontrado."
    if row["condominio_id"] != condominio_id:
        return False, "Sem permissão."

    todos = listar_usuarios_condominio(condominio_id)
    sindicos = [u for u in todos if u["perfil"] == "sindico" and u["ativo"] and u["usuario"] != usuario]
    if row["perfil"] == "sindico" and not sindicos:
        return False, "Não é possível remover o único síndico ativo."

    if removido_por:
        registrar_log_admin(condominio_id, removido_por, "remocao_usuario", usuario)
    remover_usuario(usuario)
    return True, "Usuário removido."


# ================================================================
# LOG
# ================================================================

def listar_log_service(condominio_id: int | None, limit: int = 50):
    return [dict(r) for r in listar_log_admin(condominio_id, limit)]


def listar_todos_usuarios_service():
    return [dict(r) for r in listar_todos_usuarios()]
