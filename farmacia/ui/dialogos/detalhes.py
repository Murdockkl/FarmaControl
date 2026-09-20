"""Detalhes de um medicamento: tudo em uma só tela, com a localização em destaque."""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

from ...dominio import (ALERTA_VENCIDO, ENTRADA, ROTULO_ALERTA, SAIDA)
from ...texto import (codigo, fmt_data, fmt_data_hora, fmt_dinheiro, fmt_inteiro,
                      texto_prazo, unidades)
from ..tema import BADGE_DO_ALERTA, COR, botao, fonte
from ..widgets import Cartao, Selo, linha_info, titulo_secao
from .base import Dialogo


class DialogoDetalhes(Dialogo):
    def __init__(self, app, medicamento_id: int):
        super().__init__(app, "Detalhes do medicamento", 960, 800, redimensionavel=True)
        self.medicamento_id = medicamento_id
        self.minsize(820, 560)
        self._ouvinte = self.recarregar
        app.ouvintes.append(self._ouvinte)

        rodape = ctk.CTkFrame(self, fg_color=COR.cartao, corner_radius=0)
        rodape.pack(side="bottom", fill="x")
        botao(rodape, "Fechar", self.fechar, tipo="secundario", largura=100, altura=40).pack(
            side="right", padx=(8, 26), pady=14)
        botao(rodape, "Editar", lambda: app.abrir_formulario(self.medicamento_id),
              tipo="primario", largura=120, altura=40).pack(side="left", padx=(26, 8), pady=14)
        botao(rodape, "Entrada", lambda: app.abrir_movimentacao(self.medicamento_id, ENTRADA),
              tipo="entrada", largura=120, altura=40).pack(side="left", padx=8, pady=14)
        botao(rodape, "Saída", lambda: app.abrir_movimentacao(self.medicamento_id, SAIDA),
              tipo="saida", largura=120, altura=40).pack(side="left", padx=8, pady=14)

        self.rolagem = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rolagem.pack(fill="both", expand=True, padx=(18, 10))
        self.recarregar()
        self.exibir()

    def ao_fechar(self) -> None:
        if self._ouvinte in self.app.ouvintes:
            self.app.ouvintes.remove(self._ouvinte)

    # ------------------------------------------------------------------ conteúdo
    def recarregar(self) -> None:
        """Redesenha a tela com os dados atuais (chamado após entrada, saída ou edição)."""
        ctx = self.app.ctx
        med = ctx.medicamentos.obter(self.medicamento_id)
        if med is None:                                   # foi excluído
            self.fechar()
            return
        for w in self.rolagem.winfo_children():
            w.destroy()
        hoje = date.today()
        dias = ctx.config.dias_alerta
        alertas = med.alertas(hoje, dias)
        self.title(f"Detalhes: {med.rotulo}")

        # ---- título e selos
        topo = ctk.CTkFrame(self.rolagem, fg_color="transparent")
        topo.pack(fill="x", padx=8, pady=(10, 4))
        ctk.CTkLabel(topo, text=med.rotulo.upper(), font=fonte(24, "bold"), text_color=COR.texto,
                     anchor="w", justify="left", wraplength=820).pack(anchor="w")
        selos = ctk.CTkFrame(topo, fg_color="transparent")
        selos.pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(selos, text=f"Código {codigo(med.id)}", font=fonte(12),
                     text_color=COR.texto_suave).pack(side="left", padx=(0, 10))
        if med.eh_generico:
            Selo(selos, "Genérico", "info").pack(side="left", padx=(0, 6))
        for a in alertas:
            Selo(selos, ROTULO_ALERTA[a], BADGE_DO_ALERTA[a]).pack(side="left", padx=(0, 6))
        if not alertas:
            Selo(selos, "Situação normal", "ok").pack(side="left")
        if med.demo:
            Selo(selos, "Dado fictício de demonstração", "neutro").pack(side="left", padx=(6, 0))

        # ---- localização em destaque
        faixa = ctk.CTkFrame(self.rolagem, fg_color=COR.primaria, corner_radius=12)
        faixa.pack(fill="x", padx=8, pady=(10, 6))
        ctk.CTkLabel(faixa, text="Onde encontrar", font=fonte(12), text_color="#BFE6E1",
                     anchor="w").pack(anchor="w", padx=20, pady=(12, 0))
        ctk.CTkLabel(faixa, text=med.localizacao, font=fonte(20, "bold"), text_color="#FFFFFF",
                     anchor="w").pack(anchor="w", padx=20)
        extra = " · ".join(p for p in (f"Setor {med.setor}" if med.setor else "",
                                       f"Gaveta {med.gaveta}" if med.gaveta and med.corredor else "")
                           if p)
        if extra:
            ctk.CTkLabel(faixa, text=extra, font=fonte(13), text_color="#D7F0EC",
                         anchor="w").pack(anchor="w", padx=20)
        ctk.CTkFrame(faixa, height=8, fg_color="transparent").pack()

        # ---- grade de cartões
        grade = ctk.CTkFrame(self.rolagem, fg_color="transparent")
        grade.pack(fill="x", padx=0)
        grade.columnconfigure((0, 1), weight=1, uniform="c")

        c1 = self._cartao(grade, "Identificação", 0, 0)
        linhas = [("Princípio ativo", med.principio_ativo, True),
                  ("Genérico", "Sim" if med.eh_generico else "Não", False),
                  ("Nome genérico", med.nome_generico, False),
                  ("Laboratório", med.laboratorio, False), ("Categoria", med.categoria, False),
                  ("Dosagem", med.dosagem_completa, False),
                  ("Forma farmacêutica", med.forma_farmaceutica, False)]
        for i, (r, v, d) in enumerate(linhas):
            linha_info(c1, i, r, v, destaque=d)
        ctk.CTkFrame(c1, height=8, fg_color="transparent").grid(row=len(linhas), column=0)

        c2 = self._cartao(grade, "Estoque", 0, 1)
        cor_estoque = COR.perigo if any(a in ("sem_estoque",) for a in alertas) else (
            COR.aviso if "estoque_baixo" in alertas else COR.texto)
        linha_info(c2, 0, "Quantidade", unidades(med.quantidade_atual), destaque=True, cor=cor_estoque)
        linha_info(c2, 1, "Estoque mínimo", fmt_inteiro(med.estoque_minimo))
        linha_info(c2, 2, "Preço de compra", fmt_dinheiro(med.preco_compra_centavos))
        linha_info(c2, 3, "Preço de venda", fmt_dinheiro(med.preco_venda_centavos))
        linha_info(c2, 4, "Valor em estoque", f"{fmt_dinheiro(med.valor_custo_centavos)} (custo)  ·  "
                                              f"{fmt_dinheiro(med.valor_venda_centavos)} (venda)")
        ctk.CTkFrame(c2, height=8, fg_color="transparent").grid(row=5, column=0)

        c3 = self._cartao(grade, "Lote e validade", 1, 0)
        prazo = texto_prazo(med.dias_para_vencer(hoje)) if med.data_validade else ""
        cor_validade = COR.perigo if ALERTA_VENCIDO in alertas else (
            COR.aviso if "proximo_vencimento" in alertas else COR.texto)
        linha_info(c3, 0, "Validade", fmt_data(med.data_validade), destaque=True, cor=cor_validade)
        if prazo:
            linha_info(c3, 1, "Prazo", prazo, cor=cor_validade)
        linha_info(c3, 2, "Lote", med.lote)
        linha_info(c3, 3, "Fabricação", fmt_data(med.data_fabricacao))
        ctk.CTkFrame(c3, height=8, fg_color="transparent").grid(row=4, column=0)

        c4 = self._cartao(grade, "Últimas movimentações", 1, 1)
        movs = ctx.estoque.listar(medicamento_id=med.id, limite=5)
        if not movs:
            ctk.CTkLabel(c4, text="Nenhuma movimentação registrada.", font=fonte(13),
                         text_color=COR.texto_suave).grid(row=0, column=0, padx=16, pady=6, sticky="w")
        for i, m in enumerate(movs):
            sinal = f"+{m.quantidade}" if m.tipo == ENTRADA else f"-{m.quantidade}"
            cor = COR.entrada if m.tipo == ENTRADA else COR.saida
            ctk.CTkLabel(c4, text=fmt_data_hora(m.data_hora), font=fonte(12),
                         text_color=COR.texto_suave, anchor="w").grid(row=i, column=0, padx=(16, 8),
                                                                       pady=2, sticky="w")
            ctk.CTkLabel(c4, text=f"{sinal}  {m.motivo}", font=fonte(13, "bold"), text_color=cor,
                         anchor="w").grid(row=i, column=1, padx=(0, 16), pady=2, sticky="w")
        ctk.CTkFrame(c4, height=8, fg_color="transparent").grid(row=max(len(movs), 1), column=0)

        # ---- semelhantes e observações
        cs = Cartao(self.rolagem)
        cs.pack(fill="x", padx=8, pady=(8, 4))
        titulo_secao(cs, "Medicamentos semelhantes / referências").pack(anchor="w", padx=16, pady=(12, 2))
        if med.relacionados:
            for r in med.relacionados:
                linha = ctk.CTkFrame(cs, fg_color="transparent")
                linha.pack(fill="x", padx=16, pady=2)
                ctk.CTkLabel(linha, text=r.rotulo, font=fonte(13, "bold"), text_color=COR.texto,
                             anchor="w").pack(side="left")
                ctk.CTkLabel(linha, text=f"   {r.principio_ativo}  ·  {unidades(r.quantidade_atual)}  ·  "
                                         f"{r.localizacao}", font=fonte(12),
                             text_color=COR.texto_suave, anchor="w").pack(side="left")
                ctk.CTkButton(linha, text="Abrir", width=60, height=26, font=fonte(12),
                              fg_color=COR.primaria_suave, hover_color="#C3E6E0",
                              text_color=COR.primaria,
                              command=lambda i=r.id: self.app.abrir_detalhes(i)).pack(side="right")
        else:
            ctk.CTkLabel(cs, text="Nenhum medicamento relacionado foi cadastrado.", font=fonte(13),
                         text_color=COR.texto_suave).pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkLabel(cs, text="Relações vêm apenas do que foi cadastrado. Isto é uma ferramenta de "
                              "organização do estoque e não substitui a orientação de um farmacêutico.",
                     font=fonte(11), text_color=COR.texto_suave, anchor="w", justify="left",
                     wraplength=840).pack(anchor="w", padx=16, pady=(4, 12))

        if med.observacoes:
            co = Cartao(self.rolagem)
            co.pack(fill="x", padx=8, pady=(4, 12))
            titulo_secao(co, "Observações").pack(anchor="w", padx=16, pady=(12, 2))
            ctk.CTkLabel(co, text=med.observacoes, font=fonte(13), text_color=COR.texto, anchor="w",
                         justify="left", wraplength=840).pack(anchor="w", padx=16, pady=(0, 12))

    def _cartao(self, grade, titulo: str, linha: int, coluna: int) -> ctk.CTkFrame:
        cartao = Cartao(grade)
        cartao.grid(row=linha, column=coluna, sticky="nsew", padx=8, pady=6)
        titulo_secao(cartao, titulo).pack(anchor="w", padx=16, pady=(12, 4))
        interno = ctk.CTkFrame(cartao, fg_color="transparent")
        interno.pack(fill="both", expand=True, padx=2, pady=(0, 6))
        return interno
