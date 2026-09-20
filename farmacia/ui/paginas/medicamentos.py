"""Lista principal de medicamentos com pesquisa, filtros e ações por linha."""
from __future__ import annotations

import tkinter as tk
from datetime import date

import customtkinter as ctk

from ...dominio import ENTRADA, ROTULO_ALERTA, SAIDA, Medicamento
from ...servicos.medicamentos import (SIT_BAIXO, SIT_PROXIMO, SIT_SEM_ESTOQUE, SIT_TODOS,
                                      SIT_VENCIDO)
from ...texto import codigo, fmt_data, fmt_inteiro
from ..tema import COR, TAG_DO_ALERTA, botao, fonte
from ..widgets import Cartao, CampoBusca, Col, TabelaDados, cabecalho_pagina

SITUACOES = [
    ("Todas as situações", SIT_TODOS), ("Estoque baixo", SIT_BAIXO), ("Sem estoque", SIT_SEM_ESTOQUE),
    ("Vencidos", SIT_VENCIDO), ("Próximos do vencimento", SIT_PROXIMO),
]
TODAS_CATEGORIAS = "Todas as categorias"


def linha_medicamento(m: Medicamento, hoje: date, dias_alerta: int) -> dict:
    """Converte um medicamento na linha de uma TabelaDados."""
    alertas = m.alertas(hoje, dias_alerta)
    return {
        "iid": m.id,
        "tag": TAG_DO_ALERTA[alertas[0]] if alertas else "",
        "valores": {
            "codigo": codigo(m.id), "nome": m.nome, "principio": m.principio_ativo,
            "dosagem": m.dosagem_completa, "estoque": fmt_inteiro(m.quantidade_atual),
            "local": m.localizacao_curta,
            "validade": fmt_data(m.data_validade),
            "situacao": " · ".join(ROTULO_ALERTA[a] for a in alertas) if alertas else "OK",
        },
        "ordem": {"estoque": m.quantidade_atual, "codigo": m.id,
                  "validade": m.data_validade or date.max},
    }


