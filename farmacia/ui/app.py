"""Janela principal do FarmaControl: menu lateral, páginas e ações compartilhadas."""
from __future__ import annotations

import logging
import traceback

import customtkinter as ctk

from ..config import APP_NOME
from ..contexto import Contexto
from ..dominio import FarmaciaError
from .dialogos.base import mostrar_mensagem, pedir_confirmacao
from .dialogos.detalhes import DialogoDetalhes
from .dialogos.formulario import DialogoFormulario
from .dialogos.movimentacao import DialogoMovimentacao
from .paginas.configuracoes import PaginaConfiguracoes
from .paginas.dashboard import PaginaDashboard
from .paginas.estoque import PaginaEstoque
from .paginas.historico import PaginaHistorico
from .paginas.medicamentos import PaginaMedicamentos
from .paginas.relatorios import PaginaRelatorios
from .tema import COR, aplicar_estilo_ttk, escala_de, fonte
from .widgets import Aviso

log = logging.getLogger(__name__)

# (chave, texto do menu, ícone, classe da página)
MENU = [
    ("dashboard", "Início", "⌂", PaginaDashboard),
    ("medicamentos", "Medicamentos", "✚", PaginaMedicamentos),
    ("estoque", "Estoque", "⇅", PaginaEstoque),
    ("historico", "Histórico", "☰", PaginaHistorico),
    ("relatorios", "Relatórios", "▤", PaginaRelatorios),
    ("configuracoes", "Configurações", "⚙", PaginaConfiguracoes),
]


