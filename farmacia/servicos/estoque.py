"""Entradas e saídas de estoque. Toda alteração de quantidade passa por aqui."""
from __future__ import annotations

from datetime import date, datetime

from ..banco import Banco
from ..dominio import (ENTRADA, SAIDA, TIPOS_MOVIMENTACAO, EstoqueInsuficienteError,
                       Movimentacao, NaoEncontradoError, ValidacaoError)
from ..config import LIMITE_QUANTIDADE
from ..texto import limpar_espacos, normalizar, padrao_like, rotulo_medicamento, unidades

_FORMATO_DATA_HORA = "%Y-%m-%d %H:%M:%S"


class EstoqueService:
    def __init__(self, db: Banco):
        self.db = db

    # --------------------------------------------------------------- registrar
    def registrar_movimentacao(self, medicamento_id: int, tipo: str, quantidade: int,
                               motivo: str, observacao: str = "",
                               data_hora: datetime | None = None) -> Movimentacao:
        """Soma (ENTRADA) ou subtrai (SAIDA) do estoque e grava a movimentação.

        A atualização do estoque e o registro no histórico acontecem na mesma
        transação: ou os dois são gravados, ou nenhum.
        Levanta EstoqueInsuficienteError se a saída for maior que o estoque.
        """
        if tipo not in TIPOS_MOVIMENTACAO:
            raise ValidacaoError("Tipo de movimentação inválido.")
        if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade <= 0:
            raise ValidacaoError({"quantidade": "A quantidade deve ser um número inteiro maior que zero."})
        if quantidade > LIMITE_QUANTIDADE:
            raise ValidacaoError({"quantidade": "Quantidade muito alta. Confira o número digitado."})
        motivo = limpar_espacos(motivo)
        if not motivo:
            raise ValidacaoError({"motivo": "Informe o motivo da movimentação."})
        observacao = limpar_espacos(observacao)
        quando = (data_hora or datetime.now()).replace(microsecond=0)

        with self.db.transacao() as conn:
            med = conn.execute(
                "SELECT nome, dosagem, unidade_medida, quantidade_atual "
                "FROM medicamentos WHERE id = ? AND ativo = 1", (medicamento_id,)).fetchone()
            if med is None:
                raise NaoEncontradoError("Medicamento não encontrado. Ele pode ter sido excluído.")
            anterior = med["quantidade_atual"]
            if tipo == SAIDA:
                if quantidade > anterior:
                    raise EstoqueInsuficienteError(
                        f"Estoque insuficiente: você tentou retirar {unidades(quantidade)}, "
                        f"mas há apenas {unidades(anterior)} em estoque.")
                posterior = anterior - quantidade
            else:
                posterior = anterior + quantidade
                if posterior > LIMITE_QUANTIDADE:
                    raise ValidacaoError({"quantidade": "O estoque total ficaria alto demais. "
                                                        "Confira a quantidade digitada."})
            rotulo = rotulo_medicamento(med["nome"], med["dosagem"], med["unidade_medida"])
            conn.execute(
                "UPDATE medicamentos SET quantidade_atual = ?, atualizado_em = ? WHERE id = ?",
                (posterior, quando.strftime(_FORMATO_DATA_HORA), medicamento_id))
            cursor = conn.execute(
                "INSERT INTO movimentacoes (medicamento_id, medicamento_nome, tipo, quantidade, "
                "estoque_anterior, estoque_posterior, motivo, observacao, data_hora) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (medicamento_id, rotulo, tipo, quantidade, anterior, posterior, motivo,
                 observacao, quando.strftime(_FORMATO_DATA_HORA)))
            movimento_id = cursor.lastrowid
        return Movimentacao(id=movimento_id, medicamento_id=medicamento_id, medicamento=rotulo,
                            excluido=False, tipo=tipo, quantidade=quantidade,
                            estoque_anterior=anterior, estoque_posterior=posterior,
                            motivo=motivo, observacao=observacao, data_hora=quando)

    def entrada(self, medicamento_id: int, quantidade: int, motivo: str = "Compra",
                observacao: str = "") -> Movimentacao:
        return self.registrar_movimentacao(medicamento_id, ENTRADA, quantidade, motivo, observacao)

    def saida(self, medicamento_id: int, quantidade: int, motivo: str = "Venda",
              observacao: str = "") -> Movimentacao:
        return self.registrar_movimentacao(medicamento_id, SAIDA, quantidade, motivo, observacao)

    # ---------------------------------------------------------------- consultas
    def listar(self, *, data_inicio: date | None = None, data_fim: date | None = None,
               medicamento_id: int | None = None, texto: str = "", tipo: str | None = None,
               limite: int | None = None) -> list[Movimentacao]:
        """Movimentações, da mais recente para a mais antiga, com filtros opcionais.

        `texto` procura no nome do medicamento (sem diferenciar acentos/maiúsculas).
        """
        where, params = ["1 = 1"], []
        if data_inicio:
            where.append("mv.data_hora >= ?")
            params.append(f"{data_inicio.isoformat()} 00:00:00")
        if data_fim:
            where.append("mv.data_hora <= ?")
            params.append(f"{data_fim.isoformat()} 23:59:59")
        if medicamento_id:
            where.append("mv.medicamento_id = ?")
            params.append(medicamento_id)
        if tipo in TIPOS_MOVIMENTACAO:
            where.append("mv.tipo = ?")
            params.append(tipo)
        busca = normalizar(texto)
        if busca:
            where.append("(norm(mv.medicamento_nome) LIKE ? ESCAPE '\\' "
                         "OR norm(m.nome) LIKE ? ESCAPE '\\' "
                         "OR norm(m.principio_ativo) LIKE ? ESCAPE '\\')")
            params += [padrao_like(busca)] * 3
        sql = (
            "SELECT mv.*, m.ativo AS med_ativo, m.nome AS med_nome, m.dosagem AS med_dosagem, "
            "       m.unidade_medida AS med_unidade "
            "FROM movimentacoes mv JOIN medicamentos m ON m.id = mv.medicamento_id "
            f"WHERE {' AND '.join(where)} ORDER BY mv.data_hora DESC, mv.id DESC")
        if limite:
            sql += f" LIMIT {int(limite)}"
        return [self._para_movimentacao(r) for r in self.db.conn.execute(sql, params)]

    def ultimas(self, limite: int = 8) -> list[Movimentacao]:
        return self.listar(limite=limite)

    @staticmethod
    def _para_movimentacao(r) -> Movimentacao:
        ativo = bool(r["med_ativo"])
        nome = (rotulo_medicamento(r["med_nome"], r["med_dosagem"], r["med_unidade"])
                if ativo else r["medicamento_nome"])
        return Movimentacao(
            id=r["id"], medicamento_id=r["medicamento_id"], medicamento=nome, excluido=not ativo,
            tipo=r["tipo"], quantidade=r["quantidade"], estoque_anterior=r["estoque_anterior"],
            estoque_posterior=r["estoque_posterior"], motivo=r["motivo"], observacao=r["observacao"],
            data_hora=datetime.strptime(r["data_hora"], _FORMATO_DATA_HORA))
