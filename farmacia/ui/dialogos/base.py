"""Janelas modais: base comum e caixas de mensagem / confirmação no visual do sistema."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ..tema import COR, botao, escala_de, fonte


class Dialogo(ctk.CTkToplevel):
    """Janela modal centralizada sobre a janela principal.

    Uso: monte o conteúdo no __init__ e chame `self.exibir()` no final.
    """

    def __init__(self, app, titulo: str, largura: int, altura: int, *, redimensionavel: bool = False):
        super().__init__(app)
        self.withdraw()                                   # só aparece depois de pronta
        self.app = app
        self.configure(fg_color=COR.fundo)
        self.title(titulo)
        escala = escala_de(self)
        altura = min(altura, max(400, int(self.winfo_screenheight() / escala) - 120))
        largura = min(largura, max(420, int(self.winfo_screenwidth() / escala) - 60))
        self.geometry(f"{largura}x{altura}")
        self._tamanho = (largura, altura)                 # em unidades lógicas (antes do zoom)
        self.resizable(redimensionavel, redimensionavel)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.fechar)
        self.bind("<Escape>", lambda _e: self.fechar())
        self._fechado = False

    def exibir(self) -> None:
        self.update_idletasks()
        self._centralizar()
        self.deiconify()
        self.app.modais.append(self)
        self.after(60, self._capturar)

    def _centralizar(self) -> None:
        pai = self.app
        escala = escala_de(self)
        largura = int(self._tamanho[0] * escala)          # winfo_width() ainda vale 1 (janela oculta)
        altura = int(self._tamanho[1] * escala)
        x = pai.winfo_rootx() + (pai.winfo_width() - largura) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - altura) // 2
        # tk.Toplevel.geometry só muda a posição (o tamanho já foi definido acima)
        tk.Toplevel.geometry(self, f"+{max(x, 0)}+{max(y, 30)}")

    def _capturar(self, tentativas: int = 0) -> None:
        """Bloqueia a janela de trás (modal). Espera a janela ficar visível sem travar a tela."""
        if self._fechado:
            return
        try:
            if not self.winfo_viewable() and tentativas < 40:
                self.after(50, lambda: self._capturar(tentativas + 1))
                return
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            pass

    def fechar(self) -> None:
        if self._fechado:
            return
        self._fechado = True
        try:
            self.grab_release()
        except tk.TclError:
            pass
        if self in self.app.modais:
            self.app.modais.remove(self)
        self.ao_fechar()
        self.destroy()
        if self.app.modais:                               # devolve o foco à janela de baixo
            anterior = self.app.modais[-1]
            try:
                anterior.grab_set()
                anterior.focus_force()
            except tk.TclError:
                pass

    def ao_fechar(self) -> None:
        """Gancho para as subclasses limparem o que registraram."""


class _CaixaSimples(Dialogo):
    _ICONES = {"info": ("i", "info"), "erro": ("!", "perigo"), "aviso": ("!", "aviso"),
               "pergunta": ("?", "info"), "perigo": ("!", "perigo")}

    def __init__(self, app, titulo, mensagem, tipo, botao_ok, botao_cancelar):
        super().__init__(app, titulo, 470, 100)
        self.resultado = False
        icone, estilo = self._ICONES[tipo]
        from ..tema import ESTILO_BADGE
        cor_texto, cor_fundo = ESTILO_BADGE[estilo]

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=24, pady=(22, 8))
        ctk.CTkLabel(corpo, text=icone, width=44, height=44, corner_radius=22, fg_color=cor_fundo,
                     text_color=cor_texto, font=fonte(20, "bold")).pack(side="left", anchor="n")
        textos = ctk.CTkFrame(corpo, fg_color="transparent")
        textos.pack(side="left", fill="both", expand=True, padx=(16, 0))
        ctk.CTkLabel(textos, text=titulo, font=fonte(16, "bold"), text_color=COR.texto,
                     anchor="w", justify="left", wraplength=340).pack(anchor="w")
        ctk.CTkLabel(textos, text=mensagem, font=fonte(13), text_color=COR.texto_suave, anchor="w",
                     justify="left", wraplength=340).pack(anchor="w", pady=(6, 0))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(10, 20))
        estilo_ok = "perigo" if tipo == "perigo" else "primario"
        self.btn_ok = botao(rodape, botao_ok, self._ok, tipo=estilo_ok, largura=120)
        self.btn_ok.pack(side="right")
        if botao_cancelar:
            botao(rodape, botao_cancelar, self.fechar, tipo="secundario", largura=110).pack(
                side="right", padx=(0, 10))
        self.bind("<Return>", lambda _e: self._ok())

        # ajusta a altura ao conteúdo
        self.update_idletasks()
        altura = self.winfo_reqheight() + 4
        altura = max(int(altura / escala_de(self)), 170)
        self.geometry(f"470x{altura}")
        self._tamanho = (470, altura)
        self.exibir()

    def _ok(self):
        self.resultado = True
        self.fechar()


def mostrar_mensagem(app, titulo: str, mensagem: str, tipo: str = "info") -> None:
    caixa = _CaixaSimples(app, titulo, mensagem, tipo, "OK", None)
    app.wait_window(caixa)


def pedir_confirmacao(app, titulo: str, mensagem: str, confirmar: str = "Confirmar",
                      cancelar: str = "Cancelar", perigo: bool = False) -> bool:
    caixa = _CaixaSimples(app, titulo, mensagem, "perigo" if perigo else "pergunta",
                          confirmar, cancelar)
    app.wait_window(caixa)
    return caixa.resultado
