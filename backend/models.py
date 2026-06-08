from pydantic import BaseModel, Field


class RegistroCondominio(BaseModel):
    nome_condominio:  str = Field(min_length=2)
    endereco:         str | None = None
    usuario_sindico:  str = Field(min_length=3)
    senha_sindico:    str = Field(min_length=4)


class CondominioUpdate(BaseModel):
    nome:     str = Field(min_length=2)
    endereco: str | None = None
    ativo:    int = 1


class PessoaCreate(BaseModel):
    nome:      str = Field(min_length=1)
    documento: str = Field(min_length=1)
    tipo:      str = Field(min_length=1)
    quadra:    str | None = None
    lote:      str | None = None
    foto:      str | None = None


class PessoaUpdate(BaseModel):
    nome:        str | None = None
    tipo:        str | None = None
    quadra_lote: str | None = None
    foto:        str | None = None


class EntradaRequest(BaseModel):
    documento: str = Field(min_length=1)
    quadra:    str | None = None
    lote:      str | None = None


class SaidaRequest(BaseModel):
    documento: str = Field(min_length=1)


class UsuarioCreate(BaseModel):
    usuario: str = Field(min_length=3)
    senha:   str = Field(min_length=4)
    perfil:  str = "porteiro"


class UsuarioUpdate(BaseModel):
    nova_senha: str | None = None
    perfil:     str | None = None
    ativo:      int | None = None


class TrocarSenha(BaseModel):
    senha_atual: str = Field(min_length=1)
    nova_senha:  str = Field(min_length=4)


class VeiculoCreate(BaseModel):
    placa:            str = Field(min_length=1)
    modelo:           str | None = None
    cor:              str | None = None
    empresa:          str | None = None
    pessoa_documento: str | None = None


class VeiculoUpdate(BaseModel):
    modelo:           str | None = None
    cor:              str | None = None
    empresa:          str | None = None
    pessoa_documento: str | None = None


class EntradaVeiculoRequest(BaseModel):
    placa:   str = Field(min_length=1)
    destino: str | None = None


class SaidaVeiculoRequest(BaseModel):
    placa: str = Field(min_length=1)


class QRCodeCreate(BaseModel):
    nome_visitante:      str = Field(min_length=1)
    documento_visitante: str | None = None
    destino:             str | None = None
    horas_validade:      int = 24


class QRCodeValidar(BaseModel):
    token: str = Field(min_length=1)