class App(ctk.CTk):
    def __init__(self, ctx: Contexto):
        ctk.set_appearance_mode("light")
        super().__init__()
        self.ctx = ctx
        self.modais: list = []                 # janelas modais abertas (a última é a de cima)
        self.ouvintes: list = []               # funções chamadas quando os dados mudam
        self.paginas: dict[str, ctk.CTkFrame] = {}
        self._sujas: set[str] = set()
        self.pagina_atual = ""

        self.title(f"{APP_NOME} - Gerenciamento de Farmácia")
        escala = escala_de(self)                # zoom do Windows (125%, 150%...)
        largura = min(1320, int(self.winfo_screenwidth() / escala) - 40)
        altura = min(820, int(self.winfo_screenheight() / escala) - 90)
        self.geometry(f"{largura}x{altura}+20+20")
        self.minsize(min(1180, largura), min(680, altura))
        self.configure(fg_color=COR.fundo)
        aplicar_estilo_ttk(self)
        self.protocol("WM_DELETE_WINDOW", self._sair)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._montar_menu()
        self.conteudo = ctk.CTkFrame(self, fg_color=COR.fundo, corner_radius=0)
        self.conteudo.grid(row=0, column=1, sticky="nsew")
        self.conteudo.columnconfigure(0, weight=1)
        self.conteudo.rowconfigure(0, weight=1)
        self._aviso = Aviso(self)
        self.bind("<Control-n>", lambda _e: None if self.modais else self.abrir_formulario())
        self.navegar("dashboard")

    # ---------------------------------------------------------------- menu lateral
    def _montar_menu(self) -> None:
        lateral = ctk.CTkFrame(self, width=240, fg_color=COR.lateral, corner_radius=0)
        lateral.grid(row=0, column=0, sticky="ns")
        lateral.grid_propagate(False)
        lateral.rowconfigure(20, weight=1)

        marca = ctk.CTkFrame(lateral, fg_color="transparent")
        marca.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 4))
        ctk.CTkLabel(marca, text="✚", width=40, height=40, corner_radius=12, fg_color=COR.lateral_ativo,
                     text_color="#FFFFFF", font=fonte(20, "bold")).pack(side="left")
        textos = ctk.CTkFrame(marca, fg_color="transparent")
        textos.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(textos, text=APP_NOME, font=fonte(18, "bold"), text_color="#FFFFFF",
                     anchor="w").pack(anchor="w")
        self.rotulo_farmacia = ctk.CTkLabel(textos, text="", font=fonte(12), text_color=COR.lateral_texto_suave,
                                            anchor="w", wraplength=140, justify="left")
        self.rotulo_farmacia.pack(anchor="w")

        ctk.CTkFrame(lateral, height=1, fg_color=COR.lateral_hover).grid(
            row=1, column=0, sticky="ew", padx=20, pady=(20, 14))
        self.botoes_menu: dict[str, ctk.CTkButton] = {}
        for i, (chave, texto, icone, _classe) in enumerate(MENU, start=2):
            b = ctk.CTkButton(lateral, text=f"  {icone}   {texto}", anchor="w", height=44, corner_radius=10,
                              font=fonte(14, "bold"), fg_color="transparent",
                              hover_color=COR.lateral_hover, text_color=COR.lateral_texto,
                              command=lambda k=chave: self.navegar(k))
            b.grid(row=i, column=0, sticky="ew", padx=14, pady=2)
            self.botoes_menu[chave] = b

        rodape = ctk.CTkLabel(lateral, text="Sistema local\nseus dados ficam neste computador",
                              font=fonte(11), text_color=COR.lateral_texto_suave, justify="left",
                              anchor="w")
        rodape.grid(row=21, column=0, sticky="sw", padx=22, pady=(0, 20))

    def _atualizar_marca(self) -> None:
        nome = self.ctx.config.nome_farmacia
        self.rotulo_farmacia.configure(text=nome or "Gestão de medicamentos")

    # ------------------------------------------------------------------ navegação
    def navegar(self, chave: str) -> ctk.CTkFrame:
        if chave not in self.paginas:
            classe = next(c for k, _t, _i, c in MENU if k == chave)
            pagina = classe(self.conteudo, self)
            pagina.grid(row=0, column=0, sticky="nsew")
            self.paginas[chave] = pagina
            self._sujas.add(chave)
        pagina = self.paginas[chave]
        if chave in self._sujas:
            self._sujas.discard(chave)
            pagina.atualizar()
        pagina.tkraise()
        self.pagina_atual = chave
        for k, b in self.botoes_menu.items():
            ativo = k == chave
            b.configure(fg_color=COR.lateral_ativo if ativo else "transparent",
                        text_color="#FFFFFF" if ativo else COR.lateral_texto)
        self._atualizar_marca()
        return pagina

    def ver_medicamentos(self, situacao: str) -> None:
        """Abre a lista de medicamentos já filtrada (atalho dos cartões do início)."""
        pagina = self.navegar("medicamentos")
        pagina.aplicar_filtro_situacao(situacao)

    def dados_alterados(self) -> None:
        """Chame depois de qualquer alteração: todas as telas se atualizam."""
        self._sujas = set(self.paginas)
        for ouvinte in list(self.ouvintes):
            ouvinte()
        if self.pagina_atual:
            self._sujas.discard(self.pagina_atual)
            self.paginas[self.pagina_atual].atualizar()
        self._atualizar_marca()

    # -------------------------------------------------------------------- avisos
    def aviso(self, mensagem: str, tipo: str = "ok", ms: int = 3500) -> None:
        self._aviso.mostrar(mensagem, tipo, ms)

    def mensagem(self, titulo: str, texto: str, tipo: str = "info") -> None:
        mostrar_mensagem(self, titulo, texto, tipo)

    def confirmar(self, titulo: str, texto: str, confirmar: str = "Confirmar", perigo: bool = False) -> bool:
        return pedir_confirmacao(self, titulo, texto, confirmar, perigo=perigo)

    # ------------------------------------------------------------------- diálogos
    def _existe(self, medicamento_id) -> int | None:
        med_id = int(medicamento_id)
        if self.ctx.medicamentos.obter(med_id) is None:
            self.mensagem("Medicamento não encontrado", "Este medicamento não existe mais no cadastro.", "aviso")
            self.dados_alterados()
            return None
        return med_id

    def abrir_detalhes(self, medicamento_id) -> None:
        if (med_id := self._existe(medicamento_id)) is not None:
            DialogoDetalhes(self, med_id)

    def abrir_movimentacao(self, medicamento_id, tipo: str) -> None:
        if (med_id := self._existe(medicamento_id)) is not None:
            DialogoMovimentacao(self, med_id, tipo)

    def abrir_formulario(self, medicamento_id=None, ao_salvar=None) -> None:
        if medicamento_id is not None and self._existe(medicamento_id) is None:
            return
        DialogoFormulario(self, int(medicamento_id) if medicamento_id is not None else None, ao_salvar)

    def excluir_medicamento(self, medicamento_id) -> None:
        med = self.ctx.medicamentos.obter(int(medicamento_id))
        if med is None:
            self.dados_alterados()
            return
        movimentos = self.ctx.medicamentos.contar_movimentacoes(med.id)
        texto = (f"Você vai excluir \"{med.rotulo}\" do cadastro"
                 + (f", que tem {med.quantidade_atual} unidade(s) em estoque" if med.quantidade_atual else "")
                 + ".\n\n")
        texto += (f"As {movimentos} movimentações dele continuarão no histórico." if movimentos
                  else "Ele não tem movimentações registradas.")
        texto += "\nEsta ação não pode ser desfeita pela tela."
        if not self.confirmar("Excluir medicamento?", texto, "Excluir", perigo=True):
            return
        try:
            self.ctx.medicamentos.excluir(med.id)
        except FarmaciaError as e:
            self.mensagem("Não foi possível excluir", str(e), "erro")
            return
        self.aviso(f"Medicamento excluído: {med.rotulo}", "info")
        self.dados_alterados()

    def adicionar_demo(self) -> None:
        if self.ctx.demo.existem_dados_demo():
            self.mensagem("Dados de demonstração", "Os dados de demonstração já foram adicionados.", "info")
            return
        qtd = self.ctx.demo.adicionar()
        self.aviso(f"{qtd} medicamentos FICTÍCIOS de demonstração adicionados.", "info", 5000)
        self.dados_alterados()

    # --------------------------------------------------------------------- saída
    def _sair(self) -> None:
        try:
            self.ctx.fechar()
        finally:
            self.destroy()

    def report_callback_exception(self, exc, val, tb) -> None:
        """Qualquer erro inesperado vira uma mensagem amigável (e um registro no log)."""
        log.error("Erro inesperado na interface:\n%s", "".join(traceback.format_exception(exc, val, tb)))
        try:
            self.mensagem("Ocorreu um erro inesperado",
                          "O sistema encontrou um problema, mas seus dados continuam salvos.\n\n"
                          f"Detalhe: {val}\n\nO registro completo está no arquivo farmacia.log, "
                          "na pasta dos dados.", "erro")
        except Exception:
            pass
