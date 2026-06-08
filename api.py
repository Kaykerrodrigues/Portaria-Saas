from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse

from database import criar_tabelas, DB_PATH
from models import (
    RegistroCondominio, CondominioUpdate,
    PessoaCreate, PessoaUpdate, EntradaRequest, SaidaRequest,
    UsuarioCreate, UsuarioUpdate, TrocarSenha,
    VeiculoCreate, VeiculoUpdate, EntradaVeiculoRequest, SaidaVeiculoRequest,
    QRCodeCreate, QRCodeValidar,
)
from services import (
    garantir_superadmin,
    autenticar_login_service, trocar_senha_service,
    registrar_condominio_service,
    listar_condominios_service, buscar_condominio_service, atualizar_condominio_service,
    inserir_pessoa_service, listar_pessoas_service, contar_pessoas_service,
    listar_por_tipo_service, listar_dentro_service,
    buscar_pessoa_service, buscar_por_nome_service,
    editar_pessoa_service, remover_pessoa_service,
    registrar_entrada_service, registrar_saida_service,
    cadastrar_veiculo_service, listar_veiculos_service, buscar_veiculo_service,
    listar_veiculos_dentro_service, editar_veiculo_service, remover_veiculo_service,
    entrada_veiculo_service, saida_veiculo_service, relatorio_veiculos_service,
    gerar_qrcode_service, validar_qrcode_service, listar_qrcodes_service,
    dashboard_service, dashboard_superadmin_service,
    relatorio_por_dia_service,
    fazer_backup_service, listar_backups_service,
    criar_usuario_service, listar_usuarios_service,
    editar_usuario_service, remover_usuario_service,
    listar_log_service, listar_todos_usuarios_service,
)

app = FastAPI(title="Portaria Pro API", version="3.0")
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    criar_tabelas()
    garantir_superadmin()


# ================================================================
# AUTH
# ================================================================

def get_user(credentials: HTTPBasicCredentials = Depends(security)) -> dict:
    ok, msg, user = autenticar_login_service(credentials.username, credentials.password)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg, headers={"WWW-Authenticate": "Basic"})
    return user


def require_superadmin(user: dict = Depends(get_user)) -> dict:
    if user["perfil"] != "superadmin":
        raise HTTPException(403, "Acesso exclusivo ao superadmin.")
    return user


def require_cond_user(user: dict = Depends(get_user)) -> dict:
    if user["perfil"] == "superadmin":
        raise HTTPException(403, "Use os endpoints /super/.")
    return user


def require_admin(user: dict = Depends(get_user)) -> dict:
    if user["perfil"] not in {"sindico", "admin", "superadmin"}:
        raise HTTPException(403, "Acesso restrito a admin ou síndico.")
    return user


def require_sindico(user: dict = Depends(get_user)) -> dict:
    if user["perfil"] not in {"sindico"}:
        raise HTTPException(403, "Acesso restrito ao síndico.")
    return user


# ================================================================
# HEALTH / LOGIN
# ================================================================

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0"}


@app.get("/login")
def login(user: dict = Depends(get_user)):
    extra = {}
    if user["condominio_id"]:
        cond = buscar_condominio_service(user["condominio_id"])
        extra["condominio"] = cond
    return {"usuario": user["usuario"], "perfil": user["perfil"],
            "condominio_id": user["condominio_id"], **extra}


@app.post("/trocar-senha")
def trocar_senha(payload: TrocarSenha, user: dict = Depends(get_user)):
    ok, msg = trocar_senha_service(user["usuario"], payload.senha_atual, payload.nova_senha)
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


# ================================================================
# REGISTRO PÚBLICO
# ================================================================

