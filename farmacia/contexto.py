"""Reúne o banco e todos os serviços em um só objeto, usado pela interface e pelos testes."""
from __future__ import annotations

from pathlib import Path

from .banco import Banco
from .servicos.backup import BackupService
from .servicos.configuracoes import ConfiguracaoService
from .servicos.demonstracao import DemoService
from .servicos.estoque import EstoqueService
from .servicos.medicamentos import MedicamentoService
from .servicos.relatorios import RelatorioService


class Contexto:
    def __init__(self, caminho_banco: str | Path):
        self.caminho_banco = Path(caminho_banco)
        self.db = Banco(self.caminho_banco)
        self.config = ConfiguracaoService(self.db)
        self.estoque = EstoqueService(self.db)
        self.medicamentos = MedicamentoService(self.db, self.estoque)
        self.relatorios = RelatorioService(self.db, self.config, self.medicamentos, self.estoque)
        self.demo = DemoService(self.db, self.medicamentos, self.estoque)
        self.backup = BackupService(
            self.db, self.caminho_banco.parent / "copias_antes_de_restaurar")

    def fechar(self) -> None:
        self.db.fechar()
