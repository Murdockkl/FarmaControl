"""Histórico de movimentações de estoque, com filtros por período, medicamento e tipo."""
from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from ...dominio import ENTRADA, SAIDA
from ...texto import fmt_data, fmt_inteiro, fmt_sinal
from ...validacao import converter_data
from ..tema import COR, botao, fonte
from ..widgets import (Cartao, CampoBusca, Col, SeletorSegmentado, TabelaDados,
                       aplicar_mascara_data, cabecalho_pagina, limpar_entrada)

_TIPOS = [("Todos", None), ("Entradas", ENTRADA), ("Saídas", SAIDA)]


class PaginaHistorico(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        cab, _ = cabecalho_pagina(self, "Histórico de movimentações",
                                  "Toda entrada e saída de estoque fica registrada aqui.")
        cab.grid(row=0, column=0, sticky="w", padx=32, pady=(26, 12))

        # ---- filtros
        filtros = Cartao(self)
        filtros.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 10))
        filtros.columnconfigure(2, weight=1)
        linha1 = ctk.CTkFrame(filtros, fg_color="transparent")
        linha1.pack(fill="x", padx=16, pady=(14, 4))
        estilo_data = dict(width=118, height=36, font=fonte(13), corner_radius=8,
                           border_color=COR.borda, fg_color=COR.cartao)
        for texto in ("De", ):
            ctk.CTkLabel(linha1, text=texto, font=fonte(12), text_color=COR.texto_suave).pack(side="left")
        self.data_ini = ctk.CTkEntry(linha1, placeholder_text="dd/mm/aaaa", **estilo_data)
        self.data_ini.pack(side="left", padx=(6, 12))
        ctk.CTkLabel(linha1, text="até", font=fonte(12), text_color=COR.texto_suave).pack(side="left")
        self.data_fim = ctk.CTkEntry(linha1, placeholder_text="dd/mm/aaaa", **estilo_data)
        self.data_fim.pack(side="left", padx=(6, 16))
        for entrada in (self.data_ini, self.data_fim):
            aplicar_mascara_data(entrada)
            entrada.bind("<Return>", lambda _e: self.atualizar(), add="+")
        for rotulo, comando in (("Hoje", lambda: self._periodo(0)),
                                ("7 dias", lambda: self._periodo(6)),
                                ("30 dias", lambda: self._periodo(29)),
                                ("Tudo", lambda: self._periodo(None))):
            botao(linha1, rotulo, comando, tipo="suave", altura=32, largura=68).pack(side="left", padx=3)
        self.tipo = SeletorSegmentado(linha1, [r for r, _ in _TIPOS], lambda _v: self.atualizar(),
                                      altura=38)
        self.tipo.pack(side="right")

        linha2 = ctk.CTkFrame(filtros, fg_color="transparent")
        linha2.pack(fill="x", padx=16, pady=(4, 8))
        linha2.columnconfigure(0, weight=1)
        self.busca = CampoBusca(linha2, "Filtrar por medicamento (nome ou princípio ativo)…",
                                lambda _t: self.atualizar())
        self.busca.grid(row=0, column=0, sticky="ew")
        botao(linha2, "Aplicar", self.atualizar, largura=90, altura=40).grid(row=0, column=1, padx=(10, 0))
        self.erro = ctk.CTkLabel(filtros, text="", font=fonte(12, "bold"), text_color=COR.perigo,
                                 anchor="w")                       # só aparece quando há erro

        # ---- tabela
        cartao = Cartao(self)
        cartao.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 8))
        cartao.rowconfigure(0, weight=1)
        cartao.columnconfigure(0, weight=1)
        self.tabela = TabelaDados(
            cartao,
            [Col("data", "Data", 95), Col("hora", "Hora", 60), Col("nome", "Medicamento", 240),
             Col("tipo", "Tipo", 75), Col("qtd", "Quantidade", 100, "e"),
             Col("anterior", "Est. anterior", 105, "e"), Col("posterior", "Est. posterior", 110, "e"),
             Col("motivo", "Motivo", 160), Col("obs", "Observação", 170)],
            altura=14, ao_abrir=self._abrir, mensagem_vazia="Nenhuma movimentação encontrada com estes filtros.")
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self._med_do_mov: dict[str, tuple[int, bool]] = {}

        self.resumo = ctk.CTkLabel(self, text="", font=fonte(13), text_color=COR.texto_suave, anchor="w")
        self.resumo.grid(row=3, column=0, sticky="w", padx=34, pady=(0, 20))

        self._periodo(29, atualizar=False)          # começa mostrando os últimos 30 dias

    # ---------------------------------------------------------------- filtros
    def _periodo(self, dias: int | None, atualizar: bool = True) -> None:
        for e in (self.data_ini, self.data_fim):
            limpar_entrada(e)
        if dias is not None:
            hoje = date.today()
            self.data_ini.insert(0, fmt_data(hoje - timedelta(days=dias)))
            self.data_fim.insert(0, fmt_data(hoje))
        if atualizar:
            self.atualizar()

    def _datas(self) -> tuple[date | None, date | None]:
        ini = converter_data(self.data_ini.get())
        fim = converter_data(self.data_fim.get())
        if ini and fim and ini > fim:
            raise ValueError("A data inicial não pode ser depois da data final.")
        return ini, fim

    def _abrir(self, iid: str) -> None:
        med_id, excluido = self._med_do_mov.get(iid, (None, True))
        if med_id is None:
            return
        if excluido:
            self.app.mensagem("Medicamento excluído",
                              "Este medicamento foi excluído do cadastro. Os registros do histórico "
                              "foram mantidos, mas não há mais detalhes para mostrar.", "info")
        else:
            self.app.abrir_detalhes(med_id)

    # ------------------------------------------------------------------ dados
    def atualizar(self) -> None:
        try:
            ini, fim = self._datas()
        except ValueError as e:
            self.erro.configure(text=f"Período inválido: {e}")
            self.erro.pack(anchor="w", padx=18, pady=(0, 8))
            return
        self.erro.pack_forget()
        tipo = dict(_TIPOS)[self.tipo.get()]
        movs = self.app.ctx.estoque.listar(data_inicio=ini, data_fim=fim, tipo=tipo,
                                           texto=self.busca.texto(), limite=2000)
        self._med_do_mov = {str(m.id): (m.medicamento_id, m.excluido) for m in movs}
        self.tabela.definir_linhas([{
            "iid": m.id, "tag": "entrada" if m.tipo == ENTRADA else "saida",
            "valores": {"data": fmt_data(m.data_hora.date()), "hora": m.data_hora.strftime("%H:%M"),
                        "nome": m.medicamento + ("  (excluído)" if m.excluido else ""),
                        "tipo": m.rotulo_tipo, "qtd": fmt_sinal(m.quantidade_com_sinal),
                        "anterior": fmt_inteiro(m.estoque_anterior),
                        "posterior": fmt_inteiro(m.estoque_posterior), "motivo": m.motivo,
                        "obs": m.observacao},
            "ordem": {"data": m.data_hora, "hora": m.data_hora.time(),
                      "qtd": m.quantidade_com_sinal, "anterior": m.estoque_anterior,
                      "posterior": m.estoque_posterior}} for m in movs])
        entradas = sum(m.quantidade for m in movs if m.tipo == ENTRADA)
        saidas = sum(m.quantidade for m in movs if m.tipo == SAIDA)
        aviso_limite = "  (mostrando as 2.000 mais recentes)" if len(movs) >= 2000 else ""
        self.resumo.configure(
            text=f"{fmt_inteiro(len(movs))} movimentações  ·  Entradas: {fmt_sinal(entradas)}  ·  "
                 f"Saídas: {fmt_sinal(-saidas)}{aviso_limite}")
