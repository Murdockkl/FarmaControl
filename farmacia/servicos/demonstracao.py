"""Dados FICTÍCIOS de demonstração, para testar o sistema sem cadastrar nada à mão.

Todos os registros criados aqui ficam marcados como "demo" no banco e podem ser
removidos de uma vez, sem afetar os medicamentos reais.
Os nomes comerciais e laboratórios são inventados. As relações entre medicamentos
(campo "semelhantes") também são apenas exemplos de como cadastrar essa informação.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from ..banco import Banco
from ..dominio import ENTRADA, SAIDA, MedicamentoDados
from .estoque import EstoqueService
from .medicamentos import MedicamentoService

AVISO_DEMO = "DADO FICTÍCIO DE DEMONSTRAÇÃO - não representa um produto real."


@dataclass
class _Demo:
    chave: str
    nome: str
    principio: str
    generico: str
    eh_generico: bool
    lab: str
    categoria: str
    dosagem: str
    unidade: str
    forma: str
    minimo: int
    estoque_final: int
    compra: int                    # centavos
    venda: int                     # centavos
    local: tuple[str, str, str, str, str]      # setor, corredor, estante, prateleira, gaveta
    lote: str
    validade_dias: int             # dias a partir de hoje (negativo = já vencido)
    saidas: list[tuple[int, int]] = field(default_factory=list)      # (dias atrás, quantidade)
    reposicoes: list[tuple[int, int]] = field(default_factory=list)  # (dias atrás, quantidade)
    relacionados: tuple[str, ...] = ()


_MED = "Medicamentos"
_LISTA = [
    _Demo("para_gen", "Paracetamol Genérico", "Paracetamol", "Paracetamol 750 mg Genérico", True,
          "Laboratório Exemplo A", "Analgésico", "750", "mg", "Comprimido", 20, 35, 420, 890,
          (_MED, "A", "02", "03", ""), "L001", 400, [(12, 5), (6, 8), (2, 3)], [(9, 30)],
          ("para_marca", "para_gotas")),
    _Demo("para_marca", "Febrolyn", "Paracetamol", "Paracetamol 750 mg Genérico", False,
          "Laboratório Exemplo B", "Analgésico", "750", "mg", "Comprimido", 15, 12, 980, 1750,
          (_MED, "A", "02", "04", ""), "L014", 200, [(20, 6), (5, 4)]),
    _Demo("para_gotas", "Paracetamol Genérico", "Paracetamol", "Paracetamol 200 mg/mL Genérico",
          True, "Laboratório Exemplo A", "Analgésico", "200", "mg/mL", "Gotas", 8, 18, 610, 1190,
          (_MED, "A", "03", "01", ""), "L007", 25, [(15, 4), (3, 2)]),
    _Demo("dip_gen", "Dipirona Sódica Genérico", "Dipirona sódica", "Dipirona sódica 500 mg Genérico",
          True, "Laboratório Exemplo C", "Analgésico", "500", "mg", "Comprimido", 30, 60, 310, 690,
          (_MED, "A", "01", "02", ""), "L102", 520, [(18, 10), (8, 12), (1, 6)], [],
          ("dip_marca",)),
    _Demo("dip_marca", "Dorexa Gotas", "Dipirona sódica", "Dipirona sódica 500 mg/mL Genérico",
          False, "Laboratório Exemplo B", "Analgésico", "500", "mg/mL", "Gotas", 10, 0, 720, 1490,
          (_MED, "A", "01", "03", ""), "L033", 330, [(10, 9), (4, 6)]),
    _Demo("ibu_gen", "Ibuprofeno Genérico", "Ibuprofeno", "Ibuprofeno 600 mg Genérico", True,
          "Laboratório Exemplo C", "Anti-inflamatório", "600", "mg", "Comprimido", 15, 40, 540, 1150,
          (_MED, "A", "04", "01", ""), "L210", 18, [(14, 10), (7, 5)], [], ("ibu_marca",)),
    _Demo("ibu_marca", "Inflamex", "Ibuprofeno", "Ibuprofeno 600 mg Genérico", False,
          "Laboratório Exemplo B", "Anti-inflamatório", "600", "mg", "Comprimido", 10, 8, 1290, 2290,
          (_MED, "A", "04", "02", ""), "L055", 300, [(11, 7), (2, 3)]),
    _Demo("amox_cap", "Amoxicilina Genérico", "Amoxicilina", "Amoxicilina 500 mg Genérico", True,
          "Laboratório Exemplo A", "Antibiótico", "500", "mg", "Cápsula", 12, 25, 890, 1990,
          (_MED, "B", "01", "02", ""), "L088", -20, [(25, 8), (16, 6)], [], ("amox_xar",)),
    _Demo("amox_xar", "Amoxicilina Genérico", "Amoxicilina", "Amoxicilina 250 mg/5 mL Genérico",
          True, "Laboratório Exemplo A", "Antibiótico", "250", "mg/5 mL", "Xarope", 6, 6, 1490, 2790,
          (_MED, "B", "01", "04", ""), "L091", 90, [(13, 3)]),
    _Demo("lora", "Loratadina Genérico", "Loratadina", "Loratadina 10 mg Genérico", True,
          "Laboratório Exemplo C", "Antialérgico", "10", "mg", "Comprimido", 15, 45, 260, 690,
          (_MED, "B", "02", "01", ""), "L120", 500, [(9, 5), (3, 5)]),
    _Demo("omep", "Omeprazol Genérico", "Omeprazol", "Omeprazol 20 mg Genérico", True,
          "Laboratório Exemplo A", "Gastrointestinal", "20", "mg", "Cápsula", 20, 30, 380, 990,
          (_MED, "B", "03", "02", ""), "L145", 150, [(17, 10), (5, 5)]),
    _Demo("losa", "Losartana Genérico", "Losartana potássica", "Losartana 50 mg Genérico", True,
          "Laboratório Exemplo C", "Anti-hipertensivo", "50", "mg", "Comprimido", 25, 55, 420, 1190,
          (_MED, "C", "01", "03", ""), "L301", 600, [(21, 15), (7, 10)]),
    _Demo("vitc", "Vitamina C Efervescente", "Ácido ascórbico", "", False,
          "Laboratório Exemplo B", "Vitaminas", "1", "g", "Comprimido", 20, 70, 590, 1490,
          ("Suplementos", "D", "01", "01", ""), "L410", 45, [(30, 12), (10, 8)]),
    _Demo("soro", "Soro Fisiológico", "Cloreto de sódio", "", False,
          "Laboratório Exemplo C", "Soluções", "0,9", "%", "Solução", 10, 22, 280, 690,
          ("Higiene", "D", "02", "01", "2"), "L502", 700, [(19, 6), (8, 4)]),
    _Demo("creme", "Creme Cicatrizante Demo", "Dexpantenol", "", False,
          "Laboratório Exemplo A", "Dermatológico", "50", "mg/g", "Creme", 10, 14, 1190, 2490,
          ("Dermocosméticos", "E", "01", "02", ""), "L610", 260, [(22, 3), (6, 2)]),
]


class DemoService:
    def __init__(self, db: Banco, medicamentos: MedicamentoService, estoque: EstoqueService):
        self.db = db
        self.medicamentos = medicamentos
        self.estoque = estoque

    def existem_dados_demo(self) -> bool:
        return self.db.conn.execute(
            "SELECT 1 FROM medicamentos WHERE demo = 1 AND ativo = 1 LIMIT 1").fetchone() is not None

    def adicionar(self, hoje: date | None = None) -> int:
        """Cadastra os medicamentos fictícios (e um histórico de movimentações). Devolve quantos."""
        hoje = hoje or date.today()
        aleatorio = random.Random(2026)
        ids: dict[str, int] = {}
        with self.db.transacao():
            for d in _LISTA:
                dados = MedicamentoDados(
                    nome=d.nome, principio_ativo=d.principio, nome_generico=d.generico,
                    eh_generico=d.eh_generico, laboratorio=d.lab, categoria=d.categoria,
                    dosagem=d.dosagem, unidade_medida=d.unidade, forma_farmaceutica=d.forma,
                    quantidade_atual=0, estoque_minimo=d.minimo, preco_compra_centavos=d.compra,
                    preco_venda_centavos=d.venda, setor=d.local[0], corredor=d.local[1],
                    estante=d.local[2], prateleira=d.local[3], gaveta=d.local[4], lote=d.lote,
                    data_fabricacao=hoje - timedelta(days=200),
                    data_validade=hoje + timedelta(days=d.validade_dias),
                    observacoes=AVISO_DEMO)
                ids[d.chave] = self.medicamentos.criar(dados, registrar_estoque_inicial=False,
                                                       demo=True)
                self._historico(ids[d.chave], d, hoje, aleatorio)
            for d in _LISTA:                               # relações (precisam dos ids prontos)
                if d.relacionados:
                    atual = self.medicamentos.obter(ids[d.chave])
                    dados = self._dados_de(atual)
                    dados.relacionados = [m.id for m in atual.relacionados] + \
                                         [ids[c] for c in d.relacionados]
                    self.medicamentos.atualizar(ids[d.chave], dados)
        return len(ids)

    def _historico(self, med_id: int, d: _Demo, hoje: date, aleatorio: random.Random) -> None:
        """Cria compras e vendas fictícias, em ordem cronológica, terminando no estoque desejado."""
        inicial = d.estoque_final + sum(q for _, q in d.saidas) - sum(q for _, q in d.reposicoes)
        eventos = [(60, ENTRADA, inicial, "Compra")]
        eventos += [(dias, ENTRADA, q, "Compra") for dias, q in d.reposicoes]
        eventos += [(dias, SAIDA, q, "Venda") for dias, q in d.saidas]
        eventos.sort(key=lambda e: (-e[0], 0 if e[1] == ENTRADA else 1))
        for dias, tipo, quantidade, motivo in eventos:
            if quantidade <= 0:
                continue
            quando = datetime.combine(hoje - timedelta(days=dias),
                                      time(aleatorio.randint(8, 18), aleatorio.randint(0, 59)))
            self.estoque.registrar_movimentacao(med_id, tipo, quantidade, motivo,
                                                "Movimentação fictícia de demonstração", quando)

    @staticmethod
    def _dados_de(m) -> MedicamentoDados:
        return MedicamentoDados(
            nome=m.nome, principio_ativo=m.principio_ativo, nome_generico=m.nome_generico,
            eh_generico=m.eh_generico, laboratorio=m.laboratorio, categoria=m.categoria,
            dosagem=m.dosagem, unidade_medida=m.unidade_medida,
            forma_farmaceutica=m.forma_farmaceutica, quantidade_atual=m.quantidade_atual,
            estoque_minimo=m.estoque_minimo, preco_compra_centavos=m.preco_compra_centavos,
            preco_venda_centavos=m.preco_venda_centavos, setor=m.setor, corredor=m.corredor,
            estante=m.estante, prateleira=m.prateleira, gaveta=m.gaveta, lote=m.lote,
            data_fabricacao=m.data_fabricacao, data_validade=m.data_validade,
            observacoes=m.observacoes)

    def remover(self) -> int:
        """Apaga por completo os dados de demonstração (e o histórico deles). Devolve quantos."""
        conn = self.db.conn
        with self.db.transacao():
            ids = [r[0] for r in conn.execute("SELECT id FROM medicamentos WHERE demo = 1")]
            if not ids:
                return 0
            marcas = ",".join("?" * len(ids))
            conn.execute(f"DELETE FROM movimentacoes WHERE medicamento_id IN ({marcas})", ids)
            conn.execute(f"DELETE FROM medicamentos WHERE id IN ({marcas})", ids)
            # limpa laboratórios, categorias e locais que sobraram sem uso
            conn.execute("DELETE FROM laboratorios WHERE nome LIKE 'Laboratório Exemplo%' AND id NOT IN "
                         "(SELECT laboratorio_id FROM medicamentos WHERE laboratorio_id IS NOT NULL)")
            conn.execute("DELETE FROM categorias WHERE id NOT IN "
                         "(SELECT categoria_id FROM medicamentos WHERE categoria_id IS NOT NULL) "
                         "AND nome IN (%s)" % ",".join("?" * len({d.categoria for d in _LISTA})),
                         sorted({d.categoria for d in _LISTA}))
            conn.execute("DELETE FROM localizacoes WHERE id NOT IN "
                         "(SELECT localizacao_id FROM medicamentos WHERE localizacao_id IS NOT NULL)")
        return len(ids)
