"""Acesso ao SQLite: conexão, criação das tabelas, transações e cópia do banco.

O banco é um único arquivo (.db). Nada de servidor: o Python já inclui o SQLite.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .dominio import BackupError
from .texto import normalizar

VERSAO_ESQUEMA = 1

# Cada item é um comando SQL. Ao evoluir o sistema, crie uma nova entrada em
# MIGRACOES (versão -> lista de comandos) sem mexer nas antigas.
_ESQUEMA_V1 = [
    """CREATE TABLE categorias (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE COLLATE NOCASE
    )""",
    """CREATE TABLE laboratorios (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE COLLATE NOCASE
    )""",
    """CREATE TABLE localizacoes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        setor      TEXT NOT NULL DEFAULT '',
        corredor   TEXT NOT NULL DEFAULT '',
        estante    TEXT NOT NULL DEFAULT '',
        prateleira TEXT NOT NULL DEFAULT '',
        gaveta     TEXT NOT NULL DEFAULT '',
        texto      TEXT NOT NULL DEFAULT '',          -- usado na busca
        UNIQUE (setor, corredor, estante, prateleira, gaveta)
    )""",
    """CREATE TABLE medicamentos (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        nome                  TEXT    NOT NULL CHECK (length(trim(nome)) > 0),
        principio_ativo       TEXT    NOT NULL CHECK (length(trim(principio_ativo)) > 0),
        nome_generico         TEXT    NOT NULL DEFAULT '',
        eh_generico           INTEGER NOT NULL DEFAULT 0 CHECK (eh_generico IN (0, 1)),
        laboratorio_id        INTEGER REFERENCES laboratorios (id),
        categoria_id          INTEGER REFERENCES categorias (id),
        dosagem               TEXT    NOT NULL DEFAULT '',
        unidade_medida        TEXT    NOT NULL DEFAULT '',
        forma_farmaceutica    TEXT    NOT NULL DEFAULT '',
        quantidade_atual      INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_atual >= 0),
        estoque_minimo        INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
        preco_compra_centavos INTEGER NOT NULL DEFAULT 0 CHECK (preco_compra_centavos >= 0),
        preco_venda_centavos  INTEGER NOT NULL DEFAULT 0 CHECK (preco_venda_centavos >= 0),
        localizacao_id        INTEGER REFERENCES localizacoes (id),
        lote                  TEXT    NOT NULL DEFAULT '',
        data_fabricacao       TEXT,                   -- AAAA-MM-DD
        data_validade         TEXT,                   -- AAAA-MM-DD
        observacoes           TEXT    NOT NULL DEFAULT '',
        demo                  INTEGER NOT NULL DEFAULT 0 CHECK (demo IN (0, 1)),
        ativo                 INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
        criado_em             TEXT    NOT NULL,
        atualizado_em         TEXT    NOT NULL
    )""",
    "CREATE INDEX idx_medicamentos_ativo_nome ON medicamentos (ativo, nome)",
    "CREATE INDEX idx_medicamentos_validade ON medicamentos (data_validade)",
    """CREATE TABLE medicamentos_relacionados (
        medicamento_a INTEGER NOT NULL REFERENCES medicamentos (id) ON DELETE CASCADE,
        medicamento_b INTEGER NOT NULL REFERENCES medicamentos (id) ON DELETE CASCADE,
        PRIMARY KEY (medicamento_a, medicamento_b),
        CHECK (medicamento_a < medicamento_b)          -- um par = uma linha
    )""",
    """CREATE TABLE movimentacoes (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        medicamento_id    INTEGER NOT NULL REFERENCES medicamentos (id),
        medicamento_nome  TEXT    NOT NULL,           -- nome no momento da movimentação
        tipo              TEXT    NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
        quantidade        INTEGER NOT NULL CHECK (quantidade > 0),
        estoque_anterior  INTEGER NOT NULL CHECK (estoque_anterior >= 0),
        estoque_posterior INTEGER NOT NULL CHECK (estoque_posterior >= 0),
        motivo            TEXT    NOT NULL,
        observacao        TEXT    NOT NULL DEFAULT '',
        data_hora         TEXT    NOT NULL,           -- AAAA-MM-DD HH:MM:SS (hora local)
        CHECK ((tipo = 'ENTRADA' AND estoque_posterior = estoque_anterior + quantidade)
            OR (tipo = 'SAIDA'   AND estoque_posterior = estoque_anterior - quantidade))
    )""",
    "CREATE INDEX idx_movimentacoes_data ON movimentacoes (data_hora)",
    "CREATE INDEX idx_movimentacoes_med ON movimentacoes (medicamento_id)",
    """CREATE TABLE configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    )""",
]

MIGRACOES: dict[int, list[str]] = {1: _ESQUEMA_V1}

_TABELAS_OBRIGATORIAS = {"medicamentos", "movimentacoes", "configuracoes",
                         "categorias", "laboratorios", "localizacoes"}


class Banco:
    """Uma conexão SQLite com ajustes de segurança (chaves estrangeiras) e busca sem acento."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._profundidade = 0
        self.conn = self._abrir()
        self.migrar()

    # ------------------------------------------------------------------ conexão
    def _abrir(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.caminho), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = None               # transações controladas por transacao()
        conn.create_function("norm", 1, normalizar, deterministic=True)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def fechar(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # ---------------------------------------------------------------- transações
    @contextmanager
    def transacao(self):
        """Tudo dentro do bloco é gravado junto, ou nada é gravado (se houver erro).

        Pode ser aninhada: só a transação mais externa faz o COMMIT.
        """
        if self._profundidade == 0:
            self.conn.execute("BEGIN IMMEDIATE")
        self._profundidade += 1
        try:
            yield self.conn
        except BaseException:
            self._profundidade -= 1
            if self._profundidade == 0:
                self.conn.execute("ROLLBACK")
            raise
        else:
            self._profundidade -= 1
            if self._profundidade == 0:
                self.conn.execute("COMMIT")

    # ------------------------------------------------------------------ esquema
    def versao(self) -> int:
        return self.conn.execute("PRAGMA user_version").fetchone()[0]

    def migrar(self) -> None:
        """Cria as tabelas na primeira execução e aplica melhorias de versões futuras."""
        atual = self.versao()
        for versao in sorted(MIGRACOES):
            if versao > atual:
                with self.transacao():
                    for comando in MIGRACOES[versao]:
                        self.conn.execute(comando)
                    self.conn.execute(f"PRAGMA user_version = {int(versao)}")

    # ------------------------------------------------------------- cópia / backup
    def copiar_para(self, destino: str | Path) -> None:
        """Cópia consistente do banco (segura mesmo com o programa aberto)."""
        destino = Path(destino)
        temporario = destino.with_name(destino.name + ".tmp")
        if temporario.exists():
            temporario.unlink()
        copia = sqlite3.connect(str(temporario))
        try:
            self.conn.backup(copia)
        finally:
            copia.close()
        temporario.replace(destino)

    @staticmethod
    def validar_arquivo(origem: str | Path) -> None:
        """Confere se o arquivo é um banco do FarmaControl íntegro e compatível."""
        origem = Path(origem)
        if not origem.is_file():
            raise BackupError("O arquivo selecionado não foi encontrado.")
        try:
            conn = sqlite3.connect(origem.resolve().as_uri() + "?mode=ro", uri=True)
        except sqlite3.Error:
            raise BackupError("Não foi possível abrir o arquivo selecionado.") from None
        try:
            try:
                if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise BackupError("O arquivo de backup está corrompido.")
                tabelas = {r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'")}
                versao = conn.execute("PRAGMA user_version").fetchone()[0]
            except sqlite3.DatabaseError:
                raise BackupError("O arquivo selecionado não é um banco de dados válido.") from None
        finally:
            conn.close()
        if not _TABELAS_OBRIGATORIAS <= tabelas:
            raise BackupError("Este arquivo não é um backup do FarmaControl "
                              "(faltam tabelas do sistema).")
        if versao > VERSAO_ESQUEMA:
            raise BackupError("Este backup foi criado por uma versão mais nova do programa. "
                              "Atualize o programa antes de restaurá-lo.")

    def substituir_por(self, origem: str | Path) -> None:
        """Troca TODO o conteúdo do banco atual pelo conteúdo do arquivo informado."""
        origem = Path(origem)
        self.validar_arquivo(origem)
        origem_conn = sqlite3.connect(origem.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            origem_conn.backup(self.conn)
        finally:
            origem_conn.close()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.migrar()
