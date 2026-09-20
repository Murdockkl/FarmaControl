"""Área de Estoque: escolha o medicamento à esquerda e registre entrada ou saída à direita."""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ...dominio import ENTRADA, ROTULO_ALERTA
from ...texto import codigo, fmt_data_hora, fmt_inteiro, fmt_sinal, unidades
from ..dialogos.movimentacao import FormularioMovimentacao
from ..tema import BADGE_DO_ALERTA, COR, fonte
from ..widgets import Cartao, CampoBusca, Col, Selo, TabelaDados, cabecalho_pagina, titulo_secao
from .medicamentos import linha_medicamento


class PaginaEstoque(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.medicamento_id: int | None = None
        self.columnconfigure(0, weight=6, uniform="e")
        self.columnconfigure(1, weight=5, uniform="e")
        self.rowconfigure(1, weight=1)

        cab, _ = cabecalho_pagina(self, "Estoque",
                                  "Registre entradas e saídas. O estoque nunca fica negativo e tudo vai para o histórico.")
        cab.grid(row=0, column=0, columnspan=2, sticky="w", padx=32, pady=(26, 14))

        # ---- esquerda: escolher medicamento
        esquerda = Cartao(self)
        esquerda.grid(row=1, column=0, sticky="nsew", padx=(32, 10), pady=(0, 24))
        esquerda.rowconfigure(2, weight=1)
        esquerda.columnconfigure(0, weight=1)
        titulo_secao(esquerda, "1. Escolha o medicamento").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))
        self.busca = CampoBusca(esquerda, "Nome, princípio ativo, lote, localização…",
                                lambda _t: self._listar())
        self.busca.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.tabela = TabelaDados(
            esquerda, [Col("nome", "Medicamento", 200), Col("estoque", "Estoque", 75, "e"),
                       Col("local", "Localização", 210)],
            altura=12, ao_selecionar=self._escolheu, mensagem_vazia="Nenhum medicamento encontrado.")
        self.tabela.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 8))

        # ---- direita: movimentação (rolável, para caber também em telas pequenas)
        self.direita = Cartao(self)
        self.direita.grid(row=1, column=1, sticky="nsew", padx=(10, 32), pady=(0, 24))
        self.direita.columnconfigure(0, weight=1)
        self.direita.rowconfigure(1, weight=1)
        titulo_secao(self.direita, "2. Registre a movimentação").grid(row=0, column=0, sticky="w",
                                                                       padx=18, pady=(16, 4))
        corpo = ctk.CTkScrollableFrame(self.direita, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=(0, 8))
        corpo.columnconfigure(0, weight=1)

        self.resumo = ctk.CTkFrame(corpo, fg_color=COR.linha, corner_radius=10)
        self.resumo.grid(row=0, column=0, sticky="ew", padx=10)
        self.nome = ctk.CTkLabel(self.resumo, text="Selecione um medicamento na lista ao lado.",
                                 font=fonte(16, "bold"), text_color=COR.texto_suave, anchor="w",
                                 justify="left", wraplength=360)
        self.nome.pack(anchor="w", padx=16, pady=(12, 0))
        self.info = ctk.CTkLabel(self.resumo, text="", font=fonte(12), text_color=COR.texto_suave,
                                 anchor="w", justify="left", wraplength=360)
        self.info.pack(anchor="w", padx=16)
        # frame vazio do CTk mede 200 px por padrão: height=1 evita um espaço enorme sem selos
        self.selos = ctk.CTkFrame(self.resumo, fg_color="transparent", width=1, height=1)
        self.selos.pack(anchor="w", padx=16, pady=(4, 12))
        self.estoque_atual = ctk.CTkLabel(self.resumo, text="", font=fonte(28, "bold"),
                                          text_color=COR.primaria)
        self.estoque_atual.place(relx=1.0, x=-18, y=10, anchor="ne")

        self.formulario = FormularioMovimentacao(corpo, app, compacto=True, ao_concluir=self._concluido)
        self.formulario.grid(row=1, column=0, sticky="ew", padx=10, pady=(12, 0))

        titulo_secao(corpo, "Últimas movimentações deste medicamento").grid(
            row=2, column=0, sticky="w", padx=10, pady=(16, 4))
        self.historico = TabelaDados(
            corpo, [Col("data", "Data e hora", 135), Col("qtd", "Qtd.", 55, "e"),
                    Col("estoque", "Estoque", 90, "e"), Col("motivo", "Motivo", 150)],
            altura=4, ordenavel=False, mensagem_vazia="Sem movimentações.")
        self.historico.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 4))

    # ------------------------------------------------------------------ ações
    def selecionar_medicamento(self, medicamento_id: int, tipo: str | None = None) -> None:
        """Usado por outras telas para abrir o Estoque já com um medicamento escolhido."""
        self.busca.definir("", disparar=False)
        self._listar()
        self.tabela.selecionar(str(medicamento_id))
        self._escolheu(str(medicamento_id))
        if tipo:
            self.formulario.escolher_tipo(tipo)

    def _listar(self) -> None:
        ctx = self.app.ctx
        dias, hoje = ctx.config.dias_alerta, date.today()
        itens = ctx.medicamentos.listar(self.busca.texto(), dias_alerta=dias, hoje=hoje, limite=300)
        self.tabela.definir_linhas([{
            "iid": m.id, "tag": linha_medicamento(m, hoje, dias)["tag"],
            "valores": {"nome": m.rotulo, "estoque": fmt_inteiro(m.quantidade_atual),
                        "local": m.localizacao_curta},
            "ordem": {"estoque": m.quantidade_atual}} for m in itens])

    def _escolheu(self, iid) -> None:
        self.medicamento_id = int(iid) if iid else None
        self._mostrar_medicamento()

    def _concluido(self, _mov) -> None:
        self.formulario.focar_quantidade()

    def _mostrar_medicamento(self) -> None:
        ctx = self.app.ctx
        med = ctx.medicamentos.obter(self.medicamento_id) if self.medicamento_id else None
        for w in self.selos.winfo_children():
            w.destroy()
        if med is None:
            self.medicamento_id = None
            self.nome.configure(text="Selecione um medicamento na lista ao lado.",
                                text_color=COR.texto_suave)
            self.info.configure(text="")
            self.estoque_atual.configure(text="")
            self.formulario.definir_medicamento(None)
            self.historico.definir_linhas([])
            return
        self.nome.configure(text=med.rotulo, text_color=COR.texto)
        self.info.configure(text=f"Código {codigo(med.id)}  ·  {med.principio_ativo}\n"
                                 f"Local: {med.localizacao}")
        self.estoque_atual.configure(text=fmt_inteiro(med.quantidade_atual))
        for a in med.alertas(date.today(), ctx.config.dias_alerta):
            Selo(self.selos, ROTULO_ALERTA[a], BADGE_DO_ALERTA[a]).pack(side="left", padx=(0, 6))
        self.formulario.definir_medicamento(med)
        movs = ctx.estoque.listar(medicamento_id=med.id, limite=4)
        self.historico.definir_linhas([{
            "iid": m.id, "tag": "entrada" if m.tipo == ENTRADA else "saida",
            "valores": {"data": fmt_data_hora(m.data_hora), "qtd": fmt_sinal(m.quantidade_com_sinal),
                        "estoque": f"{m.estoque_anterior} → {m.estoque_posterior}",
                        "motivo": m.motivo}} for m in movs])

    # ------------------------------------------------------------------- dados
    def atualizar(self) -> None:
        self._listar()
        if self.medicamento_id:
            self.tabela.selecionar(str(self.medicamento_id))
            self._mostrar_medicamento()
