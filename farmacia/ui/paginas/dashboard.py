"""Tela inicial: indicadores, medicamentos que exigem atenção e últimas movimentações."""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ...dominio import ALERTA_VENCIDO, ENTRADA
from ...servicos.medicamentos import SIT_BAIXO, SIT_PROXIMO, SIT_VENCIDO
from ...texto import (data_por_extenso, fmt_data, fmt_data_hora, fmt_dinheiro, fmt_inteiro,
                      fmt_sinal, texto_prazo)
from ..tema import COR, botao, fonte
from ..widgets import Cartao, CartaoIndicador, Col, TabelaDados, cabecalho_pagina, titulo_secao


class PaginaDashboard(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        cab, self.subtitulo = cabecalho_pagina(self, "Visão geral", "")
        cab.grid(row=0, column=0, sticky="w", padx=32, pady=(26, 14))

        # ---- boas-vindas (aparece só enquanto não há medicamentos)
        self.boas_vindas = Cartao(self, fg_color=COR.primaria_suave, border_color="#B7DDD7")
        ctk.CTkLabel(self.boas_vindas, text="Bem-vindo! Vamos começar?", font=fonte(17, "bold"),
                     text_color=COR.primaria, anchor="w").pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(self.boas_vindas,
                     text="Ainda não há medicamentos cadastrados. Cadastre o primeiro ou carregue "
                          "alguns dados de demonstração (fictícios) para conhecer o sistema.",
                     font=fonte(13), text_color=COR.texto, anchor="w", justify="left",
                     wraplength=760).pack(anchor="w", padx=20, pady=(4, 10))
        botoes = ctk.CTkFrame(self.boas_vindas, fg_color="transparent")
        botoes.pack(anchor="w", padx=20, pady=(0, 16))
        botao(botoes, "Cadastrar medicamento", lambda: app.abrir_formulario()).pack(side="left")
        botao(botoes, "Adicionar dados de demonstração", app.adicionar_demo, tipo="secundario").pack(
            side="left", padx=10)

        # ---- indicadores
        self.indicadores = ctk.CTkFrame(self, fg_color="transparent")
        self.indicadores.grid(row=2, column=0, sticky="ew", padx=24)
        for c in range(5):
            self.indicadores.columnconfigure(c, weight=1, uniform="ind")
        self.c_total = CartaoIndicador(self.indicadores, "Medicamentos cadastrados", "✚", "info",
                                       lambda: app.navegar("medicamentos"))
        self.c_unidades = CartaoIndicador(self.indicadores, "Produtos em estoque", "▦", "ok",
                                          lambda: app.navegar("estoque"))
        self.c_baixo = CartaoIndicador(self.indicadores, "Estoque baixo", "▼", "aviso",
                                       lambda: app.ver_medicamentos(SIT_BAIXO))
        self.c_venc = CartaoIndicador(self.indicadores, "Próximos do vencimento", "◷", "aviso",
                                      self._abrir_vencimentos)
        self.c_valor = CartaoIndicador(self.indicadores, "Valor aproximado do estoque", "R$", "neutro",
                                       lambda: app.navegar("relatorios"), tamanho_valor=21)
        for i, c in enumerate((self.c_total, self.c_unidades, self.c_baixo, self.c_venc, self.c_valor)):
            c.grid(row=0, column=i, sticky="nsew", padx=8, pady=4)

        # ---- listas de atenção
        ctk.CTkFrame(self, height=6, fg_color="transparent").grid(row=3, column=0)
        meio = ctk.CTkFrame(self, fg_color="transparent")
        meio.grid(row=4, column=0, sticky="nsew", padx=24, pady=(6, 0))
        meio.columnconfigure((0, 1), weight=1, uniform="m")
        meio.rowconfigure(0, weight=1)

        self.t_baixo = TabelaDados(
            self._cartao_lista(meio, 0, "Medicamentos com estoque baixo",
                               lambda: app.ver_medicamentos(SIT_BAIXO)),
            [Col("nome", "Medicamento", 200), Col("estoque", "Atual / mín.", 95, "e"),
             Col("local", "Localização", 215)],
            altura=4, ao_abrir=app.abrir_detalhes, ordenavel=False,
            mensagem_vazia="Nenhum medicamento com estoque baixo.")
        self.t_baixo.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self.t_venc = TabelaDados(
            self._cartao_lista(meio, 1, "Vencidos e próximos do vencimento", self._abrir_vencimentos),
            [Col("nome", "Medicamento", 215), Col("validade", "Validade", 95),
             Col("situacao", "Situação", 140)],
            altura=4, ao_abrir=app.abrir_detalhes, ordenavel=False,
            mensagem_vazia="Nenhum medicamento vencido ou perto de vencer.")
        self.t_venc.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        # ---- últimas movimentações
        inferior = Cartao(self)
        inferior.grid(row=5, column=0, sticky="ew", padx=32, pady=(14, 22))
        cab_inf = ctk.CTkFrame(inferior, fg_color="transparent")
        cab_inf.pack(fill="x", padx=16, pady=(12, 6))
        titulo_secao(cab_inf, "Últimas movimentações do estoque").pack(side="left")
        botao(cab_inf, "Ver histórico completo", lambda: app.navegar("historico"), tipo="suave",
              altura=28).pack(side="right")
        self.t_mov = TabelaDados(
            inferior,
            [Col("data", "Data e hora", 150), Col("nome", "Medicamento", 250),
             Col("tipo", "Tipo", 75), Col("qtd", "Qtd.", 65, "e"),
             Col("estoque", "Estoque", 110, "e"), Col("motivo", "Motivo", 170)],
            altura=5, ao_abrir=lambda iid: app.abrir_detalhes(self._id_do_mov[iid]),
            ordenavel=False, mensagem_vazia="Nenhuma movimentação registrada ainda.")
        self.t_mov.pack(fill="x", padx=6, pady=(0, 8))
        self._id_do_mov: dict[str, int] = {}

    def _cartao_lista(self, master, coluna: int, titulo: str, ver_todos) -> ctk.CTkFrame:
        cartao = Cartao(master)
        cartao.grid(row=0, column=coluna, sticky="nsew", padx=8)
        cab = ctk.CTkFrame(cartao, fg_color="transparent")
        cab.pack(fill="x", padx=16, pady=(12, 6))
        titulo_secao(cab, titulo).pack(side="left")
        botao(cab, "Ver todos", ver_todos, tipo="suave", altura=28, largura=80).pack(side="right")
        return cartao

    def _abrir_vencimentos(self):
        r = self._resumo
        self.app.ver_medicamentos(SIT_PROXIMO if r.proximos_vencimento or not r.vencidos else SIT_VENCIDO)

    # ------------------------------------------------------------------ dados
    def atualizar(self) -> None:
        ctx = self.app.ctx
        hoje = date.today()
        nome = ctx.config.nome_farmacia
        self.subtitulo.configure(text=(f"{nome}  ·  " if nome else "") + data_por_extenso(hoje))
        r = self._resumo = ctx.relatorios.resumo(hoje)

        if r.total_medicamentos == 0:
            self.boas_vindas.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 14))
        else:
            self.boas_vindas.grid_remove()

        self.c_total.definir(fmt_inteiro(r.total_medicamentos), "produtos no cadastro")
        self.c_unidades.definir(fmt_inteiro(r.total_unidades), "unidades disponíveis")
        self.c_baixo.definir(fmt_inteiro(r.estoque_baixo),
                             "abaixo ou no mínimo" if r.estoque_baixo else "tudo em ordem",
                             COR.aviso if r.estoque_baixo else COR.ok)
        detalhe = f"prazo de alerta: {r.dias_alerta} dias"
        cor = None
        if r.vencidos:
            detalhe = f"{fmt_inteiro(r.vencidos)} já vencido(s)\n{detalhe}"
            cor = COR.perigo
        self.c_venc.definir(fmt_inteiro(r.proximos_vencimento), detalhe, cor)
        self.c_valor.definir(fmt_dinheiro(r.valor_custo_centavos),
                             f"venda: {fmt_dinheiro(r.valor_venda_centavos)}")

        baixos = ctx.relatorios.lista_estoque_baixo(limite=30, hoje=hoje)
        self.t_baixo.definir_linhas([{
            "iid": m.id, "tag": "vencido" if m.quantidade_atual == 0 else "baixo",
            "valores": {"nome": m.rotulo,
                        "estoque": f"{fmt_inteiro(m.quantidade_atual)} / {fmt_inteiro(m.estoque_minimo)}",
                        "local": m.localizacao_curta},
            "ordem": {"estoque": m.quantidade_atual}} for m in baixos])

        venc = ctx.relatorios.lista_vencimentos(limite=30, hoje=hoje)
        self.t_venc.definir_linhas([{
            "iid": m.id, "tag": "vencido" if ALERTA_VENCIDO in m.alertas(hoje, r.dias_alerta) else "proximo",
            "valores": {"nome": m.rotulo, "validade": fmt_data(m.data_validade),
                        "situacao": texto_prazo(m.dias_para_vencer(hoje)).capitalize()}}
            for m in venc])

        movs = ctx.estoque.ultimas(5)
        self._id_do_mov = {str(m.id): m.medicamento_id for m in movs}
        self.t_mov.definir_linhas([{
            "iid": m.id, "tag": "entrada" if m.tipo == ENTRADA else "saida",
            "valores": {"data": fmt_data_hora(m.data_hora), "nome": m.medicamento,
                        "tipo": m.rotulo_tipo, "qtd": fmt_sinal(m.quantidade_com_sinal),
                        "estoque": f"{fmt_inteiro(m.estoque_anterior)} → {fmt_inteiro(m.estoque_posterior)}",
                        "motivo": m.motivo}} for m in movs])