class PaginaMedicamentos(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._filtro_situacao = SIT_TODOS

        # ---- cabeçalho
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=32, pady=(26, 12))
        topo.columnconfigure(0, weight=1)
        cab, _ = cabecalho_pagina(topo, "Medicamentos",
                                  "Pesquise por nome, princípio ativo, laboratório, lote, local (ex.: Corredor A)…")
        cab.grid(row=0, column=0, sticky="w")
        botao(topo, "+  Novo medicamento", lambda: app.abrir_formulario(), largura=190, altura=40).grid(
            row=0, column=1, sticky="e")

        # ---- pesquisa e filtros
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 10))
        barra.columnconfigure(0, weight=1)
        self.busca = CampoBusca(barra, "Pesquisar medicamentos…", lambda _t: self.atualizar())
        self.busca.grid(row=0, column=0, sticky="ew")
        estilo_menu = dict(height=40, font=fonte(13), dropdown_font=fonte(13), fg_color=COR.cartao,
                           button_color=COR.borda, button_hover_color="#C5D3D0",
                           text_color=COR.texto, dropdown_text_color=COR.texto,
                           dropdown_fg_color=COR.cartao, dropdown_hover_color=COR.primaria_suave)
        self.menu_categoria = ctk.CTkOptionMenu(barra, values=[TODAS_CATEGORIAS], width=200,
                                                command=lambda _v: self.atualizar(), **estilo_menu)
        self.menu_categoria.grid(row=0, column=1, padx=(10, 0))
        self.menu_situacao = ctk.CTkOptionMenu(barra, values=[r for r, _ in SITUACOES], width=200,
                                               command=lambda _v: self.atualizar(), **estilo_menu)
        self.menu_situacao.grid(row=0, column=2, padx=(10, 0))

        # ---- tabela
        cartao = Cartao(self)
        cartao.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 8))
        cartao.rowconfigure(0, weight=1)
        cartao.columnconfigure(0, weight=1)
        self.tabela = TabelaDados(
            cartao,
            [Col("codigo", "Código", 60), Col("nome", "Medicamento", 180),
             Col("principio", "Princípio ativo", 135), Col("dosagem", "Dosagem", 95),
             Col("estoque", "Estoque", 68, "e"), Col("local", "Localização", 215),
             Col("validade", "Validade", 95), Col("situacao", "Situação", 150)],
            altura=14, ao_selecionar=self._selecao_mudou, ao_abrir=app.abrir_detalhes,
            ao_menu=self._menu_contexto,
            mensagem_vazia="Nenhum medicamento encontrado. Tente outra pesquisa ou cadastre um novo.")
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        # ---- ações
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 20))
        self.contador = ctk.CTkLabel(rodape, text="", font=fonte(13), text_color=COR.texto_suave)
        self.contador.pack(side="left")
        self.botoes: list[ctk.CTkButton] = []
        for texto, tipo, comando in (("Excluir", "perigo", self._excluir), ("Editar", "secundario", self._editar),
                                     ("Saída", "saida", lambda: self._movimentar(SAIDA)),
                                     ("Entrada", "entrada", lambda: self._movimentar(ENTRADA)),
                                     ("Detalhes", "primario", self._detalhes)):
            b = botao(rodape, texto, comando, tipo=tipo, largura=100)
            b.pack(side="right", padx=(8, 0))
            b.configure(state="disabled")
            self.botoes.append(b)

        self.menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        for rotulo, comando in (("Ver detalhes", self._detalhes), ("Registrar entrada", lambda: self._movimentar(ENTRADA)),
                                ("Registrar saída", lambda: self._movimentar(SAIDA)), ("Editar", self._editar),
                                (None, None), ("Excluir", self._excluir)):
            if rotulo is None:
                self.menu.add_separator()
            else:
                self.menu.add_command(label=rotulo, command=comando)

    # ------------------------------------------------------------------- filtros
    def aplicar_filtro_situacao(self, situacao: str, limpar_busca: bool = True) -> None:
        """Usado pelos atalhos do dashboard (ex.: clicar em 'Estoque baixo')."""
        rotulo = next((r for r, v in SITUACOES if v == situacao), SITUACOES[0][0])
        self.menu_situacao.set(rotulo)
        self.menu_categoria.set(TODAS_CATEGORIAS)
        if limpar_busca:
            self.busca.definir("", disparar=False)
        self.atualizar()

    def _situacao_escolhida(self) -> str:
        return dict(SITUACOES).get(self.menu_situacao.get(), SIT_TODOS)

    # -------------------------------------------------------------------- dados
    def atualizar(self) -> None:
        ctx = self.app.ctx
        categorias = ctx.medicamentos.listar_categorias()
        opcoes = [TODAS_CATEGORIAS] + categorias
        atual = self.menu_categoria.get()
        self.menu_categoria.configure(values=opcoes)
        if atual not in opcoes:
            self.menu_categoria.set(TODAS_CATEGORIAS)
            atual = TODAS_CATEGORIAS
        dias = ctx.config.dias_alerta
        hoje = date.today()
        itens = ctx.medicamentos.listar(
            self.busca.texto(), categoria=None if atual == TODAS_CATEGORIAS else atual,
            situacao=self._situacao_escolhida(), dias_alerta=dias, hoje=hoje)
        self.tabela.definir_linhas([linha_medicamento(m, hoje, dias) for m in itens])
        total = ctx.medicamentos.total()
        filtrando = bool(self.busca.texto()) or atual != TODAS_CATEGORIAS or \
            self._situacao_escolhida() != SIT_TODOS
        if filtrando:
            texto = f"Mostrando {len(itens)} de {total}"
        else:
            texto = "1 medicamento" if total == 1 else f"{total} medicamentos"
        self.contador.configure(text=texto)
        self._selecao_mudou(self.tabela.selecionado())

    def _selecao_mudou(self, iid) -> None:
        for b in self.botoes:
            b.configure(state="normal" if iid else "disabled")

    # ------------------------------------------------------------------- ações
    def _id(self) -> int | None:
        iid = self.tabela.selecionado()
        return int(iid) if iid else None

    def _detalhes(self):
        if (i := self._id()):
            self.app.abrir_detalhes(i)

    def _movimentar(self, tipo: str):
        if (i := self._id()):
            self.app.abrir_movimentacao(i, tipo)

    def _editar(self):
        if (i := self._id()):
            self.app.abrir_formulario(i)

    def _excluir(self):
        if (i := self._id()):
            self.app.excluir_medicamento(i)

    def _menu_contexto(self, evento, _iid):
        try:
            self.menu.tk_popup(evento.x_root, evento.y_root)
        finally:
            self.menu.grab_release()
