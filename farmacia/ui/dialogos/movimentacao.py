"""Registro de entrada e saída de estoque (formulário reutilizável + janela)."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ...config import MOTIVOS_ENTRADA, MOTIVOS_SAIDA
from ...dominio import ENTRADA, SAIDA, FarmaciaError, Medicamento, Movimentacao
from ...texto import codigo, fmt_inteiro, unidades
from ...validacao import converter_inteiro
from ..tema import COR, botao, fonte
from ..widgets import Cartao, SeletorSegmentado, limpar_entrada
from .base import Dialogo

_ROTULO_TIPO = {"Entrada": ENTRADA, "Saída": SAIDA}


class FormularioMovimentacao(ctk.CTkFrame):
    """Escolha entrada/saída, quantidade, motivo e confirme. Mostra o novo estoque antes de gravar."""

    def __init__(self, master, app, *, tipo_inicial: str = ENTRADA, compacto: bool = False,
                 ao_concluir: Callable[[Movimentacao], None] | None = None):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.medicamento: Medicamento | None = None
        self.ao_concluir = ao_concluir
        self.tipo = tipo_inicial
        self.columnconfigure((0, 1), weight=1, uniform="mov")

        self.seletor = SeletorSegmentado(self, ["Entrada", "Saída"], self._trocar_tipo,
                                         cor=COR.entrada, cor_hover=COR.entrada_hover, altura=44)
        self.seletor.grid(row=0, column=0, columnspan=2, sticky="ew")

        ctk.CTkLabel(self, text="Quantidade", font=fonte(12), text_color=COR.texto_suave,
                     anchor="w").grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 2))
        self.quantidade = ctk.CTkEntry(self, height=42, font=fonte(18, "bold"), corner_radius=8,
                                       border_color=COR.borda, fg_color=COR.cartao,
                                       placeholder_text="Ex.: 30")
        self.quantidade.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.quantidade.bind("<KeyRelease>", self._atualizar_previa, add="+")
        self.quantidade.bind("<Return>", lambda _e: self.confirmar(), add="+")

        self.previa = ctk.CTkLabel(self, text="", font=fonte(14), text_color=COR.texto_suave,
                                   anchor="w", justify="left", wraplength=380)
        self.previa.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # lado a lado no modo compacto (tela de Estoque); empilhados na janela estreita
        col_obs, span_motivo = (1, 1) if compacto else (0, 2)
        lin_obs = 4 if compacto else 6
        ctk.CTkLabel(self, text="Motivo", font=fonte(12), text_color=COR.texto_suave,
                     anchor="w").grid(row=4, column=0, columnspan=span_motivo, sticky="w", pady=(10, 2))
        self.motivo = ctk.CTkOptionMenu(
            self, values=MOTIVOS_ENTRADA, height=36, font=fonte(13), dropdown_font=fonte(13),
            fg_color=COR.cartao, button_color=COR.borda, button_hover_color="#C5D3D0",
            text_color=COR.texto, dropdown_text_color=COR.texto, dropdown_fg_color=COR.cartao,
            dropdown_hover_color=COR.primaria_suave, anchor="w")
        self.motivo.grid(row=5, column=0, columnspan=span_motivo, sticky="ew",
                         padx=(0, 6) if compacto else 0)

        ctk.CTkLabel(self, text="Observação (opcional)", font=fonte(12), text_color=COR.texto_suave,
                     anchor="w").grid(row=lin_obs, column=col_obs, columnspan=span_motivo, sticky="w",
                                      pady=(10, 2), padx=(6, 0) if compacto else 0)
        self.observacao = ctk.CTkEntry(self, height=36, font=fonte(13), corner_radius=8,
                                       border_color=COR.borda, fg_color=COR.cartao,
                                       placeholder_text="Ex.: nota fiscal 1234")
        self.observacao.grid(row=lin_obs + 1, column=col_obs, columnspan=span_motivo, sticky="ew",
                             padx=(6, 0) if compacto else 0)
        self.observacao.bind("<Return>", lambda _e: self.confirmar(), add="+")

        self.erro = ctk.CTkLabel(self, text="", font=fonte(13, "bold"), text_color=COR.perigo,
                                 anchor="w", justify="left", wraplength=380)
        self.erro.grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.botao_confirmar = botao(self, "Registrar entrada", self.confirmar, tipo="entrada",
                                     altura=42)
        self.botao_confirmar.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.seletor.set("Entrada" if tipo_inicial == ENTRADA else "Saída")
        self._trocar_tipo(self.seletor.get())
        self.definir_medicamento(None)

    # ------------------------------------------------------------------ estado
    def definir_medicamento(self, med: Medicamento | None, manter_tipo: bool = True) -> None:
        self.medicamento = med
        for campo in (self.quantidade, self.observacao):
            campo.configure(state="normal")               # campo desabilitado ignora delete()
            limpar_entrada(campo)
        self._mostrar_erro("")
        estado = "normal" if med else "disabled"
        for w in (self.quantidade, self.observacao):
            w.configure(state=estado)
        self.motivo.configure(state=estado)
        self.seletor.definir_habilitado(med is not None)
        self.botao_confirmar.configure(state=estado)
        self._atualizar_previa()

    def escolher_tipo(self, tipo: str) -> None:
        self.seletor.set("Entrada" if tipo == ENTRADA else "Saída")
        self._trocar_tipo(self.seletor.get())

    def focar_quantidade(self) -> None:
        self.quantidade.focus_set()

    def _trocar_tipo(self, rotulo: str) -> None:
        self.tipo = _ROTULO_TIPO[rotulo]
        if self.tipo == ENTRADA:
            self.motivo.configure(values=MOTIVOS_ENTRADA)
            self.motivo.set(MOTIVOS_ENTRADA[0])
            self.seletor.definir_cor(COR.entrada, COR.entrada_hover)
            self.botao_confirmar.configure(text="Registrar entrada", fg_color=COR.entrada,
                                           hover_color=COR.entrada_hover)
        else:
            self.motivo.configure(values=MOTIVOS_SAIDA)
            self.motivo.set(MOTIVOS_SAIDA[0])
            self.seletor.definir_cor(COR.saida, COR.saida_hover)
            self.botao_confirmar.configure(text="Registrar saída", fg_color=COR.saida,
                                           hover_color=COR.saida_hover)
        self._mostrar_erro("")
        self._atualizar_previa()

    def _mostrar_erro(self, texto: str) -> None:
        self.erro.configure(text=texto)
        self.quantidade.configure(border_color=COR.perigo if texto else COR.borda)

    def _atualizar_previa(self, _evento=None) -> None:
        if not self.medicamento:
            self.previa.configure(text="")
            return
        atual = self.medicamento.quantidade_atual
        try:
            qtd = converter_inteiro(self.quantidade.get(), obrigatorio=True, minimo=1)
        except ValueError:
            self.previa.configure(text=f"Estoque atual: {fmt_inteiro(atual)}", text_color=COR.texto_suave)
            return
        if self.tipo == SAIDA and qtd > atual:
            self.previa.configure(
                text=f"Estoque insuficiente: há apenas {unidades(atual)}.", text_color=COR.perigo)
            return
        novo = atual + qtd if self.tipo == ENTRADA else atual - qtd
        sinal = "+" if self.tipo == ENTRADA else "−"
        self.previa.configure(
            text=f"Estoque atual: {fmt_inteiro(atual)}   {sinal}{fmt_inteiro(qtd)}   →   "
                 f"Novo estoque: {fmt_inteiro(novo)}",
            text_color=COR.entrada if self.tipo == ENTRADA else COR.saida)

    # --------------------------------------------------------------- confirmar
    def confirmar(self) -> None:
        if not self.medicamento:
            return
        try:
            qtd = converter_inteiro(self.quantidade.get(), obrigatorio=True, minimo=1)
        except ValueError as e:
            self._mostrar_erro(str(e))
            self.quantidade.focus_set()
            return
        try:
            mov = self.app.ctx.estoque.registrar_movimentacao(
                self.medicamento.id, self.tipo, qtd, self.motivo.get(), self.observacao.get())
        except FarmaciaError as e:
            self._mostrar_erro(str(e))
            self.quantidade.focus_set()
            return
        verbo = "Entrada" if self.tipo == ENTRADA else "Saída"
        self.app.aviso(f"{verbo} registrada: {self.medicamento.rotulo}\n"
                       f"Novo estoque: {fmt_inteiro(mov.estoque_posterior)}", "ok")
        self.app.dados_alterados()
        if self.ao_concluir:
            self.ao_concluir(mov)


class DialogoMovimentacao(Dialogo):
    """Janela para dar entrada ou saída em um medicamento específico."""

    def __init__(self, app, medicamento_id: int, tipo: str = ENTRADA):
        med = app.ctx.medicamentos.obter(medicamento_id)
        super().__init__(app, "Movimentação de estoque", 460, 660)
        self.medicamento = med
        cartao = Cartao(self)
        cartao.pack(fill="x", padx=22, pady=(22, 10))
        ctk.CTkLabel(cartao, text=med.rotulo, font=fonte(17, "bold"), text_color=COR.texto,
                     anchor="w", justify="left", wraplength=380).pack(anchor="w", padx=18, pady=(14, 0))
        ctk.CTkLabel(cartao, text=f"Código {codigo(med.id)}  ·  {med.principio_ativo}",
                     font=fonte(12), text_color=COR.texto_suave, anchor="w").pack(anchor="w", padx=18)
        ctk.CTkLabel(cartao, text=f"Local: {med.localizacao}", font=fonte(12),
                     text_color=COR.texto_suave, anchor="w").pack(anchor="w", padx=18, pady=(0, 2))
        ctk.CTkLabel(cartao, text=f"Estoque atual: {unidades(med.quantidade_atual)}",
                     font=fonte(15, "bold"), text_color=COR.primaria, anchor="w").pack(
            anchor="w", padx=18, pady=(4, 14))

        self.formulario = FormularioMovimentacao(self, app, tipo_inicial=tipo,
                                                 ao_concluir=lambda _m: self.fechar())
        self.formulario.pack(fill="x", padx=22)
        self.formulario.definir_medicamento(med)
        self.formulario.escolher_tipo(tipo)
        botao(self, "Cancelar", self.fechar, tipo="secundario").pack(fill="x", padx=22, pady=(10, 20))
        self.exibir()
        self.after(150, self.formulario.focar_quantidade)
