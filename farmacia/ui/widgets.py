"""Componentes visuais reutilizáveis (cartões, tabela ordenável, campo de busca, avisos)."""
from __future__ import annotations

import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable

import customtkinter as ctk

from ..texto import normalizar
from .tema import COR, ESTILO_BADGE, botao, escala_de, fonte


# ---------------------------------------------------------------------- cartão
class Cartao(ctk.CTkFrame):
    """Painel branco com borda suave, usado para agrupar informações."""

    def __init__(self, master, **kw):
        kw.setdefault("fg_color", COR.cartao)
        kw.setdefault("corner_radius", 12)
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", COR.borda)
        super().__init__(master, **kw)


def cabecalho_pagina(master, titulo: str, subtitulo: str = "") -> tuple[ctk.CTkFrame, ctk.CTkLabel]:
    """Título grande da página. Devolve (frame, rótulo do subtítulo) para poder atualizá-lo."""
    quadro = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(quadro, text=titulo, font=fonte(24, "bold"), text_color=COR.texto,
                 anchor="w").pack(anchor="w")
    sub = ctk.CTkLabel(quadro, text=subtitulo, font=fonte(13), text_color=COR.texto_suave, anchor="w")
    sub.pack(anchor="w", pady=(2, 0))
    return quadro, sub


def titulo_secao(master, texto: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto, font=fonte(15, "bold"), text_color=COR.texto, anchor="w")


class Selo(ctk.CTkFrame):
    """Etiqueta colorida arredondada (ex.: 'Estoque baixo')."""

    def __init__(self, master, texto: str, estilo: str = "neutro", **kw):
        cor_texto, cor_fundo = ESTILO_BADGE[estilo]
        super().__init__(master, fg_color=cor_fundo, corner_radius=10, **kw)
        ctk.CTkLabel(self, text=texto, font=fonte(12, "bold"), text_color=cor_texto,
                     fg_color="transparent", height=24).pack(padx=10)


def tornar_clicavel(widget, comando: Callable[[], None]) -> None:
    """Faz o widget e tudo o que há dentro dele responder ao clique."""
    def _clique(_e=None):
        comando()

    def _aplicar(w):
        try:
            w.bind("<Button-1>", _clique, add="+")
            w.configure(cursor="hand2")
        except (tk.TclError, ValueError, NotImplementedError):
            pass
        for filho in w.winfo_children():
            _aplicar(filho)
    _aplicar(widget)


class CartaoIndicador(Cartao):
    """Cartão do dashboard: título, número grande com ícone e uma linha de detalhe."""

    def __init__(self, master, titulo: str, icone: str, estilo: str = "info",
                 comando: Callable[[], None] | None = None, tamanho_valor: int = 26):
        super().__init__(master)
        self._tamanho_valor = tamanho_valor
        cor_texto, cor_fundo = ESTILO_BADGE[estilo]
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=icone, width=32, height=32, corner_radius=16, fg_color=cor_fundo,
                     text_color=cor_texto, font=fonte(13, "bold")).grid(
            row=0, column=0, sticky="nw", padx=(14, 8), pady=(14, 0))
        ctk.CTkLabel(self, text=titulo, font=fonte(12, "bold"), text_color=COR.texto_suave,
                     anchor="nw", justify="left", wraplength=112, height=34).grid(
            row=0, column=1, sticky="nw", padx=(0, 10), pady=(14, 0))
        self.valor = ctk.CTkLabel(self, text="0", font=fonte(tamanho_valor, "bold"),
                                  text_color=COR.texto, anchor="w")
        self.valor.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 0))
        self.detalhe = ctk.CTkLabel(self, text="", font=fonte(12), text_color=COR.texto_suave,
                                    anchor="nw", justify="left", wraplength=156, height=32)
        self.detalhe.grid(row=2, column=0, columnspan=2, sticky="nw", padx=16, pady=(0, 12))
        if comando:
            tornar_clicavel(self, comando)

    def definir(self, valor: str, detalhe: str = "", cor_detalhe: str | None = None) -> None:
        tamanho = self._tamanho_valor if len(valor) <= 11 else max(15, self._tamanho_valor - 5)
        self.valor.configure(text=valor, font=fonte(tamanho, "bold"))
        self.detalhe.configure(text=detalhe, text_color=cor_detalhe or COR.texto_suave)


