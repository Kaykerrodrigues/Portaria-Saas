import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).with_name("portaria.db")


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def executar(sql: str, params: tuple = ()):
    with conectar() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur


def criar_tabelas() -> None:

    # Condomínios
    executar("""
        CREATE TABLE IF NOT EXISTS condominios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT NOT NULL,
            endereco   TEXT,
            slug       TEXT NOT NULL UNIQUE,
            ativo      INTEGER NOT NULL DEFAULT 1,
            criado_em  TEXT NOT NULL
        );
    """)

    # Pessoas
    executar("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER NOT NULL,
            nome          TEXT NOT NULL,
            documento     TEXT NOT NULL,
            tipo          TEXT NOT NULL,
            quadra_lote   TEXT,
            status        TEXT NOT NULL DEFAULT 'FORA',
            foto          TEXT,
            UNIQUE(condominio_id, documento),
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # Histórico de movimentações
    executar("""
        CREATE TABLE IF NOT EXISTS historico (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER NOT NULL,
            documento     TEXT NOT NULL,
            acao          TEXT NOT NULL,
            data_hora     TEXT NOT NULL,
            destino       TEXT,
            porteiro      TEXT,
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # Autorizações de acesso
    executar("""
        CREATE TABLE IF NOT EXISTS autorizacoes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER NOT NULL,
            documento     TEXT NOT NULL,
            destino       TEXT NOT NULL,
            ativo         INTEGER NOT NULL DEFAULT 1,
            autorizado_por TEXT,
            data_hora     TEXT NOT NULL,
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # Usuários (porteiros, admins, síndicos, superadmin)
    executar("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER,
            usuario       TEXT NOT NULL UNIQUE,
            senha_hash    TEXT NOT NULL,
            salt          TEXT NOT NULL,
            perfil        TEXT NOT NULL DEFAULT 'porteiro',
            ativo         INTEGER NOT NULL DEFAULT 1,
            criado_em     TEXT NOT NULL,
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # Log de ações administrativas
    executar("""
        CREATE TABLE IF NOT EXISTS log_admin (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER,
            usuario       TEXT NOT NULL,
            acao          TEXT NOT NULL,
            detalhe       TEXT,
            data_hora     TEXT NOT NULL
        );
    """)

    # Veículos
    executar("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER NOT NULL,
            placa         TEXT NOT NULL,
            modelo        TEXT,
            cor           TEXT,
            empresa       TEXT,
            pessoa_documento TEXT,
            status        TEXT NOT NULL DEFAULT 'FORA',
            criado_em     TEXT NOT NULL,
            UNIQUE(condominio_id, placa),
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # Histórico de veículos
    executar("""
        CREATE TABLE IF NOT EXISTS historico_veiculos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER NOT NULL,
            placa         TEXT NOT NULL,
            acao          TEXT NOT NULL,
            data_hora     TEXT NOT NULL,
            destino       TEXT,
            porteiro      TEXT,
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # QR Codes de visitantes
    executar("""
        CREATE TABLE IF NOT EXISTS qrcodes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            condominio_id INTEGER NOT NULL,
            token         TEXT NOT NULL UNIQUE,
            nome_visitante TEXT NOT NULL,
            documento_visitante TEXT,
            destino       TEXT,
            criado_por    TEXT NOT NULL,
            usado         INTEGER NOT NULL DEFAULT 0,
            expira_em     TEXT NOT NULL,
            criado_em     TEXT NOT NULL,
            FOREIGN KEY(condominio_id) REFERENCES condominios(id)
        );
    """)

    # Índices
    executar("CREATE INDEX IF NOT EXISTS idx_pessoas_cond        ON pessoas(condominio_id);")
    executar("CREATE INDEX IF NOT EXISTS idx_pessoas_status      ON pessoas(condominio_id, status);")
    executar("CREATE INDEX IF NOT EXISTS idx_pessoas_tipo        ON pessoas(condominio_id, tipo);")
    executar("CREATE INDEX IF NOT EXISTS idx_hist_cond_data      ON historico(condominio_id, data_hora);")
    executar("CREATE INDEX IF NOT EXISTS idx_aut_cond            ON autorizacoes(condominio_id, documento, ativo);")
    executar("CREATE INDEX IF NOT EXISTS idx_usuarios_usuario    ON usuarios(usuario);")
    executar("CREATE INDEX IF NOT EXISTS idx_usuarios_cond       ON usuarios(condominio_id);")
    executar("CREATE INDEX IF NOT EXISTS idx_log_cond            ON log_admin(condominio_id, data_hora);")
    executar("CREATE INDEX IF NOT EXISTS idx_veic_cond           ON veiculos(condominio_id);")
    executar("CREATE INDEX IF NOT EXISTS idx_veic_placa          ON veiculos(condominio_id, placa);")
    executar("CREATE INDEX IF NOT EXISTS idx_qr_token            ON qrcodes(token);")
    executar("CREATE INDEX IF NOT EXISTS idx_qr_cond             ON qrcodes(condominio_id);")


# ================================================================
# CONDOMÍNIOS
# ================================================================

def inserir_condominio(nome: str, endereco: str | None, slug: str) -> int:
    criado_em = datetime.now().isoformat(timespec="seconds")
    cur = executar("""
        INSERT INTO condominios (nome, endereco, slug, ativo, criado_em)
        VALUES (?, ?, ?, 1, ?)
    """, (nome, endereco, slug, criado_em))
    return cur.lastrowid


def listar_condominios():
    cur = executar("SELECT * FROM condominios ORDER BY criado_em DESC")
    return cur.fetchall()


def buscar_condominio(condominio_id: int):
    cur = executar("SELECT * FROM condominios WHERE id = ? LIMIT 1", (condominio_id,))
    return cur.fetchone()


def buscar_condominio_por_slug(slug: str):
    cur = executar("SELECT * FROM condominios WHERE slug = ? LIMIT 1", (slug,))
    return cur.fetchone()


def atualizar_condominio(condominio_id: int, nome: str, endereco: str | None, ativo: int) -> None:
    executar("""
        UPDATE condominios SET nome = ?, endereco = ?, ativo = ? WHERE id = ?
    """, (nome, endereco, ativo, condominio_id))


def contar_condominios() -> int:
    cur = executar("SELECT COUNT(*) AS total FROM condominios")
    return int(cur.fetchone()["total"])


# ================================================================
# PESSOAS
# ================================================================

def inserir_pessoa(condominio_id: int, nome: str, documento: str, tipo: str,
                   quadra_lote: str | None, foto: str | None = None) -> None:
    executar("""
        INSERT INTO pessoas (condominio_id, nome, documento, tipo, quadra_lote, foto)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (condominio_id, nome, documento, tipo, quadra_lote, foto))


def listar_pessoas(condominio_id: int, limit: int | None = None, offset: int | None = None):
    sql = "SELECT * FROM pessoas WHERE condominio_id = ? ORDER BY nome ASC"
    params: list = [condominio_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))
        if offset is not None:
            sql += " OFFSET ?"
            params.append(int(offset))
    return executar(sql, tuple(params)).fetchall()


def contar_pessoas(condominio_id: int) -> int:
    cur = executar("SELECT COUNT(*) AS total FROM pessoas WHERE condominio_id = ?", (condominio_id,))
    return int(cur.fetchone()["total"])


def listar_pessoas_por_tipo(condominio_id: int, tipo: str):
    cur = executar("""
        SELECT * FROM pessoas WHERE condominio_id = ? AND tipo = ? ORDER BY nome ASC
    """, (condominio_id, tipo))
    return cur.fetchall()


def listar_dentro(condominio_id: int):
    cur = executar("""
        SELECT * FROM pessoas WHERE condominio_id = ? AND status = 'DENTRO' ORDER BY nome ASC
    """, (condominio_id,))
    return cur.fetchall()


def contar_dentro(condominio_id: int) -> int:
    cur = executar("""
        SELECT COUNT(*) AS total FROM pessoas WHERE condominio_id = ? AND status = 'DENTRO'
    """, (condominio_id,))
    return int(cur.fetchone()["total"])


def buscar_pessoa(condominio_id: int, documento: str):
    cur = executar("""
        SELECT * FROM pessoas WHERE condominio_id = ? AND documento = ? LIMIT 1
    """, (condominio_id, documento))
    return cur.fetchone()


def buscar_pessoas_por_nome(condominio_id: int, nome: str, limit: int = 10):
    cur = executar("""
        SELECT * FROM pessoas WHERE condominio_id = ? AND nome LIKE ? ORDER BY nome ASC LIMIT ?
    """, (condominio_id, f"%{nome}%", limit))
    return cur.fetchall()


def editar_pessoa(condominio_id: int, documento: str, nome: str, tipo: str,
                  quadra_lote: str | None, foto: str | None = None) -> None:
    if foto is not None:
        executar("""
            UPDATE pessoas SET nome=?, tipo=?, quadra_lote=?, foto=?
            WHERE condominio_id=? AND documento=?
        """, (nome, tipo, quadra_lote, foto, condominio_id, documento))
    else:
        executar("""
            UPDATE pessoas SET nome=?, tipo=?, quadra_lote=?
            WHERE condominio_id=? AND documento=?
        """, (nome, tipo, quadra_lote, condominio_id, documento))


def remover_pessoa(condominio_id: int, documento: str) -> None:
    executar("DELETE FROM pessoas WHERE condominio_id=? AND documento=?", (condominio_id, documento))


def atualizar_status(condominio_id: int, documento: str, status: str) -> None:
    executar("UPDATE pessoas SET status=? WHERE condominio_id=? AND documento=?",
             (status, condominio_id, documento))


# ================================================================
# HISTÓRICO
# ================================================================

def registrar_historico(condominio_id: int, documento: str, acao: str,
                         destino: str | None, porteiro: str) -> None:
    data_hora = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO historico (condominio_id, documento, acao, data_hora, destino, porteiro)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (condominio_id, documento, acao, data_hora, destino, porteiro))


def relatorio_por_data(condominio_id: int, data_iso: str):
    cur = executar("""
        SELECT h.data_hora, h.acao, p.nome, p.documento, p.tipo, h.porteiro, h.destino
        FROM historico h
        JOIN pessoas p ON p.documento = h.documento AND p.condominio_id = h.condominio_id
        WHERE h.condominio_id = ? AND h.data_hora LIKE ?
        ORDER BY h.data_hora
    """, (condominio_id, f"{data_iso}%"))
    return cur.fetchall()


def contar_entradas_hoje(condominio_id: int) -> int:
    hoje = datetime.now().strftime("%Y-%m-%d")
    cur = executar("""
        SELECT COUNT(*) AS total FROM historico
        WHERE condominio_id=? AND acao='entrada' AND data_hora LIKE ?
    """, (condominio_id, f"{hoje}%"))
    return int(cur.fetchone()["total"])


def contar_saidas_hoje(condominio_id: int) -> int:
    hoje = datetime.now().strftime("%Y-%m-%d")
    cur = executar("""
        SELECT COUNT(*) AS total FROM historico
        WHERE condominio_id=? AND acao='saida' AND data_hora LIKE ?
    """, (condominio_id, f"{hoje}%"))
    return int(cur.fetchone()["total"])


def ultimas_movimentacoes(condominio_id: int, limit: int = 10):
    cur = executar("""
        SELECT h.data_hora, h.acao, p.nome, p.documento, p.tipo, h.porteiro, h.destino
        FROM historico h
        JOIN pessoas p ON p.documento = h.documento AND p.condominio_id = h.condominio_id
        WHERE h.condominio_id = ?
        ORDER BY h.id DESC LIMIT ?
    """, (condominio_id, limit))
    return cur.fetchall()


# ================================================================
# AUTORIZAÇÕES
# ================================================================

def autorizar_documento(condominio_id: int, documento: str, destino: str, autorizado_por: str) -> None:
    data_hora = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO autorizacoes (condominio_id, documento, destino, ativo, autorizado_por, data_hora)
        VALUES (?, ?, ?, 1, ?, ?)
    """, (condominio_id, documento, destino, autorizado_por, data_hora))


def revogar_documento(condominio_id: int, documento: str, destino: str) -> None:
    executar("""
        UPDATE autorizacoes SET ativo=0
        WHERE condominio_id=? AND documento=? AND destino=? AND ativo=1
    """, (condominio_id, documento, destino))


def esta_autorizado(condominio_id: int, documento: str, destino: str) -> bool:
    cur = executar("""
        SELECT 1 FROM autorizacoes
        WHERE condominio_id=? AND documento=? AND destino=? AND ativo=1
        LIMIT 1
    """, (condominio_id, documento, destino))
    return cur.fetchone() is not None


# ================================================================
# USUÁRIOS
# ================================================================

def contar_superadmins() -> int:
    cur = executar("SELECT COUNT(*) AS total FROM usuarios WHERE perfil='superadmin'")
    return int(cur.fetchone()["total"])


def contar_usuarios_condominio(condominio_id: int) -> int:
    cur = executar("SELECT COUNT(*) AS total FROM usuarios WHERE condominio_id=?", (condominio_id,))
    return int(cur.fetchone()["total"])


def inserir_usuario(condominio_id: int | None, usuario: str, senha_hash: str,
                    salt: str, perfil: str = "porteiro") -> None:
    criado_em = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO usuarios (condominio_id, usuario, senha_hash, salt, perfil, ativo, criado_em)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (condominio_id, usuario, senha_hash, salt, perfil, criado_em))


def buscar_usuario(usuario: str):
    cur = executar("""
        SELECT id, condominio_id, usuario, senha_hash, salt, perfil, ativo
        FROM usuarios WHERE usuario=? LIMIT 1
    """, (usuario,))
    return cur.fetchone()


def listar_usuarios_condominio(condominio_id: int):
    cur = executar("""
        SELECT id, usuario, perfil, ativo, criado_em
        FROM usuarios WHERE condominio_id=? ORDER BY criado_em
    """, (condominio_id,))
    return cur.fetchall()


def listar_todos_usuarios():
    cur = executar("""
        SELECT u.id, u.usuario, u.perfil, u.ativo, u.criado_em,
               c.nome AS condominio_nome, u.condominio_id
        FROM usuarios u
        LEFT JOIN condominios c ON c.id = u.condominio_id
        ORDER BY u.id
    """)
    return cur.fetchall()


def atualizar_usuario(usuario: str, senha_hash: str | None, salt: str | None,
                      perfil: str | None, ativo: int | None) -> None:
    campos, params = [], []
    if senha_hash is not None:
        campos.append("senha_hash=?"); params.append(senha_hash)
    if salt is not None:
        campos.append("salt=?"); params.append(salt)
    if perfil is not None:
        campos.append("perfil=?"); params.append(perfil)
    if ativo is not None:
        campos.append("ativo=?"); params.append(ativo)
    if not campos:
        return
    params.append(usuario)
    executar(f"UPDATE usuarios SET {', '.join(campos)} WHERE usuario=?", tuple(params))


def remover_usuario(usuario: str) -> None:
    executar("DELETE FROM usuarios WHERE usuario=?", (usuario,))


# ================================================================
# LOG ADMIN
# ================================================================

def registrar_log_admin(condominio_id: int | None, usuario: str,
                         acao: str, detalhe: str | None = None) -> None:
    data_hora = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO log_admin (condominio_id, usuario, acao, detalhe, data_hora)
        VALUES (?, ?, ?, ?, ?)
    """, (condominio_id, usuario, acao, detalhe, data_hora))


