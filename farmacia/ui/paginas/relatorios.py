"""Relatórios: escolha o tipo, veja a prévia e exporte para CSV, Excel ou PDF."""
from __future__ import annotations

from datetime import date, timedelta
from tkinter import filedialog

import customtkinter as ctk

from ...dominio import FarmaciaError
from ...servicos import exportacao
from ...servicos.relatorios import (REL_MOVIMENTACOES, TIPOS_RELATORIO, Relatorio)
from ...texto import fmt_data
from ...validacao import converter_data
from ..tema import COR, botao, fonte
from ..widgets import Cartao, Col, TabelaDados, aplicar_mascara_data, cabecalho_pagina, titulo_secao

_NUMERICOS = {"inteiro", "sinal", "dinheiro"}


class PaginaRelatorios(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.tipo = TIPOS_RELATORIO[0][0]
        self.relatorio: Relatorio | None = None
        self.tabela: TabelaDados | None = None
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        cab, _ = cabecalho_pagina(self, "Relatórios", "Consulte, imprima ou leve os dados para uma planilha.")
        cab.grid(row=0, column=0, columnspan=2, sticky="w", padx=32, pady=(26, 14))

        # ---- lista de relatórios
        lateral = Cartao(self, width=270)
        lateral.grid(row=1, column=0, sticky="ns", padx=(32, 10), pady=(0, 24))
        lateral.grid_propagate(False)
        titulo_secao(lateral, "Escolha o relatório").pack(anchor="w", padx=16, pady=(16, 8))
        self.botoes: dict[str, ctk.CTkButton] = {}
        for chave, titulo, _desc in TIPOS_RELATORIO:
            b = ctk.CTkButton(lateral, text=titulo, anchor="w", height=42, corner_radius=8,
                              font=fonte(14), fg_color="transparent", hover_color=COR.linha,
                              text_color=COR.texto, command=lambda k=chave: self.escolher(k))
            b.pack(fill="x", padx=10, pady=2)
            self.botoes[chave] = b

        # ---- prévia
        direita = Cartao(self)
        direita.grid(row=1, column=1, sticky="nsew", padx=(10, 32), pady=(0, 24))
        direita.columnconfigure(0, weight=1)
        direita.rowconfigure(3, weight=1)
        topo = ctk.CTkFrame(direita, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        topo.columnconfigure(0, weight=1)
        self.titulo = ctk.CTkLabel(topo, text="", font=fonte(19, "bold"), text_color=COR.texto, anchor="w")
        self.titulo.grid(row=0, column=0, sticky="w")
        self.descricao = ctk.CTkLabel(topo, text="", font=fonte(12), text_color=COR.texto_suave,
                                      anchor="w", justify="left", wraplength=640)
        self.descricao.grid(row=1, column=0, sticky="w")
        botoes = ctk.CTkFrame(topo, fg_color="transparent")
        botoes.grid(row=0, column=1, rowspan=2, sticky="e")
        for texto, comando in (("PDF", lambda: self.exportar("pdf")), ("Excel", lambda: self.exportar("xlsx")),
                               ("CSV", lambda: self.exportar("csv"))):
            botao(botoes, f"Exportar {texto}", comando, tipo="secundario", altura=34, largura=104).pack(
                side="left", padx=(6, 0))

        # filtros de período (aparecem só no relatório de movimentações)
        self.periodo = ctk.CTkFrame(direita, fg_color="transparent")
        estilo = dict(width=118, height=34, font=fonte(13), corner_radius=8, border_color=COR.borda,
                      fg_color=COR.cartao)
        ctk.CTkLabel(self.periodo, text="Período:  de", font=fonte(12), text_color=COR.texto_suave).pack(side="left")
        self.data_ini = ctk.CTkEntry(self.periodo, placeholder_text="dd/mm/aaaa", **estilo)
        self.data_ini.pack(side="left", padx=6)
        ctk.CTkLabel(self.periodo, text="até", font=fonte(12), text_color=COR.texto_suave).pack(side="left")
        self.data_fim = ctk.CTkEntry(self.periodo, placeholder_text="dd/mm/aaaa", **estilo)
        self.data_fim.pack(side="left", padx=6)
        for e in (self.data_ini, self.data_fim):
            aplicar_mascara_data(e)
            e.bind("<Return>", lambda _e: self.gerar(), add="+")
        botao(self.periodo, "Gerar", self.gerar, tipo="suave", altura=34, largura=70).pack(side="left", padx=6)
        hoje = date.today()
        self.data_ini.insert(0, fmt_data(hoje - timedelta(days=29)))
        self.data_fim.insert(0, fmt_data(hoje))
        self.periodo.grid(row=1, column=0, sticky="w", padx=18, pady=(4, 0))
        self.periodo.grid_remove()

        self.erro = ctk.CTkLabel(direita, text="", font=fonte(12, "bold"), text_color=COR.perigo, anchor="w")
        self.erro.grid(row=2, column=0, sticky="w", padx=18)
        self.erro.grid_remove()
        self.area_tabela = ctk.CTkFrame(direita, fg_color="transparent")
        self.area_tabela.grid(row=3, column=0, sticky="nsew", padx=1, pady=(6, 0))
        self.area_tabela.columnconfigure(0, weight=1)
        self.area_tabela.rowconfigure(0, weight=1)
        self.resumo = ctk.CTkLabel(direita, text="", font=fonte(13, "bold"), text_color=COR.texto,
                                   anchor="w", justify="left")
        self.resumo.grid(row=4, column=0, sticky="w", padx=18, pady=(10, 14))

    # ------------------------------------------------------------------ ações
    def escolher(self, tipo: str) -> None:
        self.tipo = tipo
        for chave, b in self.botoes.items():
            ativo = chave == tipo
            b.configure(fg_color=COR.primaria_suave if ativo else "transparent",
                        text_color=COR.primaria if ativo else COR.texto,
                        font=fonte(14, "bold" if ativo else "normal"))
        if tipo == REL_MOVIMENTACOES:
            self.periodo.grid()
        else:
            self.periodo.grid_remove()
        self.gerar()

    def atualizar(self) -> None:
        self.escolher(self.tipo)

    def gerar(self) -> None:
        ini = fim = None
        if self.tipo == REL_MOVIMENTACOES:
            try:
                ini, fim = converter_data(self.data_ini.get()), converter_data(self.data_fim.get())
                if ini and fim and ini > fim:
                    raise ValueError("A data inicial não pode ser depois da data final.")
            except ValueError as e:
                self.erro.configure(text=f"Período inválido: {e}")
                self.erro.grid()
                return
        self.erro.grid_remove()
        rel = self.relatorio = self.app.ctx.relatorios.gerar(self.tipo, data_inicio=ini, data_fim=fim)
        descricao = next(d for k, _t, d in TIPOS_RELATORIO if k == self.tipo)
        self.titulo.configure(text=rel.titulo)
        self.descricao.configure(text=f"{descricao}\n{rel.subtitulo}")
        self._montar_tabela(rel)
        self.resumo.configure(text="   ·   ".join(f"{r}: {v}" for r, v in rel.resumo))

    def _montar_tabela(self, rel: Relatorio) -> None:
        if self.tabela is not None:
            self.tabela.destroy()
        colunas = [Col(f"c{i}", c.titulo, int(c.largura * 95) + 40, "e" if c.tipo in _NUMERICOS else "w")
                   for i, c in enumerate(rel.colunas)]
        self.tabela = TabelaDados(self.area_tabela, colunas, altura=12, rolagem_horizontal=True,
                                  mensagem_vazia="Nenhum registro para este relatório.")
        self.tabela.grid(row=0, column=0, sticky="nsew")
        formatadas = rel.linhas_formatadas()
        self.tabela.definir_linhas([{
            "iid": i, "valores": {f"c{j}": v for j, v in enumerate(texto)},
            "ordem": {f"c{j}": bruto for j, bruto in enumerate(rel.linhas[i])}}
            for i, texto in enumerate(formatadas)])

    def exportar(self, formato: str) -> None:
        if self.relatorio is None:
            return
        rel = self.relatorio
        tipos = {"csv": ("CSV (abre no Excel)", "*.csv"), "xlsx": ("Planilha Excel", "*.xlsx"),
                 "pdf": ("Documento PDF", "*.pdf")}
        caminho = filedialog.asksaveasfilename(
            parent=self.app, title=f"Exportar relatório para {formato.upper()}",
            defaultextension=f".{formato}", filetypes=[tipos[formato], ("Todos os arquivos", "*.*")],
            initialfile=f"{self.tipo}_{date.today():%Y-%m-%d}.{formato}")
        if not caminho:
            return
        funcao = {"csv": exportacao.exportar_csv, "xlsx": exportacao.exportar_excel,
                  "pdf": exportacao.exportar_pdf}[formato]
        try:
            funcao(rel, caminho, self.app.ctx.config.nome_farmacia)
        except FarmaciaError as e:
            self.app.mensagem("Não foi possível exportar", str(e), "erro")
        except OSError as e:
            self.app.mensagem("Não foi possível salvar o arquivo",
                              f"{e.strerror or e}\n\nVerifique se o arquivo não está aberto em outro programa.",
                              "erro")
        else:
            self.app.aviso(f"Relatório exportado:\n{caminho}", "ok", 5000)
