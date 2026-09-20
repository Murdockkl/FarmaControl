"""Converte o que o usuário digita (texto) em números e datas, com mensagens claras.

Todas as funções levantam ValueError com uma mensagem pronta para exibição.
"""
from __future__ import annotations

import calendar
import re
from datetime import date

from .config import LIMITE_CENTAVOS, LIMITE_QUANTIDADE

_ANO_MIN, _ANO_MAX = 1990, 2100


def converter_inteiro(texto: str, *, obrigatorio: bool = False, minimo: int = 0,
                      maximo: int = LIMITE_QUANTIDADE) -> int:
    """'25' -> 25. Vazio vale 0, a menos que o campo seja obrigatório."""
    t = (texto or "").strip().replace(" ", "")
    if not t:
        if obrigatorio:
            raise ValueError("Informe a quantidade.")
        return 0
    if t.startswith("-"):
        raise ValueError("Não é permitido informar valor negativo.")
    if not t.isdigit():
        raise ValueError("Use apenas números inteiros, sem vírgula, ponto ou letras.")
    valor = int(t)
    if valor < minimo:
        raise ValueError(f"O valor mínimo é {minimo}.")
    if valor > maximo:
        raise ValueError("Valor muito alto. Confira o número digitado.")
    return valor


def converter_dinheiro(texto: str) -> int:
    """'8,90' | '8.90' | 'R$ 1.234,56' -> centavos (int). Vazio vale 0."""
    t = re.sub(r"^R\$\s*", "", (texto or "").strip(), flags=re.IGNORECASE).replace(" ", "")
    if not t:
        return 0
    if t.startswith("-"):
        raise ValueError("O valor não pode ser negativo.")
    if not re.fullmatch(r"[\d.,]+", t):
        raise ValueError("Valor inválido. Use apenas números, por exemplo 8,90.")

    if "," in t and "." in t:                       # 1.234,56  ou  1,234.56
        if t.rfind(",") > t.rfind("."):
            inteiro, dec = t.rsplit(",", 1)
            inteiro = inteiro.replace(".", "")
        else:
            inteiro, dec = t.rsplit(".", 1)
            inteiro = inteiro.replace(",", "")
    elif "," in t:                                  # 8,90
        if t.count(",") > 1:
            raise ValueError("Valor inválido. Use apenas uma vírgula, por exemplo 8,90.")
        inteiro, dec = t.split(",")
    elif "." in t:                                  # 8.90  ou  1.234
        partes = t.split(".")
        if len(partes) == 2 and len(partes[1]) != 3:
            inteiro, dec = partes
        else:
            inteiro, dec = "".join(partes), ""
    else:
        inteiro, dec = t, ""

    inteiro = inteiro or "0"
    if not inteiro.isdigit() or (dec and not dec.isdigit()):
        raise ValueError("Valor inválido. Use apenas números, por exemplo 8,90.")
    if len(dec) > 2:
        raise ValueError("Use no máximo 2 casas decimais (centavos).")
    centavos = int(inteiro) * 100 + int(dec.ljust(2, "0") or "0")
    if centavos > LIMITE_CENTAVOS:
        raise ValueError("Valor muito alto. Confira o número digitado.")
    return centavos


def converter_data(texto: str, *, fim_do_mes: bool = False) -> date | None:
    """Aceita 'dd/mm/aaaa', 'mm/aaaa' e 'aaaa-mm-dd'. Vazio devolve None.

    Em 'mm/aaaa' (comum em embalagens), usa o último dia do mês quando
    fim_do_mes=True (validade) ou o primeiro dia (fabricação).
    """
    t = (texto or "").strip()
    if not t:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        ano, mes, dia = int(m[1]), int(m[2]), int(m[3])
    else:
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", t)
        if m:
            dia, mes, ano = int(m[1]), int(m[2]), int(m[3])
        else:
            m = re.fullmatch(r"(\d{1,2})[/.\-](\d{4})", t)
            if not m:
                raise ValueError("Data inválida. Use dd/mm/aaaa ou mm/aaaa (ex.: 31/08/2027 ou 08/2027).")
            mes, ano = int(m[1]), int(m[2])
            if not 1 <= mes <= 12:
                raise ValueError("Mês inválido. Use um valor entre 01 e 12.")
            dia = calendar.monthrange(ano, mes)[1] if fim_do_mes else 1
    if not _ANO_MIN <= ano <= _ANO_MAX:
        raise ValueError(f"Ano inválido. Use um ano entre {_ANO_MIN} e {_ANO_MAX}.")
    try:
        return date(ano, mes, dia)
    except ValueError:
        raise ValueError("Essa data não existe no calendário. Confira o dia e o mês.") from None