def listar_log_admin(condominio_id: int | None, limit: int = 50):
    if condominio_id:
        cur = executar("""
            SELECT * FROM log_admin WHERE condominio_id=? ORDER BY id DESC LIMIT ?
        """, (condominio_id, limit))
    else:
        cur = executar("SELECT * FROM log_admin ORDER BY id DESC LIMIT ?", (limit,))
    return cur.fetchall()


# ================================================================
# VEÍCULOS
# ================================================================

def inserir_veiculo(condominio_id: int, placa: str, modelo: str | None,
                    cor: str | None, empresa: str | None,
                    pessoa_documento: str | None) -> None:
    criado_em = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO veiculos (condominio_id, placa, modelo, cor, empresa, pessoa_documento, status, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, 'FORA', ?)
    """, (condominio_id, placa.upper(), modelo, cor, empresa, pessoa_documento, criado_em))


def listar_veiculos(condominio_id: int):
    cur = executar("""
        SELECT v.*, p.nome as pessoa_nome
        FROM veiculos v
        LEFT JOIN pessoas p ON p.documento = v.pessoa_documento AND p.condominio_id = v.condominio_id
        WHERE v.condominio_id = ? ORDER BY v.placa ASC
    """, (condominio_id,))
    return cur.fetchall()


def buscar_veiculo(condominio_id: int, placa: str):
    cur = executar("""
        SELECT v.*, p.nome as pessoa_nome
        FROM veiculos v
        LEFT JOIN pessoas p ON p.documento = v.pessoa_documento AND p.condominio_id = v.condominio_id
        WHERE v.condominio_id = ? AND v.placa = ? LIMIT 1
    """, (condominio_id, placa.upper()))
    return cur.fetchone()


def listar_veiculos_dentro(condominio_id: int):
    cur = executar("""
        SELECT v.*, p.nome as pessoa_nome
        FROM veiculos v
        LEFT JOIN pessoas p ON p.documento = v.pessoa_documento AND p.condominio_id = v.condominio_id
        WHERE v.condominio_id = ? AND v.status = 'DENTRO' ORDER BY v.placa ASC
    """, (condominio_id,))
    return cur.fetchall()


def atualizar_status_veiculo(condominio_id: int, placa: str, status: str) -> None:
    executar("UPDATE veiculos SET status=? WHERE condominio_id=? AND placa=?",
             (status, condominio_id, placa.upper()))


def editar_veiculo(condominio_id: int, placa: str, modelo: str | None,
                   cor: str | None, empresa: str | None,
                   pessoa_documento: str | None) -> None:
    executar("""
        UPDATE veiculos SET modelo=?, cor=?, empresa=?, pessoa_documento=?
        WHERE condominio_id=? AND placa=?
    """, (modelo, cor, empresa, pessoa_documento, condominio_id, placa.upper()))


def remover_veiculo(condominio_id: int, placa: str) -> None:
    executar("DELETE FROM veiculos WHERE condominio_id=? AND placa=?",
             (condominio_id, placa.upper()))


def registrar_historico_veiculo(condominio_id: int, placa: str, acao: str,
                                 destino: str | None, porteiro: str) -> None:
    data_hora = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO historico_veiculos (condominio_id, placa, acao, data_hora, destino, porteiro)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (condominio_id, placa.upper(), acao, data_hora, destino, porteiro))


def relatorio_veiculos_por_data(condominio_id: int, data_iso: str):
    cur = executar("""
        SELECT h.data_hora, h.acao, h.placa, v.modelo, v.cor, v.empresa,
               h.porteiro, h.destino
        FROM historico_veiculos h
        LEFT JOIN veiculos v ON v.placa = h.placa AND v.condominio_id = h.condominio_id
        WHERE h.condominio_id = ? AND h.data_hora LIKE ?
        ORDER BY h.data_hora
    """, (condominio_id, f"{data_iso}%"))
    return cur.fetchall()


def contar_veiculos_dentro(condominio_id: int) -> int:
    cur = executar("SELECT COUNT(*) AS total FROM veiculos WHERE condominio_id=? AND status='DENTRO'",
                   (condominio_id,))
    return int(cur.fetchone()["total"])


# ================================================================
# QR CODE
# ================================================================

def inserir_qrcode(condominio_id: int, token: str, nome_visitante: str,
                   documento_visitante: str | None, destino: str | None,
                   criado_por: str, expira_em: str) -> None:
    criado_em = datetime.now().isoformat(timespec="seconds")
    executar("""
        INSERT INTO qrcodes (condominio_id, token, nome_visitante, documento_visitante,
                             destino, criado_por, usado, expira_em, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
    """, (condominio_id, token, nome_visitante, documento_visitante,
          destino, criado_por, expira_em, criado_em))


def buscar_qrcode(token: str):
    cur = executar("SELECT * FROM qrcodes WHERE token=? LIMIT 1", (token,))
    return cur.fetchone()


def listar_qrcodes(condominio_id: int):
    cur = executar("""
        SELECT * FROM qrcodes WHERE condominio_id=? ORDER BY id DESC
    """, (condominio_id,))
    return cur.fetchall()


def marcar_qrcode_usado(token: str) -> None:
    executar("UPDATE qrcodes SET usado=1 WHERE token=?", (token,))