class SeletorSegmentado(ctk.CTkFrame):
    """Grupo de botões lado a lado, onde um fica destacado (ex.: Entrada | Saída)."""

    def __init__(self, master, valores: list[str], comando: Callable[[str], None] | None = None,
                 cor: str = COR.primaria, cor_hover: str = COR.primaria_hover, altura: int = 40):
        super().__init__(master, fg_color=COR.linha, corner_radius=10)
        self.valores = valores
        self._valor = valores[0]
        self._comando = comando
        self._cor, self._cor_hover = cor, cor_hover
        self._habilitado = True
        self._botoes: dict[str, ctk.CTkButton] = {}
        for v in valores:
            b = ctk.CTkButton(self, text=v, height=altura - 8, corner_radius=8, font=fonte(13, "bold"),
                              command=lambda v=v: self._clicou(v), text_color_disabled="#9FB0AD")
            b.pack(side="left", fill="x", expand=True, padx=4, pady=4)
            self._botoes[v] = b
        self._pintar()

    def get(self) -> str:
        return self._valor

    def set(self, valor: str) -> None:
        self._valor = valor
        self._pintar()

    def definir_cor(self, cor: str, cor_hover: str) -> None:
        self._cor, self._cor_hover = cor, cor_hover
        self._pintar()

    def definir_habilitado(self, habilitado: bool) -> None:
        self._habilitado = habilitado
        for b in self._botoes.values():
            b.configure(state="normal" if habilitado else "disabled")
        self._pintar()

    def _clicou(self, valor: str) -> None:
        self.set(valor)
        if self._comando:
            self._comando(valor)

    def _pintar(self) -> None:
        for v, b in self._botoes.items():
            sel = v == self._valor
            b.configure(fg_color=(self._cor if self._habilitado else "#B8C7C4") if sel else "transparent",
                        hover_color=self._cor_hover if sel else COR.borda,
                        text_color="#FFFFFF" if sel else COR.texto)


# ------------------------------------------------------------------ campo de busca
class CampoBusca(ctk.CTkFrame):
    """Caixa de pesquisa com atraso (a lista só atualiza quando a pessoa para de digitar)."""

    def __init__(self, master, placeholder: str, ao_mudar: Callable[[str], None], atraso_ms: int = 250):
        super().__init__(master, fg_color="transparent")
        self._ao_mudar = ao_mudar
        self._atraso = atraso_ms
        self._agendado = None
        self.columnconfigure(0, weight=1)
        self.entrada = ctk.CTkEntry(self, placeholder_text=placeholder, height=40, corner_radius=10,
                                    border_color=COR.borda, fg_color=COR.cartao,
                                    font=fonte(14), text_color=COR.texto)
        self.entrada.grid(row=0, column=0, sticky="ew")
        self.limpar_btn = ctk.CTkButton(self, text="✕", width=30, height=30, corner_radius=15,
                                        fg_color="transparent", hover_color=COR.linha,
                                        text_color=COR.texto_suave, command=self.limpar)
        self.entrada.bind("<KeyRelease>", self._tecla, add="+")

    def _tecla(self, _evento=None):
        if self.entrada.get():
            self.limpar_btn.place(in_=self.entrada, relx=1.0, x=-8, rely=0.5, anchor="e")
        else:
            self.limpar_btn.place_forget()
        if self._agendado:
            self.after_cancel(self._agendado)
        self._agendado = self.after(self._atraso, self._disparar)

    def _disparar(self):
        self._agendado = None
        self._ao_mudar(self.entrada.get())

    def texto(self) -> str:
        return self.entrada.get()

    def definir(self, texto: str, disparar: bool = True) -> None:
        if texto:
            self.entrada.delete(0, "end")
            self.entrada.insert(0, texto)
        else:
            limpar_entrada(self.entrada)
        self._tecla()
        if disparar:
            if self._agendado:
                self.after_cancel(self._agendado)
                self._agendado = None
            self._ao_mudar(texto)

    def limpar(self):
        self.definir("")
        self.entrada.focus_set()

    def focar(self):
        self.entrada.focus_set()


