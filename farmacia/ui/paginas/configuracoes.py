"""Configurações: nome da farmácia, prazo de alerta, backup, restauração e dados de demonstração."""
from __future__ import annotations

import os
import subprocess
import sys
from tkinter import filedialog

import customtkinter as ctk

from ...config import APP_NOME, APP_VERSAO, DIAS_ALERTA_MAXIMO
from ...dominio import BackupError, FarmaciaError
from ..tema import COR, botao, fonte
from ..widgets import Cartao, cabecalho_pagina, limpar_entrada, titulo_secao


class PaginaConfiguracoes(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        cab, _ = cabecalho_pagina(self, "Configurações", "Ajustes do sistema, backup e dados de exemplo.")
        cab.grid(row=0, column=0, sticky="w", padx=32, pady=(26, 10))
        self.rolagem = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rolagem.grid(row=1, column=0, sticky="nsew", padx=(24, 16), pady=(0, 12))
        self.rolagem.columnconfigure(0, weight=1)

        estilo_entrada = dict(height=38, font=fonte(13), corner_radius=8, border_color=COR.borda,
                              fg_color=COR.cartao)

        # ---- farmácia
        c = self._cartao("Sua farmácia", "O nome aparece no menu, no início e nos relatórios.")
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=(0, 16))
        self.nome = ctk.CTkEntry(linha, width=340, placeholder_text="Ex.: Farmácia Saúde", **estilo_entrada)
        self.nome.pack(side="left")
        botao(linha, "Salvar nome", self._salvar_nome, tipo="suave", largura=120).pack(side="left", padx=10)

        # ---- alertas
        c = self._cartao("Alerta de validade",
                         "Avisar quando um medicamento estiver perto de vencer. Por exemplo, 30 = avisar "
                         "30 dias antes.")
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkLabel(linha, text="Avisar", font=fonte(13), text_color=COR.texto).pack(side="left")
        self.dias = ctk.CTkEntry(linha, width=80, justify="center", **estilo_entrada)
        self.dias.pack(side="left", padx=8)
        ctk.CTkLabel(linha, text="dias antes do vencimento", font=fonte(13), text_color=COR.texto).pack(side="left")
        botao(linha, "Salvar", self._salvar_dias, tipo="suave", largura=90).pack(side="left", padx=14)
        self.msg_dias = ctk.CTkLabel(c, text="", font=fonte(12, "bold"), text_color=COR.perigo, anchor="w")
        self._cartao_dias = c
        ctk.CTkFrame(c, height=10, fg_color="transparent").pack()       # respiro inferior
        self.dias.bind("<Return>", lambda _e: self._salvar_dias())

        # ---- backup
        c = self._cartao("Backup e restauração",
                         "O backup é uma cópia de todos os seus dados em um único arquivo (.db). "
                         "Guarde-o em um pen drive ou na nuvem. Faça backups com frequência.")
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=(0, 6))
        botao(linha, "Fazer backup", self._backup, largura=160).pack(side="left")
        botao(linha, "Restaurar backup", self._restaurar, tipo="secundario", largura=170).pack(side="left", padx=10)
        ctk.CTkLabel(c, text="Ao restaurar, os dados atuais são substituídos pelos do arquivo. Antes disso o "
                             "sistema guarda automaticamente uma cópia dos dados atuais.",
                     font=fonte(12), text_color=COR.texto_suave, anchor="w", justify="left",
                     wraplength=760).pack(anchor="w", padx=20, pady=(2, 16))

        # ---- demonstração
        c = self._cartao("Dados de demonstração",
                         "Medicamentos FICTÍCIOS para testar pesquisa, estoque, alertas e localização. "
                         "Ficam identificados como demonstração e podem ser removidos a qualquer momento "
                         "sem afetar seus medicamentos reais.")
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=(0, 16))
        self.btn_add_demo = botao(linha, "Adicionar dados de demonstração", self.app.adicionar_demo, largura=250)
        self.btn_add_demo.pack(side="left")
        self.btn_rem_demo = botao(linha, "Remover dados de demonstração", self._remover_demo,
                                  tipo="secundario", largura=250)
        self.btn_rem_demo.pack(side="left", padx=10)

        # ---- informações
        c = self._cartao("Informações do sistema", "")
        self.info = ctk.CTkLabel(c, text="", font=fonte(12), text_color=COR.texto_suave, anchor="w",
                                 justify="left", wraplength=760)
        self.info.pack(anchor="w", padx=20)
        botao(c, "Abrir pasta dos dados", self._abrir_pasta, tipo="secundario", largura=190, altura=32).pack(
            anchor="w", padx=20, pady=(8, 16))

    def _cartao(self, titulo: str, descricao: str) -> Cartao:
        cartao = Cartao(self.rolagem)
        cartao.pack(fill="x", padx=8, pady=6)
        titulo_secao(cartao, titulo).pack(anchor="w", padx=20, pady=(16, 2))
        if descricao:
            ctk.CTkLabel(cartao, text=descricao, font=fonte(12), text_color=COR.texto_suave, anchor="w",
                         justify="left", wraplength=760).pack(anchor="w", padx=20, pady=(0, 10))
        return cartao

    # ------------------------------------------------------------------- dados
    def atualizar(self) -> None:
        ctx = self.app.ctx
        for campo, valor in ((self.nome, ctx.config.nome_farmacia), (self.dias, str(ctx.config.dias_alerta))):
            limpar_entrada(campo)
            if valor:
                campo.insert(0, valor)
        tem_demo = ctx.demo.existem_dados_demo()
        self.btn_rem_demo.configure(state="normal" if tem_demo else "disabled")
        self.info.configure(
            text=f"{APP_NOME} versão {APP_VERSAO}\nBanco de dados: {ctx.caminho_banco}\n"
                 f"Medicamentos cadastrados: {ctx.medicamentos.total()}")

    # ------------------------------------------------------------------- ações
    def _salvar_nome(self) -> None:
        try:
            self.app.ctx.config.definir_nome_farmacia(self.nome.get())
        except FarmaciaError as e:
            self.app.mensagem("Nome inválido", str(e), "erro")
            return
        self.app.aviso("Nome da farmácia salvo.")
        self.app.dados_alterados()

    def _salvar_dias(self) -> None:
        try:
            dias = self.app.ctx.config.definir_dias_alerta(self.dias.get())
        except FarmaciaError as e:
            self.msg_dias.configure(text=str(e))
            self.msg_dias.pack(anchor="w", padx=20, pady=(0, 6))
            self.dias.configure(border_color=COR.perigo)
            return
        self.msg_dias.pack_forget()
        self.dias.configure(border_color=COR.borda)
        self.app.aviso(f"Alerta de validade: {dias} dias antes do vencimento.")
        self.app.dados_alterados()

    def _backup(self) -> None:
        caminho = filedialog.asksaveasfilename(
            parent=self.app, title="Salvar backup", defaultextension=".db",
            initialfile=self.app.ctx.backup.nome_sugerido(),
            filetypes=[("Backup do FarmaControl (.db)", "*.db"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            self.app.ctx.backup.criar_backup(caminho)
        except FarmaciaError as e:
            self.app.mensagem("Não foi possível fazer o backup", str(e), "erro")
            return
        self.app.mensagem("Backup concluído", f"Seus dados foram salvos em:\n{caminho}", "info")

    def _restaurar(self) -> None:
        caminho = filedialog.askopenfilename(
            parent=self.app, title="Escolha o arquivo de backup",
            filetypes=[("Backup do FarmaControl (.db)", "*.db"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            self.app.ctx.db.validar_arquivo(caminho)
        except BackupError as e:
            self.app.mensagem("Arquivo inválido", str(e), "erro")
            return
        if not self.app.confirmar(
                "Restaurar este backup?",
                "TODOS os dados atuais serão substituídos pelos dados do arquivo escolhido.\n\n"
                f"{caminho}\n\nUma cópia dos dados atuais será guardada automaticamente antes.",
                "Restaurar", perigo=True):
            return
        try:
            copia = self.app.ctx.backup.restaurar(caminho)
        except FarmaciaError as e:
            self.app.mensagem("Não foi possível restaurar", str(e), "erro")
            return
        self.app.dados_alterados()
        self.app.mensagem("Backup restaurado",
                          f"Os dados foram restaurados com sucesso.\n\nCópia dos dados anteriores:\n{copia}",
                          "info")

    def _remover_demo(self) -> None:
        if not self.app.confirmar(
                "Remover dados de demonstração?",
                "Serão apagados apenas os medicamentos fictícios de demonstração e o histórico deles. "
                "Seus medicamentos reais não serão alterados.", "Remover", perigo=True):
            return
        qtd = self.app.ctx.demo.remover()
        self.app.aviso(f"{qtd} medicamentos de demonstração removidos.")
        self.app.dados_alterados()

    def _abrir_pasta(self) -> None:
        pasta = self.app.ctx.caminho_banco.parent
        try:
            if sys.platform.startswith("win"):
                os.startfile(pasta)                                   # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(pasta)], check=False)
            else:
                subprocess.run(["xdg-open", str(pasta)], check=False)
        except OSError:
            self.app.mensagem("Pasta dos dados", f"Os dados estão em:\n{pasta}", "info")
