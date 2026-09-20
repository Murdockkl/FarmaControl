"""Backup e restauração do banco de dados (arquivo .db)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..banco import Banco
from ..dominio import BackupError


class BackupService:
    def __init__(self, db: Banco, pasta_seguranca: Path):
        self.db = db
        self.pasta_seguranca = Path(pasta_seguranca)

    @staticmethod
    def nome_sugerido() -> str:
        return f"farmacia_backup_{datetime.now():%Y-%m-%d_%H%M}.db"

    def criar_backup(self, destino: str | Path) -> Path:
        """Salva uma cópia completa do banco no caminho escolhido pelo usuário."""
        destino = Path(destino)
        if destino.resolve() == self.db.caminho.resolve():
            raise BackupError("Escolha um local diferente do banco de dados em uso.")
        try:
            self.db.copiar_para(destino)
        except OSError as e:
            raise BackupError(f"Não foi possível salvar o backup: {e.strerror or e}") from e
        return destino

    def restaurar(self, origem: str | Path) -> Path:
        """Substitui os dados atuais pelo conteúdo do backup.

        Antes de substituir, guarda automaticamente uma cópia dos dados atuais
        (pasta "copias_antes_de_restaurar"), para que nada se perca por engano.
        Devolve o caminho dessa cópia de segurança.
        """
        origem = Path(origem)
        self.db.validar_arquivo(origem)                 # confere antes de mexer em qualquer coisa
        if origem.resolve() == self.db.caminho.resolve():
            raise BackupError("O arquivo escolhido é o próprio banco em uso.")
        self.pasta_seguranca.mkdir(parents=True, exist_ok=True)
        copia = self.pasta_seguranca / f"antes_de_restaurar_{datetime.now():%Y-%m-%d_%H%M%S}.db"
        try:
            self.db.copiar_para(copia)
            self.db.substituir_por(origem)
        except OSError as e:
            raise BackupError(f"Não foi possível restaurar o backup: {e.strerror or e}") from e
        return copia
