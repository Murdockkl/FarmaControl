"""Preferências do usuário guardadas no próprio banco (tabela `configuracoes`)."""
from __future__ import annotations

from ..banco import Banco
from ..config import DIAS_ALERTA_MAXIMO, DIAS_ALERTA_PADRAO
from ..dominio import ValidacaoError

_DIAS_ALERTA = "dias_alerta_vencimento"
_NOME_FARMACIA = "nome_farmacia"


class ConfiguracaoService:
    def __init__(self, db: Banco):
        self.db = db

    def obter(self, chave: str, padrao: str = "") -> str:
        linha = self.db.conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
        return linha["valor"] if linha else padrao

    def definir(self, chave: str, valor: str) -> None:
        with self.db.transacao():
            self.db.conn.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
                "ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor",
                (chave, str(valor)))

    # ------------------------------------------------------- dias de alerta
    @property
    def dias_alerta(self) -> int:
        try:
            dias = int(self.obter(_DIAS_ALERTA, str(DIAS_ALERTA_PADRAO)))
        except ValueError:
            return DIAS_ALERTA_PADRAO
        return dias if 1 <= dias <= DIAS_ALERTA_MAXIMO else DIAS_ALERTA_PADRAO

    def definir_dias_alerta(self, texto: str) -> int:
        t = str(texto).strip()
        if not t.isdigit() or not 1 <= int(t) <= DIAS_ALERTA_MAXIMO:
            raise ValidacaoError(
                f"Informe um número inteiro de dias entre 1 e {DIAS_ALERTA_MAXIMO}.")
        self.definir(_DIAS_ALERTA, t)
        return int(t)

    # -------------------------------------------------------- nome da farmácia
    @property
    def nome_farmacia(self) -> str:
        return self.obter(_NOME_FARMACIA, "")

    def definir_nome_farmacia(self, nome: str) -> str:
        nome = " ".join((nome or "").split())
        if len(nome) > 60:
            raise ValidacaoError("O nome da farmácia pode ter no máximo 60 caracteres.")
        self.definir(_NOME_FARMACIA, nome)
        return nome
