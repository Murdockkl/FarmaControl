"""Funções de texto: normalização para busca e formatação no padrão brasileiro."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime


# --------------------------------------------------------------- normalização
def normalizar(valor) -> str:
    """Minúsculas, sem acentos e sem espaços nas pontas.

    "Cápsula " -> "capsula". Usada em buscas e na comparação de duplicados.
    O SQLite recebe esta mesma função (ver banco.py) como norm().
    """
    if valor is None:
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold().strip()


def limpar_espacos(valor) -> str:
    """Remove espaços nas pontas e reduz espaços repetidos a um só."""
    return re.sub(r"\s+", " ", str(valor or "")).strip()


def padrao_like(texto_normalizado: str) -> str:
    """Monta o padrão %texto% para o LIKE, protegendo % e _ digitados pelo usuário."""
    escapado = (
        texto_normalizado.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escapado}%"


# ------------------------------------------------------------- números e moeda
def fmt_inteiro(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def fmt_dinheiro(centavos: int) -> str:
    """1234567 -> 'R$ 12.345,67'."""
    centavos = int(centavos)
    sinal = "-" if centavos < 0 else ""
    reais, cent = divmod(abs(centavos), 100)
    return f"{sinal}R$ {fmt_inteiro(reais)},{cent:02d}"


def fmt_numero_decimal(centavos: int) -> str:
    """Valor sem 'R$', para planilhas e campos de edição: 890 -> '8,90'."""
    reais, cent = divmod(abs(int(centavos)), 100)
    return f"{reais},{cent:02d}"


def unidades(n: int) -> str:
    return f"{fmt_inteiro(n)} unidade" if n == 1 else f"{fmt_inteiro(n)} unidades"


def fmt_sinal(n: int) -> str:
    return f"+{fmt_inteiro(n)}" if n > 0 else fmt_inteiro(n)


# ---------------------------------------------------------------------- datas
def fmt_data(d: date | None, vazio: str = "—") -> str:
    return d.strftime("%d/%m/%Y") if d else vazio


def fmt_data_hora(dt: datetime | None, vazio: str = "—") -> str:
    return dt.strftime("%d/%m/%Y %H:%M") if dt else vazio


def texto_prazo(dias: int | None) -> str:
    """Descreve, em palavras, quantos dias faltam (ou passaram) para uma data."""
    if dias is None:
        return ""
    if dias == 0:
        return "vence hoje"
    if dias == 1:
        return "vence amanhã"
    if dias > 1:
        return f"faltam {dias} dias"
    if dias == -1:
        return "venceu ontem"
    return f"vencido há {abs(dias)} dias"


# ----------------------------------------------------- localização e rótulos
def descricao_localizacao(setor="", corredor="", estante="", prateleira="", gaveta="",
                          *, sep=" → ", incluir_setor=False, vazio="Não definida") -> str:
    """Ex.: 'Corredor A → Estante 02 → Prateleira 03'."""
    partes = []
    if incluir_setor and setor:
        partes.append(f"Setor {setor}")
    if corredor:
        partes.append(f"Corredor {corredor}")
    if estante:
        partes.append(f"Estante {estante}")
    if prateleira:
        partes.append(f"Prateleira {prateleira}")
    if gaveta:
        partes.append(f"Gaveta {gaveta}")
    if not partes and setor and not incluir_setor:
        partes.append(f"Setor {setor}")
    return sep.join(partes) if partes else vazio


def descricao_localizacao_curta(setor="", corredor="", estante="", prateleira="", gaveta="") -> str:
    """Versão compacta para tabelas: 'Corredor A · Est. 02 · Prat. 03'."""
    partes = []
    if corredor:
        partes.append(f"Corredor {corredor}")
    if estante:
        partes.append(f"Est. {estante}")
    if prateleira:
        partes.append(f"Prat. {prateleira}")
    if gaveta:
        partes.append(f"Gav. {gaveta}")
    if not partes and setor:
        return f"Setor {setor}"
    return " · ".join(partes) if partes else "—"


def texto_localizacao(setor="", corredor="", estante="", prateleira="", gaveta="") -> str:
    """Texto usado na busca: 'Setor X Corredor A Estante 02 Prateleira 03 Gaveta 1'."""
    partes = []
    for rotulo, valor in (("Setor", setor), ("Corredor", corredor), ("Estante", estante),
                          ("Prateleira", prateleira), ("Gaveta", gaveta)):
        if valor:
            partes.append(f"{rotulo} {valor}")
    return " ".join(partes)


def rotulo_medicamento(nome: str, dosagem: str = "", unidade: str = "") -> str:
    """Nome + dosagem, sem repetir a dosagem se ela já estiver no nome.

    ('Paracetamol', '750', 'mg') -> 'Paracetamol 750 mg'
    ('Paracetamol 750 mg', '750', 'mg') -> 'Paracetamol 750 mg'
    """
    dose = f"{dosagem} {unidade}".strip()
    if not dose:
        return nome
    if normalizar(dose) in normalizar(nome):
        return nome
    return f"{nome} {dose}"


def codigo(medicamento_id: int) -> str:
    return f"{int(medicamento_id):05d}"


_DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                "sexta-feira", "sábado", "domingo"]
_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro"]


def data_por_extenso(d: date) -> str:
    """19/09/2026 -> 'sábado, 19 de setembro de 2026' (não depende do idioma do Windows)."""
    return f"{_DIAS_SEMANA[d.weekday()]}, {d.day} de {_MESES[d.month - 1]} de {d.year}"