def limpar_entrada(entrada: ctk.CTkEntry) -> None:
    """Apaga o campo e mostra de novo o texto de exemplo (placeholder), se houver."""
    entrada.delete(0, "end")
    try:
        entrada._activate_placeholder()
    except Exception:
        pass


def aplicar_mascara_data(entrada: ctk.CTkEntry) -> None:
    """Digitar 19092026 vira 19/09/2026 automaticamente."""
    def _formatar(evento):
        if evento.keysym in ("BackSpace", "Delete", "Left", "Right", "Home", "End", "Tab",
                             "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        digitos = re.sub(r"\D", "", entrada.get())[:8]
        partes = [digitos[:2], digitos[2:4], digitos[4:8]]
        texto = "/".join(p for p in partes if p)
        if len(digitos) in (2, 4):
            texto += "/"
        if texto != entrada.get():
            entrada.delete(0, "end")
            entrada.insert(0, texto)
    entrada.bind("<KeyRelease>", _formatar, add="+")


# -------------------------------------------------------------------------- tabela
@dataclass
class Col:
    chave: str
    titulo: str
    largura: int = 100
    alinhar: str = "w"        # w (esquerda) | e (direita) | center


class TabelaDados(ctk.CTkFrame):
    """Tabela com ordenação por clique no título, linhas coloridas e seleção.

    Cada linha é um dicionário:
        {"iid": "12", "valores": {"nome": "..."}, "ordem": {"estoque": 35}, "tag": "vencido"}
    `ordem` é opcional e define como ordenar colunas numéricas ou de data.
    """

    def __init__(self, master, colunas: list[Col], *, altura: int = 8,
                 ao_selecionar: Callable[[str | None], None] | None = None,
                 ao_abrir: Callable[[str], None] | None = None,
                 ao_menu: Callable[[Any, str], None] | None = None,
                 ordenavel: bool = True, mensagem_vazia: str = "Nenhum registro encontrado.",
                 rolagem_horizontal: bool = False):
        super().__init__(master, fg_color=COR.cartao, corner_radius=0)
        self.colunas = colunas
        self._ao_selecionar = ao_selecionar
        self._ao_abrir = ao_abrir
        self._ao_menu = ao_menu
        self._ordenavel = ordenavel
        self._horizontal = rolagem_horizontal
        self._ordem: tuple[str, bool] | None = None
        self._linhas: list[dict] = []
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.arvore = ttk.Treeview(self, columns=[c.chave for c in colunas], show="headings",
                                   selectmode="browse", height=altura, style="Farma.Treeview")
        self.rolagem = ttk.Scrollbar(self, orient="vertical", command=self.arvore.yview,
                                     style="Farma.Vertical.TScrollbar")
        self.arvore.configure(yscrollcommand=self._ao_rolar)
        self.arvore.grid(row=0, column=0, sticky="nsew")
        self._rolagem_visivel = False
        if rolagem_horizontal:
            barra_h = ttk.Scrollbar(self, orient="horizontal", command=self.arvore.xview,
                                    style="Farma.Horizontal.TScrollbar")
            self.arvore.configure(xscrollcommand=barra_h.set)
            barra_h.grid(row=1, column=0, sticky="ew")

        for tag, cor in (("vencido", COR.linha_vencido), ("baixo", COR.linha_baixo),
                         ("proximo", COR.linha_proximo), ("par", COR.cartao),
                         ("impar", COR.linha_par)):
            self.arvore.tag_configure(tag, background=cor)
        self.arvore.tag_configure("entrada", foreground=COR.entrada)
        self.arvore.tag_configure("saida", foreground=COR.saida)

        self.vazio = ctk.CTkLabel(self, text=mensagem_vazia, font=fonte(13),
                                  text_color=COR.texto_suave, fg_color=COR.cartao)
        self._configurar_colunas()

        self.arvore.bind("<<TreeviewSelect>>", self._selecionou)
        self.arvore.bind("<Double-1>", self._duplo_clique)
        self.arvore.bind("<Return>", lambda e: self._abrir_selecionado())
        self.arvore.bind("<Button-3>", self._menu)
        self.arvore.bind("<Button-2>", self._menu)

    # -- configuração ---------------------------------------------------------
    def _configurar_colunas(self):
        """Larguras em pixels. Nas tabelas normais todas as colunas são elásticas: dividem a
        largura disponível e encolhem (até 60% da largura) quando o espaço é pequeno.
        Com rolagem horizontal (relatórios largos) as colunas mantêm a largura fixa."""
        esc = escala_de(self)
        for c in self.colunas:
            if self._horizontal:
                self.arvore.column(c.chave, width=int(c.largura * esc), minwidth=int(c.largura * esc),
                                   anchor=c.alinhar, stretch=False)
            else:
                self.arvore.column(c.chave, width=int(c.largura * esc),
                                   minwidth=int(max(45, c.largura * 0.6) * esc),
                                   anchor=c.alinhar, stretch=True)
        self._atualizar_titulos()

    def _atualizar_titulos(self):
        for c in self.colunas:
            texto = c.titulo
            if self._ordem and self._ordem[0] == c.chave:
                texto += "  ▼" if self._ordem[1] else "  ▲"
            comando = (lambda k=c.chave: self._ordenar_por(k)) if self._ordenavel else ""
            self.arvore.heading(c.chave, text=texto, anchor="w" if c.alinhar == "w" else c.alinhar,
                                command=comando)

    def _ao_rolar(self, inicio, fim):
        """Mostra a barra de rolagem só quando existem linhas fora da área visível."""
        self.rolagem.set(inicio, fim)
        precisa = float(inicio) > 0.0 or float(fim) < 1.0
        if precisa and not self._rolagem_visivel:
            self.rolagem.grid(row=0, column=1, sticky="ns")
            self._rolagem_visivel = True
        elif not precisa and self._rolagem_visivel:
            self.rolagem.grid_remove()
            self._rolagem_visivel = False

    # -- dados --------------------------------------------------------------------
    def definir_linhas(self, linhas: list[dict]) -> None:
        anterior = self.selecionado()
        self._linhas = list(linhas)
        self._renderizar()
        if anterior and self.arvore.exists(anterior):
            self.arvore.selection_set(anterior)
            self.arvore.see(anterior)
        elif anterior:
            self._notificar(None)

    def _renderizar(self) -> None:
        linhas = self._linhas
        if self._ordem:
            chave, decrescente = self._ordem
            linhas = sorted(linhas, key=lambda l: self._chave_ordem(l, chave), reverse=decrescente)
        self.arvore.delete(*self.arvore.get_children())
        for i, linha in enumerate(linhas):
            valores = [linha["valores"].get(c.chave, "") for c in self.colunas]
            tag = linha.get("tag") or ("par" if i % 2 == 0 else "impar")
            self.arvore.insert("", "end", iid=str(linha["iid"]), values=valores, tags=(tag,))
        if self._linhas:
            self.vazio.place_forget()
        else:
            self.vazio.place(relx=0.5, rely=0.5, anchor="center")

    @staticmethod
    def _chave_ordem(linha: dict, chave: str):
        valor = linha.get("ordem", {}).get(chave, linha["valores"].get(chave, ""))
        if valor is None or valor == "":
            return (1, 0)
        if isinstance(valor, str):
            return (0, normalizar(valor))
        return (0, valor)

    def _ordenar_por(self, chave: str) -> None:
        if self._ordem and self._ordem[0] == chave:
            self._ordem = (chave, not self._ordem[1])
        else:
            self._ordem = (chave, False)
        self._atualizar_titulos()
        selecionado = self.selecionado()
        self._renderizar()
        if selecionado and self.arvore.exists(selecionado):
            self.arvore.selection_set(selecionado)
            self.arvore.see(selecionado)

    def selecionado(self) -> str | None:
        sel = self.arvore.selection()
        return sel[0] if sel else None

    def limpar_selecao(self) -> None:
        self.arvore.selection_remove(self.arvore.selection())

    def selecionar(self, iid: str) -> None:
        if self.arvore.exists(iid):
            self.arvore.selection_set(iid)
            self.arvore.see(iid)

    def quantidade(self) -> int:
        return len(self._linhas)

    # -- eventos ------------------------------------------------------------------
    def _notificar(self, iid):
        if self._ao_selecionar:
            self._ao_selecionar(iid)

    def _selecionou(self, _e=None):
        self._notificar(self.selecionado())

    def _duplo_clique(self, evento):
        if self.arvore.identify_region(evento.x, evento.y) != "cell":
            return
        iid = self.arvore.identify_row(evento.y)
        if iid and self._ao_abrir:
            self._ao_abrir(iid)

    def _abrir_selecionado(self):
        iid = self.selecionado()
        if iid and self._ao_abrir:
            self._ao_abrir(iid)

    def _menu(self, evento):
        iid = self.arvore.identify_row(evento.y)
        if iid and self._ao_menu:
            self.arvore.selection_set(iid)
            self._ao_menu(evento, iid)


# --------------------------------------------------------------------------- aviso
class Aviso(ctk.CTkFrame):
    """Mensagem rápida no canto inferior direito ("Entrada registrada!"), some sozinha."""

    def __init__(self, master):
        super().__init__(master, corner_radius=10, border_width=1)
        self._rotulo = ctk.CTkLabel(self, text="", font=fonte(13, "bold"), justify="left",
                                    wraplength=420)
        self._rotulo.pack(padx=18, pady=12)
        self._agendado = None

    def mostrar(self, mensagem: str, tipo: str = "ok", ms: int = 3500) -> None:
        cor_texto, cor_fundo = ESTILO_BADGE.get(tipo, ESTILO_BADGE["ok"])
        self.configure(fg_color=cor_fundo, border_color=cor_texto)
        self._rotulo.configure(text=mensagem, text_color=cor_texto)
        self.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
        self.lift()
        if self._agendado:
            self.after_cancel(self._agendado)
        self._agendado = self.after(ms, self.esconder)

    def esconder(self):
        self._agendado = None
        self.place_forget()


def linha_info(master, linha: int, rotulo: str, valor: str, *, destaque: bool = False,
               cor: str | None = None, coluna: int = 0, largura_rotulo: int = 130) -> ctk.CTkLabel:
    """Par 'rótulo: valor' em duas colunas de um grid (usado nos detalhes)."""
    ctk.CTkLabel(master, text=rotulo, font=fonte(12), text_color=COR.texto_suave, anchor="nw",
                 width=largura_rotulo, height=20).grid(row=linha, column=coluna, sticky="nw",
                                                       padx=(16, 8), pady=(5, 1))
    lbl = ctk.CTkLabel(master, text=valor or "—", font=fonte(14 if destaque else 13,
                                                              "bold" if destaque else "normal"),
                       text_color=cor or COR.texto, anchor="w", justify="left", wraplength=250,
                       height=20)
    lbl.grid(row=linha, column=coluna + 1, sticky="nw", padx=(0, 16), pady=(4, 1))
    return lbl
