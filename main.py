"""FarmaControl - sistema local de gerenciamento de farmácia.

Como executar:
    python main.py
"""
from __future__ import annotations

import logging
import sys


def _avisar_erro(titulo: str, texto: str) -> None:
    """Mostra um erro em janela simples (usado antes da interface principal existir)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror(titulo, texto)
        raiz.destroy()
    except Exception:
        print(f"{titulo}\n{texto}", file=sys.stderr)


def main() -> int:
    if sys.version_info < (3, 10):
        _avisar_erro("Python desatualizado", "O FarmaControl precisa do Python 3.10 ou mais novo.")
        return 1
    try:
        import customtkinter  # noqa: F401
    except ImportError:
        _avisar_erro("Falta instalar uma biblioteca",
                     "Não foi possível encontrar a biblioteca customtkinter.\n\n"
                     "Abra o terminal na pasta do programa e execute:\n"
                     "    pip install -r requirements.txt")
        return 1

    from farmacia.config import caminho_do_banco, pasta_de_dados
    from farmacia.contexto import Contexto

    pasta = pasta_de_dados()
    logging.basicConfig(filename=str(pasta / "farmacia.log"), level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        ctx = Contexto(caminho_do_banco())
    except Exception as erro:                       # banco corrompido, sem permissão, etc.
        logging.exception("Falha ao abrir o banco de dados")
        _avisar_erro("Não foi possível abrir o banco de dados",
                     f"{erro}\n\nArquivo: {caminho_do_banco()}\n\n"
                     "Se o problema continuar, restaure um backup ou contate quem mantém o sistema.")
        return 1

    from farmacia.ui.app import App
    app = App(ctx)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
