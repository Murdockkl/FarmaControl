"""Resumo do dashboard e montagem dos relatórios (dados prontos para tela e exportação)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from ..banco import Banco
from ..dominio import ROTULO_ALERTA, Medicamento, Resumo
from ..texto import (codigo, descricao_localizacao, fmt_data, fmt_data_hora, fmt_dinheiro,
                     fmt_inteiro, fmt_sinal)
from .configuracoes import ConfiguracaoService
from .estoque import EstoqueService
from .medicamentos import (SIT_BAIXO, SIT_PROXIMO, SIT_TODOS, SIT_VENCIDO, MedicamentoService)

REL_ESTOQUE_ATUAL = "estoque_atual"
REL_ESTOQUE_BAIXO = "estoque_baixo"
REL_VENCIDOS = "vencidos"
REL_PROXIMOS = "proximos_vencimento"
REL_MOVIMENTACOES = "movimentacoes"
REL_VALOR = "valor_estoque"

TIPOS_RELATORIO = [
    (REL_ESTOQUE_ATUAL, "Estoque atual", "Todos os medicamentos cadastrados e suas quantidades."),
    (REL_ESTOQUE_BAIXO, "Estoque baixo", "Medicamentos com estoque igual ou abaixo do mínimo."),
    (REL_VENCIDOS, "Produtos vencidos", "Medicamentos com validade vencida e unidades em estoque."),
    (REL_PROXIMOS, "Próximos do vencimento",
     "Medicamentos que vencem dentro do prazo de alerta configurado."),
    (REL_MOVIMENTACOES, "Movimentações", "Entradas e saídas de estoque em um período."),
    (REL_VALOR, "Valor do estoque", "Valor estimado do estoque (quantidade × preço)."),
]


@dataclass
class Coluna:
    titulo: str
    tipo: str = "texto"        # texto | inteiro | sinal | dinheiro | data | datahora
    largura: float = 1.0       # largura relativa (PDF e tela)


@dataclass
class Relatorio:
    tipo: str
    titulo: str
    subtitulo: str
    colunas: list[Coluna]
    linhas: list[list[Any]]
    resumo: list[tuple[str, str]] = field(default_factory=list)

    def linhas_formatadas(self) -> list[list[str]]:
        return [[formatar_valor(v, c.tipo) for v, c in zip(linha, self.colunas)]
                for linha in self.linhas]


def formatar_valor(valor: Any, tipo: str) -> str:
    if valor is None:
        return ""
    if tipo == "inteiro":
        return fmt_inteiro(valor)
    if tipo == "sinal":
        return fmt_sinal(valor)
    if tipo == "dinheiro":
        return fmt_dinheiro(valor)
    if tipo == "data":
        return fmt_data(valor, vazio="")
    if tipo == "datahora":
        return fmt_data_hora(valor, vazio="")
    return str(valor)


class RelatorioService:
    def __init__(self, db: Banco, config: ConfiguracaoService,
                 medicamentos: MedicamentoService, estoque: EstoqueService):
        self.db = db
        self.config = config
        self.medicamentos = medicamentos
        self.estoque = estoque

    # -------------------------------------------------------------- dashboard
    def resumo(self, hoje: date | None = None) -> Resumo:
        hoje = hoje or date.today()
        dias = self.config.dias_alerta
        limite = (hoje + timedelta(days=dias)).isoformat()
        r = self.db.conn.execute(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(quantidade_atual), 0) AS unidades,
                      COALESCE(SUM(CASE WHEN quantidade_atual <= estoque_minimo THEN 1 ELSE 0 END), 0) AS baixo,
                      COALESCE(SUM(CASE WHEN quantidade_atual > 0 AND data_validade IS NOT NULL
                                         AND data_validade < :hoje THEN 1 ELSE 0 END), 0) AS vencidos,
                      COALESCE(SUM(CASE WHEN quantidade_atual > 0 AND data_validade >= :hoje
                                         AND data_validade <= :limite THEN 1 ELSE 0 END), 0) AS proximos,
                      COALESCE(SUM(quantidade_atual * preco_compra_centavos), 0) AS custo,
                      COALESCE(SUM(quantidade_atual * preco_venda_centavos), 0) AS venda
               FROM medicamentos WHERE ativo = 1""",
            {"hoje": hoje.isoformat(), "limite": limite}).fetchone()
        return Resumo(total_medicamentos=r["total"], total_unidades=r["unidades"],
                      estoque_baixo=r["baixo"], vencidos=r["vencidos"],
                      proximos_vencimento=r["proximos"], valor_custo_centavos=r["custo"],
                      valor_venda_centavos=r["venda"], dias_alerta=dias)

    def lista_estoque_baixo(self, limite: int | None = None,
                            hoje: date | None = None) -> list[Medicamento]:
        """Estoque baixo, dos mais críticos (maior falta) para os menos críticos."""
        itens = self.medicamentos.listar(situacao=SIT_BAIXO, hoje=hoje,
                                         dias_alerta=self.config.dias_alerta)
        itens.sort(key=lambda m: (m.quantidade_atual - m.estoque_minimo, m.rotulo.lower()))
        return itens[:limite] if limite else itens

    def lista_vencimentos(self, limite: int | None = None,
                          hoje: date | None = None) -> list[Medicamento]:
        """Vencidos e próximos do vencimento, em ordem de validade."""
        dias = self.config.dias_alerta
        itens = (self.medicamentos.listar(situacao=SIT_VENCIDO, hoje=hoje, dias_alerta=dias)
                 + self.medicamentos.listar(situacao=SIT_PROXIMO, hoje=hoje, dias_alerta=dias))
        itens.sort(key=lambda m: (m.data_validade, m.rotulo.lower()))
        return itens[:limite] if limite else itens

    # -------------------------------------------------------------- relatórios
    def gerar(self, tipo: str, *, hoje: date | None = None, data_inicio: date | None = None,
              data_fim: date | None = None) -> Relatorio:
        hoje = hoje or date.today()
        dias = self.config.dias_alerta
        emitido = f"Emitido em {fmt_data_hora(datetime.now())}"
        if tipo == REL_ESTOQUE_ATUAL:
            return self._estoque_atual(hoje, dias, emitido)
        if tipo == REL_ESTOQUE_BAIXO:
            return self._estoque_baixo(hoje, dias, emitido)
        if tipo == REL_VENCIDOS:
            return self._vencidos(hoje, dias, emitido)
        if tipo == REL_PROXIMOS:
            return self._proximos(hoje, dias, emitido)
        if tipo == REL_MOVIMENTACOES:
            return self._movimentacoes(data_inicio, data_fim, emitido)
        if tipo == REL_VALOR:
            return self._valor(hoje, dias, emitido)
        raise ValueError(f"Relatório desconhecido: {tipo}")

    @staticmethod
    def _local(m: Medicamento) -> str:
        return descricao_localizacao(m.setor, m.corredor, m.estante, m.prateleira, m.gaveta,
                                     sep=" / ", incluir_setor=True, vazio="")

    @staticmethod
    def _situacao(m: Medicamento, hoje: date, dias: int) -> str:
        alertas = m.alertas(hoje, dias)
        return ", ".join(ROTULO_ALERTA[a] for a in alertas) if alertas else "OK"

    def _estoque_atual(self, hoje, dias, emitido) -> Relatorio:
        itens = self.medicamentos.listar(hoje=hoje, dias_alerta=dias)
        cols = [Coluna("Código", largura=0.6), Coluna("Medicamento", largura=2.0),
                Coluna("Princípio ativo", largura=1.5), Coluna("Dosagem", largura=0.8),
                Coluna("Laboratório", largura=1.3), Coluna("Categoria", largura=1.1),
                Coluna("Estoque", "inteiro", 0.7), Coluna("Mínimo", "inteiro", 0.7),
                Coluna("Localização", largura=1.8), Coluna("Lote", largura=0.8),
                Coluna("Validade", "data", 0.9), Coluna("Situação", largura=1.2)]
        linhas = [[codigo(m.id), m.nome, m.principio_ativo, m.dosagem_completa, m.laboratorio,
                   m.categoria, m.quantidade_atual, m.estoque_minimo, self._local(m), m.lote,
                   m.data_validade, self._situacao(m, hoje, dias)] for m in itens]
        resumo = [("Medicamentos", fmt_inteiro(len(itens))),
                  ("Unidades em estoque", fmt_inteiro(sum(m.quantidade_atual for m in itens)))]
        return Relatorio(REL_ESTOQUE_ATUAL, "Estoque atual", emitido, cols, linhas, resumo)

    def _estoque_baixo(self, hoje, dias, emitido) -> Relatorio:
        itens = self.lista_estoque_baixo(hoje=hoje)
        cols = [Coluna("Código", largura=0.6), Coluna("Medicamento", largura=2.2),
                Coluna("Princípio ativo", largura=1.6), Coluna("Estoque", "inteiro", 0.7),
                Coluna("Mínimo", "inteiro", 0.7), Coluna("Falta repor", "inteiro", 0.8),
                Coluna("Laboratório", largura=1.4), Coluna("Localização", largura=2.0)]
        linhas = [[codigo(m.id), m.rotulo, m.principio_ativo, m.quantidade_atual,
                   m.estoque_minimo, max(m.estoque_minimo - m.quantidade_atual, 0),
                   m.laboratorio, self._local(m)] for m in itens]
        resumo = [("Medicamentos com estoque baixo", fmt_inteiro(len(itens))),
                  ("Sem estoque", fmt_inteiro(sum(1 for m in itens if m.quantidade_atual == 0)))]
        return Relatorio(REL_ESTOQUE_BAIXO, "Estoque baixo",
                         "Estoque atual menor ou igual ao estoque mínimo. " + emitido,
                         cols, linhas, resumo)

    def _vencidos(self, hoje, dias, emitido) -> Relatorio:
        itens = self.medicamentos.listar(situacao=SIT_VENCIDO, hoje=hoje, dias_alerta=dias)
        itens.sort(key=lambda m: m.data_validade)
        cols = [Coluna("Código", largura=0.6), Coluna("Medicamento", largura=2.2),
                Coluna("Lote", largura=0.9), Coluna("Validade", "data", 0.9),
                Coluna("Dias vencido", "inteiro", 0.9), Coluna("Estoque", "inteiro", 0.7),
                Coluna("Valor (custo)", "dinheiro", 1.0), Coluna("Localização", largura=2.0)]
        linhas = [[codigo(m.id), m.rotulo, m.lote, m.data_validade,
                   (hoje - m.data_validade).days, m.quantidade_atual,
                   m.valor_custo_centavos, self._local(m)] for m in itens]
        resumo = [("Medicamentos vencidos", fmt_inteiro(len(itens))),
                  ("Unidades vencidas", fmt_inteiro(sum(m.quantidade_atual for m in itens))),
                  ("Valor a preço de custo", fmt_dinheiro(sum(m.valor_custo_centavos for m in itens)))]
        return Relatorio(REL_VENCIDOS, "Produtos vencidos",
                         f"Validade anterior a {fmt_data(hoje)}. " + emitido, cols, linhas, resumo)

    def _proximos(self, hoje, dias, emitido) -> Relatorio:
        itens = self.medicamentos.listar(situacao=SIT_PROXIMO, hoje=hoje, dias_alerta=dias)
        itens.sort(key=lambda m: m.data_validade)
        cols = [Coluna("Código", largura=0.6), Coluna("Medicamento", largura=2.2),
                Coluna("Lote", largura=0.9), Coluna("Validade", "data", 0.9),
                Coluna("Dias restantes", "inteiro", 0.9), Coluna("Estoque", "inteiro", 0.7),
                Coluna("Valor (custo)", "dinheiro", 1.0), Coluna("Localização", largura=2.0)]
        linhas = [[codigo(m.id), m.rotulo, m.lote, m.data_validade,
                   (m.data_validade - hoje).days, m.quantidade_atual,
                   m.valor_custo_centavos, self._local(m)] for m in itens]
        resumo = [("Medicamentos próximos do vencimento", fmt_inteiro(len(itens))),
                  ("Prazo de alerta", f"{dias} dias")]
        return Relatorio(REL_PROXIMOS, "Próximos do vencimento",
                         f"Vencem em até {dias} dias. " + emitido, cols, linhas, resumo)

    def _movimentacoes(self, data_inicio, data_fim, emitido) -> Relatorio:
        movs = self.estoque.listar(data_inicio=data_inicio, data_fim=data_fim)
        cols = [Coluna("Data/hora", "datahora", 1.2), Coluna("Medicamento", largura=2.4),
                Coluna("Tipo", largura=0.8), Coluna("Quantidade", "sinal", 0.9),
                Coluna("Estoque anterior", "inteiro", 1.0),
                Coluna("Estoque posterior", "inteiro", 1.0),
                Coluna("Motivo", largura=1.6), Coluna("Observação", largura=2.0)]
        linhas = [[m.data_hora, m.medicamento + (" (excluído)" if m.excluido else ""),
                   m.rotulo_tipo, m.quantidade_com_sinal, m.estoque_anterior,
                   m.estoque_posterior, m.motivo, m.observacao] for m in movs]
        entradas = sum(m.quantidade for m in movs if m.tipo == "ENTRADA")
        saidas = sum(m.quantidade for m in movs if m.tipo == "SAIDA")
        if data_inicio or data_fim:
            periodo = f"Período: {fmt_data(data_inicio, 'início')} a {fmt_data(data_fim, 'hoje')}. "
        else:
            periodo = "Todo o período. "
        resumo = [("Movimentações", fmt_inteiro(len(movs))),
                  ("Total de entradas", fmt_sinal(entradas)),
                  ("Total de saídas", fmt_sinal(-saidas))]
        return Relatorio(REL_MOVIMENTACOES, "Movimentações de estoque", periodo + emitido,
                         cols, linhas, resumo)

    def _valor(self, hoje, dias, emitido) -> Relatorio:
        itens = self.medicamentos.listar(hoje=hoje, dias_alerta=dias)
        cols = [Coluna("Código", largura=0.6), Coluna("Medicamento", largura=2.4),
                Coluna("Estoque", "inteiro", 0.7), Coluna("Preço de compra", "dinheiro", 1.0),
                Coluna("Valor (custo)", "dinheiro", 1.1), Coluna("Preço de venda", "dinheiro", 1.0),
                Coluna("Valor (venda)", "dinheiro", 1.1)]
        linhas = [[codigo(m.id), m.rotulo, m.quantidade_atual, m.preco_compra_centavos,
                   m.valor_custo_centavos, m.preco_venda_centavos, m.valor_venda_centavos]
                  for m in itens]
        custo = sum(m.valor_custo_centavos for m in itens)
        venda = sum(m.valor_venda_centavos for m in itens)
        resumo = [("Unidades em estoque", fmt_inteiro(sum(m.quantidade_atual for m in itens))),
                  ("Valor total a preço de custo", fmt_dinheiro(custo)),
                  ("Valor total a preço de venda", fmt_dinheiro(venda))]
        return Relatorio(REL_VALOR, "Valor estimado do estoque",
                         "Quantidade × preço de cada medicamento. " + emitido, cols, linhas, resumo)