@app.post("/register", status_code=201)
def register(payload: RegistroCondominio):
    ok, msg = registrar_condominio_service(
        payload.nome_condominio, payload.endereco,
        payload.usuario_sindico, payload.senha_sindico,
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


# ================================================================
# SUPERADMIN
# ================================================================

@app.get("/super/dashboard")
def super_dashboard(user: dict = Depends(require_superadmin)):
    return dashboard_superadmin_service()


@app.get("/super/condominios")
def super_listar(user: dict = Depends(require_superadmin)):
    return listar_condominios_service()


@app.get("/super/condominios/{cond_id}")
def super_buscar(cond_id: int, user: dict = Depends(require_superadmin)):
    c = buscar_condominio_service(cond_id)
    if not c:
        raise HTTPException(404, "Não encontrado.")
    return c


@app.put("/super/condominios/{cond_id}")
def super_editar(cond_id: int, payload: CondominioUpdate, user: dict = Depends(require_superadmin)):
    ok, msg = atualizar_condominio_service(cond_id, payload.nome, payload.endereco, payload.ativo, user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.get("/super/usuarios")
def super_usuarios(user: dict = Depends(require_superadmin)):
    return listar_todos_usuarios_service()


@app.get("/super/log")
def super_log(limit: int = Query(100, ge=1, le=500), user: dict = Depends(require_superadmin)):
    return listar_log_service(None, limit)


@app.post("/super/backup")
def super_backup(user: dict = Depends(require_superadmin)):
    ok, msg, nome = fazer_backup_service()
    if not ok:
        raise HTTPException(500, msg)
    return {"message": msg, "arquivo": nome}


@app.get("/super/backups")
def super_listar_backups(user: dict = Depends(require_superadmin)):
    return listar_backups_service()


# ================================================================
# DASHBOARD
# ================================================================

@app.get("/dashboard")
def dashboard(user: dict = Depends(require_cond_user)):
    return dashboard_service(user["condominio_id"])


# ================================================================
# PESSOAS
# ================================================================

@app.get("/pessoas")
def listar_pessoas(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(require_cond_user),
):
    cid = user["condominio_id"]
    return {"total": contar_pessoas_service(cid), "limit": limit, "offset": offset,
            "data": listar_pessoas_service(cid, limit=limit, offset=offset)}


@app.get("/pessoas/busca")
def busca(nome: str = Query(..., min_length=1), user: dict = Depends(require_cond_user)):
    return buscar_por_nome_service(user["condominio_id"], nome)


@app.get("/pessoas/dentro")
def dentro(user: dict = Depends(require_cond_user)):
    return listar_dentro_service(user["condominio_id"])


@app.get("/pessoas/tipo/{tipo}")
def por_tipo(tipo: str, user: dict = Depends(require_cond_user)):
    ok, msg, lista = listar_por_tipo_service(user["condominio_id"], tipo)
    if not ok:
        raise HTTPException(400, msg)
    return lista


@app.get("/pessoas/{documento}")
def buscar_pessoa(documento: str, user: dict = Depends(require_cond_user)):
    p = buscar_pessoa_service(user["condominio_id"], documento)
    if not p:
        raise HTTPException(404, "Não encontrado.")
    return p


@app.post("/pessoas", status_code=201)
def criar_pessoa(payload: PessoaCreate, user: dict = Depends(require_admin)):
    ok, msg = inserir_pessoa_service(
        user["condominio_id"], payload.nome, payload.documento, payload.tipo,
        payload.quadra, payload.lote, payload.foto, usuario_acao=user["usuario"],
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.put("/pessoas/{documento}")
def editar_pessoa(documento: str, payload: PessoaUpdate, user: dict = Depends(require_admin)):
    ok, msg = editar_pessoa_service(
        user["condominio_id"], documento,
        payload.nome or "", payload.tipo or "",
        payload.quadra_lote, payload.foto, usuario_acao=user["usuario"],
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.delete("/pessoas/{documento}")
def deletar_pessoa(documento: str, user: dict = Depends(require_admin)):
    ok, msg = remover_pessoa_service(user["condominio_id"], documento, usuario_acao=user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


# ================================================================
# MOVIMENTAÇÃO
# ================================================================

@app.post("/entrada")
def entrada(payload: EntradaRequest, user: dict = Depends(require_cond_user)):
    ok, msg, pessoa = registrar_entrada_service(
        user["condominio_id"], payload.documento, payload.quadra, payload.lote, user["usuario"]
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg, "pessoa": pessoa}


@app.post("/saida")
def saida(payload: SaidaRequest, user: dict = Depends(require_cond_user)):
    ok, msg, pessoa = registrar_saida_service(user["condominio_id"], payload.documento, user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg, "pessoa": pessoa}


# ================================================================
# VEÍCULOS
# ================================================================

@app.get("/veiculos")
def listar_veiculos(user: dict = Depends(require_cond_user)):
    return listar_veiculos_service(user["condominio_id"])


@app.get("/veiculos/dentro")
def veiculos_dentro(user: dict = Depends(require_cond_user)):
    return listar_veiculos_dentro_service(user["condominio_id"])


@app.get("/veiculos/{placa}")
def buscar_veiculo(placa: str, user: dict = Depends(require_cond_user)):
    v = buscar_veiculo_service(user["condominio_id"], placa)
    if not v:
        raise HTTPException(404, "Veículo não encontrado.")
    return v


@app.post("/veiculos", status_code=201)
def cadastrar_veiculo(payload: VeiculoCreate, user: dict = Depends(require_admin)):
    ok, msg = cadastrar_veiculo_service(
        user["condominio_id"], payload.placa, payload.modelo, payload.cor,
        payload.empresa, payload.pessoa_documento, usuario_acao=user["usuario"],
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.put("/veiculos/{placa}")
def editar_veiculo(placa: str, payload: VeiculoUpdate, user: dict = Depends(require_admin)):
    ok, msg = editar_veiculo_service(
        user["condominio_id"], placa, payload.modelo, payload.cor,
        payload.empresa, payload.pessoa_documento, usuario_acao=user["usuario"],
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.delete("/veiculos/{placa}")
def deletar_veiculo(placa: str, user: dict = Depends(require_admin)):
    ok, msg = remover_veiculo_service(user["condominio_id"], placa, usuario_acao=user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.post("/veiculos/entrada")
def entrada_veiculo(payload: EntradaVeiculoRequest, user: dict = Depends(require_cond_user)):
    ok, msg, v = entrada_veiculo_service(user["condominio_id"], payload.placa, payload.destino, user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg, "veiculo": v}


@app.post("/veiculos/saida")
def saida_veiculo(payload: SaidaVeiculoRequest, user: dict = Depends(require_cond_user)):
    ok, msg, v = saida_veiculo_service(user["condominio_id"], payload.placa, user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg, "veiculo": v}


@app.get("/veiculos/relatorio")
def relatorio_veiculo(
    data: str = Query(..., description="AAAA-MM-DD"),
    user: dict = Depends(require_cond_user),
):
    ok, msg, eventos = relatorio_veiculos_service(user["condominio_id"], data)
    if not ok:
        raise HTTPException(400, msg)
    return eventos


# ================================================================
# QR CODE
# ================================================================

@app.get("/qrcodes")
def listar_qr(user: dict = Depends(require_cond_user)):
    return listar_qrcodes_service(user["condominio_id"])


@app.post("/qrcodes", status_code=201)
def gerar_qr(payload: QRCodeCreate, user: dict = Depends(require_cond_user)):
    ok, msg, token = gerar_qrcode_service(
        user["condominio_id"], payload.nome_visitante, payload.documento_visitante,
        payload.destino, user["usuario"], payload.horas_validade,
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg, "token": token}


@app.post("/qrcodes/validar")
def validar_qr(payload: QRCodeValidar, user: dict = Depends(require_cond_user)):
    ok, msg, dados = validar_qrcode_service(payload.token, user["usuario"], user["condominio_id"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg, "dados": dados}


# ================================================================
# RELATÓRIO
# ================================================================

@app.get("/relatorio")
def relatorio(data: str = Query(...), user: dict = Depends(require_cond_user)):
    ok, msg, eventos = relatorio_por_dia_service(user["condominio_id"], data)
    if not ok:
        raise HTTPException(400, msg)
    return eventos


# ================================================================
# BACKUP (síndico)
# ================================================================

@app.post("/backup")
def backup(user: dict = Depends(require_sindico)):
    ok, msg, nome = fazer_backup_service()
    if not ok:
        raise HTTPException(500, msg)
    return {"message": msg, "arquivo": nome}


@app.get("/backups")
def listar_backups(user: dict = Depends(require_sindico)):
    return listar_backups_service()


# ================================================================
# USUÁRIOS
# ================================================================

@app.get("/usuarios")
def listar_usuarios(user: dict = Depends(require_sindico)):
    return listar_usuarios_service(user["condominio_id"])


@app.post("/usuarios", status_code=201)
def criar_usuario(payload: UsuarioCreate, user: dict = Depends(require_sindico)):
    ok, msg = criar_usuario_service(
        user["condominio_id"], payload.usuario, payload.senha, payload.perfil,
        criado_por=user["usuario"],
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.put("/usuarios/{usuario}")
def editar_usuario(usuario: str, payload: UsuarioUpdate, user: dict = Depends(require_sindico)):
    ok, msg = editar_usuario_service(
        user["condominio_id"], usuario, payload.nova_senha, payload.perfil, payload.ativo,
        editado_por=user["usuario"],
    )
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.delete("/usuarios/{usuario}")
def deletar_usuario(usuario: str, user: dict = Depends(require_sindico)):
    ok, msg = remover_usuario_service(user["condominio_id"], usuario, removido_por=user["usuario"])
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


# ================================================================
# LOG
# ================================================================

@app.get("/log-admin")
def log_admin(limit: int = Query(50, ge=1, le=200), user: dict = Depends(require_sindico)):
    return listar_log_service(user["condominio_id"], limit)
