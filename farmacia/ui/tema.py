"""Aparência do sistema: paleta discreta (verde-azulado, cor comum na área da saúde),
tipografia legível e estilo das tabelas. Para mudar o visual, ajuste este arquivo."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

import customtkinter as ctk

COR = SimpleNamespace(
    # marca
    primaria="#0F766E", primaria_hover="#0B5F58", primaria_suave="#D6EFEB",
    # menu lateral
    lateral="#0C4A46", lateral_hover="#125E59", lateral_ativo="#16807A",
    lateral_texto="#E2F2F0", lateral_texto_suave="#8DBCB7",
    # base
    fundo="#F2F6F5", cartao="#FFFFFF", borda="#D9E3E1", linha="#EDF2F1",
    texto="#1E2B29", texto_suave="#63767A", texto_claro="#FFFFFF",
    # estados (cor do texto / cor de fundo suave)
    ok="#166534", ok_fundo="#DCFCE7",
    aviso="#92400E", aviso_fundo="#FEF3C7",
    perigo="#B91C1C", perigo_fundo="#FEE2E2", perigo_hover="#991B1B",
    info="#1E40AF", info_fundo="#DBEAFE",
    neutro="#475569", neutro_fundo="#E6EDEB",
    # ações
    entrada="#15803D", entrada_hover="#116A32",
    saida="#C2410C", saida_hover="#9A3412",
    # linhas de tabela
    linha_vencido="#FDE4E4", linha_baixo="#FFF1D6", linha_proximo="#FEF9D8", linha_par="#F7FAF9",
)

if sys.platform.startswith("win"):
    FAMILIA = "Segoe UI"
elif sys.platform == "darwin":
    FAMILIA = "Helvetica Neue"
else:
    FAMILIA = "DejaVu Sans"

_fontes: dict[tuple, ctk.CTkFont] = {}


def fonte(tamanho: int = 13, peso: str = "normal") -> ctk.CTkFont:
    """Fonte reutilizada (criada sob demanda, depois que a janela principal existe)."""
    chave = (tamanho, peso)
    if chave not in _fontes:
        _fontes[chave] = ctk.CTkFont(family=FAMILIA, size=tamanho, weight=peso)
    return _fontes[chave]


def escala_de(widget) -> float:
    """Fator de escala da tela (150% no Windows = 1.5). Usado nas tabelas (ttk)."""
    try:
        return float(ctk.ScalingTracker.get_widget_scaling(widget))
    except Exception:
        return 1.0


# ------------------------------------------------------------ cores por situação
ESTILO_BADGE = {
    "ok": (COR.ok, COR.ok_fundo),
    "aviso": (COR.aviso, COR.aviso_fundo),
    "perigo": (COR.perigo, COR.perigo_fundo),
    "info": (COR.info, COR.info_fundo),
    "neutro": (COR.neutro, COR.neutro_fundo),
}

# alerta do domínio -> estilo de badge / tag de linha
BADGE_DO_ALERTA = {
    "vencido": "perigo", "sem_estoque": "perigo",
    "estoque_baixo": "aviso", "proximo_vencimento": "aviso",
}
TAG_DO_ALERTA = {
    "vencido": "vencido", "sem_estoque": "baixo",
    "estoque_baixo": "baixo", "proximo_vencimento": "proximo",
}


def aplicar_estilo_ttk(root) -> None:
    """Deixa a tabela (ttk.Treeview) com aparência moderna e limpa."""
    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    esc = escala_de(root)
    estilo.layout("Farma.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    estilo.configure("Farma.Treeview", background=COR.cartao, fieldbackground=COR.cartao,
                     foreground=COR.texto, borderwidth=0, relief="flat",
                     rowheight=int(30 * esc), font=(FAMILIA, 10))
    estilo.map("Farma.Treeview",
               background=[("selected", COR.primaria_suave)],
               foreground=[("selected", COR.texto)])
    estilo.configure("Farma.Treeview.Heading", background="#E9F1EF", foreground=COR.texto_suave,
                     font=(FAMILIA, 10, "bold"), relief="flat", borderwidth=0,
                     padding=(8, int(7 * esc)))
    estilo.map("Farma.Treeview.Heading", background=[("active", "#DCE9E6")])
    estilo.configure("Farma.Vertical.TScrollbar", background="#C5D3D0", troughcolor=COR.cartao,
                     bordercolor=COR.cartao, arrowcolor=COR.texto_suave, relief="flat",
                     gripcount=0, lightcolor="#C5D3D0", darkcolor="#C5D3D0")
    estilo.map("Farma.Vertical.TScrollbar", background=[("active", "#A9BDB9")])
    estilo.configure("Farma.Horizontal.TScrollbar", background="#C5D3D0", troughcolor=COR.cartao,
                     bordercolor=COR.cartao, arrowcolor=COR.texto_suave, relief="flat",
                     gripcount=0, lightcolor="#C5D3D0", darkcolor="#C5D3D0")
    estilo.map("Farma.Horizontal.TScrollbar", background=[("active", "#A9BDB9")])


# ------------------------------------------------------------------- botões
def botao(master, texto, comando=None, *, tipo="primario", largura=None, altura=36, **kw):
    """Botão padronizado. tipo: primario | secundario | perigo | entrada | saida | suave."""
    estilos = {
        "primario": dict(fg_color=COR.primaria, hover_color=COR.primaria_hover,
                         text_color=COR.texto_claro),
        "secundario": dict(fg_color=COR.cartao, hover_color=COR.linha, text_color=COR.texto,
                           border_width=1, border_color=COR.borda),
        "perigo": dict(fg_color=COR.perigo, hover_color=COR.perigo_hover, text_color=COR.texto_claro),
        "entrada": dict(fg_color=COR.entrada, hover_color=COR.entrada_hover,
                        text_color=COR.texto_claro),
        "saida": dict(fg_color=COR.saida, hover_color=COR.saida_hover, text_color=COR.texto_claro),
        "suave": dict(fg_color=COR.primaria_suave, hover_color="#C3E6E0", text_color=COR.primaria),
    }
    opcoes = dict(estilos[tipo])
    opcoes.update(kw)
    if largura:
        opcoes["width"] = largura
    return ctk.CTkButton(master, text=texto, command=comando, height=altura, corner_radius=8,
                         font=fonte(13, "bold"), text_color_disabled="#9FB0AD", **opcoes)
