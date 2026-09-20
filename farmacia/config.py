"""Configurações fixas do programa (nomes, caminhos e listas de opções).

Tudo o que o usuário pode querer ajustar no código (por exemplo, a lista de
formas farmacêuticas ou os motivos de movimentação) fica neste arquivo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NOME = "FarmaControl"
APP_VERSAO = "1.0.0"
ARQUIVO_BANCO = "farmacia.db"

# ----------------------------------------------------------------- limites
LIMITE_QUANTIDADE = 10_000_000          # unidades
LIMITE_CENTAVOS = 99_999_999            # R$ 999.999,99
DIAS_ALERTA_PADRAO = 30
DIAS_ALERTA_MAXIMO = 730

# ------------------------------------------------- listas de apoio (formulários)
FORMAS_FARMACEUTICAS = [
    "Comprimido", "Cápsula", "Xarope", "Solução", "Suspensão", "Creme",
    "Pomada", "Gel", "Gotas", "Spray", "Injetável", "Pó", "Supositório", "Adesivo",
]

UNIDADES_MEDIDA = ["mg", "g", "mcg", "mL", "L", "UI", "%", "mg/mL", "mg/g", "mg/5 mL"]

MOTIVOS_ENTRADA = [
    "Compra", "Devolução de cliente", "Transferência recebida",
    "Ajuste de inventário", "Outro",
]
MOTIVOS_SAIDA = [
    "Venda", "Perda ou avaria", "Descarte por vencimento",
    "Devolução ao fornecedor", "Transferência enviada",
    "Ajuste de inventário", "Outro",
]
MOTIVO_ESTOQUE_INICIAL = "Estoque inicial"


# ------------------------------------------------------------------ caminhos
def pasta_do_programa() -> Path:
    """Pasta onde o programa está (ou onde está o .exe, quando empacotado)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _pasta_gravavel(pasta: Path) -> bool:
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        teste = pasta / ".teste_escrita"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        return True
    except OSError:
        return False


def pasta_de_dados() -> Path:
    """Pasta onde ficam o banco de dados, o log e as cópias de segurança.

    Ordem de escolha:
      1. variável de ambiente FARMACIA_DATA_DIR (usada nos testes);
      2. pasta "dados" ao lado do programa (fácil de achar e de copiar);
      3. pasta "FarmaControl" dentro da pasta do usuário, se a anterior
         não permitir gravação (ex.: programa instalado em "Arquivos de Programas").
    """
    ambiente = os.environ.get("FARMACIA_DATA_DIR")
    if ambiente:
        pasta = Path(ambiente).expanduser()
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta
    pasta = pasta_do_programa() / "dados"
    if _pasta_gravavel(pasta):
        return pasta
    pasta = Path.home() / APP_NOME
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def caminho_do_banco() -> Path:
    return pasta_de_dados() / ARQUIVO_BANCO
