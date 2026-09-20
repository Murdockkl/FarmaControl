"""Cadastro de medicamentos: criar, editar, excluir, consultar e pesquisar."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from ..banco import Banco
from ..config import DIAS_ALERTA_PADRAO, MOTIVO_ESTOQUE_INICIAL
from ..dominio import (ENTRADA, DuplicadoError, Medicamento, MedicamentoDados,
                       NaoEncontradoError)
from ..texto import (codigo, limpar_espacos, normalizar, padrao_like, rotulo_medicamento,
                     texto_localizacao)
from .estoque import EstoqueService

_FMT_DATA_HORA = "%Y-%m-%d %H:%M:%S"

# Situações usadas nos filtros da tela e dos relatórios.
SIT_TODOS = "todos"
SIT_BAIXO = "baixo"
SIT_SEM_ESTOQUE = "sem_estoque"
SIT_VENCIDO = "vencido"
SIT_PROXIMO = "proximo"
SIT_ALGUM_ALERTA = "alerta"

# Consulta base. A coluna `hay` reúne, sem acentos e em minúsculas, tudo o que pode
# ser pesquisado: nome, princípio ativo, genérico, laboratório, categoria, localização,
# lote, código, dosagem e forma farmacêutica.
_SQL_BASE = """
SELECT m.*,
       COALESCE(lab.nome, '')     AS laboratorio_nome,
       COALESCE(cat.nome, '')     AS categoria_nome,
       COALESCE(loc.setor, '')      AS loc_setor,
       COALESCE(loc.corredor, '')   AS loc_corredor,
       COALESCE(loc.estante, '')    AS loc_estante,
       COALESCE(loc.prateleira, '') AS loc_prateleira,
       COALESCE(loc.gaveta, '')     AS loc_gaveta,
       norm(m.nome || ' | ' || m.principio_ativo || ' | ' || m.nome_generico || ' | '
            || COALESCE(lab.nome, '') || ' | ' || COALESCE(cat.nome, '') || ' | '
            || COALESCE(loc.texto, '') || ' | ' || m.lote || ' | ' || printf('%05d', m.id)
            || ' | ' || m.dosagem || ' ' || m.unidade_medida || ' | ' || m.forma_farmaceutica
            || CASE WHEN m.eh_generico = 1 THEN ' | generico' ELSE '' END) AS hay
FROM medicamentos m
LEFT JOIN laboratorios  lab ON lab.id = m.laboratorio_id
LEFT JOIN categorias    cat ON cat.id = m.categoria_id
LEFT JOIN localizacoes  loc ON loc.id = m.localizacao_id
"""


def _data(texto: str | None) -> date | None:
    return date.fromisoformat(texto) if texto else None


def _data_hora(texto: str | None) -> datetime | None:
    return datetime.strptime(texto, _FMT_DATA_HORA) if texto else None


def _para_medicamento(r) -> Medicamento:
    return Medicamento(
        id=r["id"], nome=r["nome"], principio_ativo=r["principio_ativo"],
        nome_generico=r["nome_generico"], eh_generico=bool(r["eh_generico"]),
        laboratorio=r["laboratorio_nome"], categoria=r["categoria_nome"],
        dosagem=r["dosagem"], unidade_medida=r["unidade_medida"],
        forma_farmaceutica=r["forma_farmaceutica"],
        quantidade_atual=r["quantidade_atual"], estoque_minimo=r["estoque_minimo"],
        preco_compra_centavos=r["preco_compra_centavos"],
        preco_venda_centavos=r["preco_venda_centavos"],
        setor=r["loc_setor"], corredor=r["loc_corredor"], estante=r["loc_estante"],
        prateleira=r["loc_prateleira"], gaveta=r["loc_gaveta"], lote=r["lote"],
        data_fabricacao=_data(r["data_fabricacao"]), data_validade=_data(r["data_validade"]),
        observacoes=r["observacoes"], demo=bool(r["demo"]),
        criado_em=_data_hora(r["criado_em"]), atualizado_em=_data_hora(r["atualizado_em"]))


def _agora() -> str:
    return datetime.now().strftime(_FMT_DATA_HORA)


class MedicamentoService:
    def __init__(self, db: Banco, estoque: EstoqueService):
        self.db = db
        self.estoque = estoque

    # ------------------------------------------------------------------ criar
    def criar(self, dados: MedicamentoDados, *, registrar_estoque_inicial: bool = True,
              demo: bool = False) -> int:
        """Cadastra um medicamento e devolve o id.

        Se a quantidade inicial for maior que zero, registra automaticamente uma
        entrada "Estoque inicial" no histórico (assim o histórico sempre "fecha").
        """
        dados.validar_ou_levantar()
        with self.db.transacao() as conn:
            self._checar_duplicado(dados, ignorar_id=None)
            agora = _agora()
            quantidade_inicial = dados.quantidade_atual if registrar_estoque_inicial else 0
            cursor = conn.execute(
                """INSERT INTO medicamentos (
                    nome, principio_ativo, nome_generico, eh_generico, laboratorio_id, categoria_id,
                    dosagem, unidade_medida, forma_farmaceutica, quantidade_atual, estoque_minimo,
                    preco_compra_centavos, preco_venda_centavos, localizacao_id, lote,
                    data_fabricacao, data_validade, observacoes, demo, ativo, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (dados.nome, dados.principio_ativo, dados.nome_generico, int(dados.eh_generico),
                 self._obter_ou_criar("laboratorios", dados.laboratorio),
                 self._obter_ou_criar("categorias", dados.categoria),
                 dados.dosagem, dados.unidade_medida, dados.forma_farmaceutica,
                 dados.estoque_minimo, dados.preco_compra_centavos, dados.preco_venda_centavos,
                 self._obter_ou_criar_localizacao(dados), dados.lote,
                 dados.data_fabricacao.isoformat() if dados.data_fabricacao else None,
                 dados.data_validade.isoformat() if dados.data_validade else None,
                 dados.observacoes, int(demo), agora, agora))
            medicamento_id = cursor.lastrowid
            self._salvar_relacionados(medicamento_id, dados.relacionados)
            if quantidade_inicial > 0:
                self.estoque.registrar_movimentacao(
                    medicamento_id, ENTRADA, quantidade_inicial, MOTIVO_ESTOQUE_INICIAL,
                    "Quantidade informada no cadastro do medicamento")
        return medicamento_id

    # -------------------------------------------------------------- atualizar
    def atualizar(self, medicamento_id: int, dados: MedicamentoDados) -> None:
        """Edita os dados cadastrais. A quantidade NÃO muda aqui (use entrada/saída)."""
        dados.validar_ou_levantar()
        with self.db.transacao() as conn:
            existe = conn.execute("SELECT 1 FROM medicamentos WHERE id = ? AND ativo = 1",
                                  (medicamento_id,)).fetchone()
            if not existe:
                raise NaoEncontradoError("Medicamento não encontrado. Ele pode ter sido excluído.")
            self._checar_duplicado(dados, ignorar_id=medicamento_id)
            conn.execute(
                """UPDATE medicamentos SET
                    nome = ?, principio_ativo = ?, nome_generico = ?, eh_generico = ?,
                    laboratorio_id = ?, categoria_id = ?, dosagem = ?, unidade_medida = ?,
                    forma_farmaceutica = ?, estoque_minimo = ?, preco_compra_centavos = ?,
                    preco_venda_centavos = ?, localizacao_id = ?, lote = ?, data_fabricacao = ?,
                    data_validade = ?, observacoes = ?, atualizado_em = ?
                   WHERE id = ?""",
                (dados.nome, dados.principio_ativo, dados.nome_generico, int(dados.eh_generico),
                 self._obter_ou_criar("laboratorios", dados.laboratorio),
                 self._obter_ou_criar("categorias", dados.categoria),
                 dados.dosagem, dados.unidade_medida, dados.forma_farmaceutica,
                 dados.estoque_minimo, dados.preco_compra_centavos, dados.preco_venda_centavos,
                 self._obter_ou_criar_localizacao(dados), dados.lote,
                 dados.data_fabricacao.isoformat() if dados.data_fabricacao else None,
                 dados.data_validade.isoformat() if dados.data_validade else None,
                 dados.observacoes, _agora(), medicamento_id))
            self._salvar_relacionados(medicamento_id, dados.relacionados)

    # ---------------------------------------------------------------- excluir
    def excluir(self, medicamento_id: int) -> None:
        """Exclusão lógica: some das telas, mas o histórico de movimentações é preservado."""
        with self.db.transacao() as conn:
            existe = conn.execute("SELECT 1 FROM medicamentos WHERE id = ? AND ativo = 1",
                                  (medicamento_id,)).fetchone()
            if not existe:
                raise NaoEncontradoError("Medicamento não encontrado. Ele pode já ter sido excluído.")
            conn.execute("UPDATE medicamentos SET ativo = 0, atualizado_em = ? WHERE id = ?",
                         (_agora(), medicamento_id))
            conn.execute("DELETE FROM medicamentos_relacionados "
                         "WHERE medicamento_a = ? OR medicamento_b = ?",
                         (medicamento_id, medicamento_id))

    def contar_movimentacoes(self, medicamento_id: int) -> int:
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM movimentacoes WHERE medicamento_id = ?",
            (medicamento_id,)).fetchone()[0]

    # ---------------------------------------------------------------- consultar
    def obter(self, medicamento_id: int) -> Medicamento | None:
        """Um medicamento completo, incluindo a lista de medicamentos relacionados."""
        linha = self.db.conn.execute(
            f"SELECT * FROM ({_SQL_BASE}) WHERE id = ? AND ativo = 1", (medicamento_id,)).fetchone()
        if linha is None:
            return None
        med = _para_medicamento(linha)
        ids = self._ids_relacionados(medicamento_id)
        if ids:
            marcas = ",".join("?" * len(ids))
            linhas = self.db.conn.execute(
                f"SELECT * FROM ({_SQL_BASE}) WHERE id IN ({marcas}) AND ativo = 1 "
                "ORDER BY norm(nome), id", ids).fetchall()
            med.relacionados = [_para_medicamento(r) for r in linhas]
        return med

    def listar(self, busca: str = "", *, categoria: str | None = None,
               situacao: str = SIT_TODOS, dias_alerta: int = DIAS_ALERTA_PADRAO,
               hoje: date | None = None, limite: int | None = None,
               excluir_ids: tuple[int, ...] = ()) -> list[Medicamento]:
        """Lista medicamentos ativos, com pesquisa e filtros (ordenados por nome)."""
        hoje = hoje or date.today()
        where, params = ["ativo = 1"], []
        condicao, p = self._condicao_busca(busca)
        where.append(condicao)
        params += p
        if categoria:
            where.append("norm(categoria_nome) = ?")
            params.append(normalizar(categoria))
        cond_sit, p = self._condicao_situacao(situacao, hoje, dias_alerta)
        where.append(cond_sit)
        params += p
        if excluir_ids:
            where.append(f"id NOT IN ({','.join('?' * len(excluir_ids))})")
            params += list(excluir_ids)
        sql = f"SELECT * FROM ({_SQL_BASE}) WHERE {' AND '.join(where)} ORDER BY norm(nome), id"
        if limite:
            sql += f" LIMIT {int(limite)}"
        return [_para_medicamento(r) for r in self.db.conn.execute(sql, params)]

    def total(self) -> int:
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM medicamentos WHERE ativo = 1").fetchone()[0]

    def listar_categorias(self) -> list[str]:
        return [r[0] for r in self.db.conn.execute(
            "SELECT nome FROM categorias ORDER BY norm(nome)")]

    def listar_laboratorios(self) -> list[str]:
        return [r[0] for r in self.db.conn.execute(
            "SELECT nome FROM laboratorios ORDER BY norm(nome)")]

    def listar_setores(self) -> list[str]:
        return [r[0] for r in self.db.conn.execute(
            "SELECT DISTINCT setor FROM localizacoes WHERE setor <> '' ORDER BY norm(setor)")]

    # -------------------------------------------------- pesquisa e filtros (SQL)
    @staticmethod
    def _condicao_busca(busca: str) -> tuple[str, list]:
        """Monta a condição de pesquisa.

        1) o texto inteiro, como frase, é procurado em qualquer campo
           (assim "corredor a" encontra só o corredor A);
        2) se houver várias palavras (todas com 3+ letras), também aceita o
           medicamento que tenha todas elas em campos diferentes
           (ex.: "paracetamol 750").
        Se o texto for um número, também procura o código do medicamento.
        """
        q = normalizar(busca)
        if not q:
            return "1 = 1", []
        partes = ["hay LIKE ? ESCAPE '\\'"]
        params: list = [padrao_like(q)]
        palavras = q.split()
        if len(palavras) > 1 and all(len(p) >= 3 for p in palavras):
            partes.append("(" + " AND ".join("hay LIKE ? ESCAPE '\\'" for _ in palavras) + ")")
            params += [padrao_like(p) for p in palavras]
        if q.isdigit():
            partes.append("id = ?")
            params.append(int(q))
        return "(" + " OR ".join(partes) + ")", params

    @staticmethod
    def _condicao_situacao(situacao: str, hoje: date, dias: int) -> tuple[str, list]:
        limite = (hoje + timedelta(days=dias)).isoformat()
        hoje_iso = hoje.isoformat()
        vencido = ("(quantidade_atual > 0 AND data_validade IS NOT NULL AND data_validade < ?)",
                   [hoje_iso])
        proximo = ("(quantidade_atual > 0 AND data_validade >= ? AND data_validade <= ?)",
                   [hoje_iso, limite])
        if situacao == SIT_BAIXO:
            return "quantidade_atual <= estoque_minimo", []
        if situacao == SIT_SEM_ESTOQUE:
            return "quantidade_atual = 0", []
        if situacao == SIT_VENCIDO:
            return vencido
        if situacao == SIT_PROXIMO:
            return proximo
        if situacao == SIT_ALGUM_ALERTA:
            return (f"(quantidade_atual <= estoque_minimo OR {vencido[0]} OR {proximo[0]})",
                    vencido[1] + proximo[1])
        return "1 = 1", []

    # ------------------------------------------------------------ internos
    def _checar_duplicado(self, dados: MedicamentoDados, ignorar_id: int | None) -> None:
        """Bloqueia o cadastro repetido: mesmo nome, dosagem, forma, laboratório e lote."""
        linha = self.db.conn.execute(
            """SELECT m.id FROM medicamentos m
               LEFT JOIN laboratorios lab ON lab.id = m.laboratorio_id
               WHERE m.ativo = 1 AND norm(m.nome) = ? AND norm(m.dosagem) = ?
                 AND norm(m.unidade_medida) = ? AND norm(m.forma_farmaceutica) = ?
                 AND norm(COALESCE(lab.nome, '')) = ? AND norm(m.lote) = ?
                 AND m.id IS NOT ?
               LIMIT 1""",
            (normalizar(dados.nome), normalizar(dados.dosagem), normalizar(dados.unidade_medida),
             normalizar(dados.forma_farmaceutica), normalizar(dados.laboratorio),
             normalizar(dados.lote), ignorar_id)).fetchone()
        if linha:
            raise DuplicadoError(
                "Já existe um medicamento com o mesmo nome, dosagem, forma farmacêutica, "
                f"laboratório e lote (código {codigo(linha['id'])}). "
                "Para adicionar unidades a ele, use a opção Entrada de estoque.",
                existente_id=linha["id"])

    def _obter_ou_criar(self, tabela: str, nome: str) -> int | None:
        """Devolve o id de um laboratório/categoria (criando se ainda não existir)."""
        nome = limpar_espacos(nome)
        if not nome:
            return None
        conn = self.db.conn
        linha = conn.execute(f"SELECT id FROM {tabela} WHERE norm(nome) = ?",
                             (normalizar(nome),)).fetchone()
        if linha:
            return linha["id"]
        return conn.execute(f"INSERT INTO {tabela} (nome) VALUES (?)", (nome,)).lastrowid

    def _obter_ou_criar_localizacao(self, d: MedicamentoDados) -> int | None:
        campos = (d.setor, d.corredor, d.estante, d.prateleira, d.gaveta)
        if not any(campos):
            return None
        conn = self.db.conn
        linha = conn.execute(
            """SELECT id FROM localizacoes WHERE norm(setor) = ? AND norm(corredor) = ?
               AND norm(estante) = ? AND norm(prateleira) = ? AND norm(gaveta) = ?""",
            tuple(normalizar(c) for c in campos)).fetchone()
        if linha:
            return linha["id"]
        return conn.execute(
            "INSERT INTO localizacoes (setor, corredor, estante, prateleira, gaveta, texto) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (*campos, texto_localizacao(*campos))).lastrowid

    def _ids_relacionados(self, medicamento_id: int) -> list[int]:
        linhas = self.db.conn.execute(
            """SELECT CASE WHEN medicamento_a = ? THEN medicamento_b ELSE medicamento_a END AS outro
               FROM medicamentos_relacionados WHERE medicamento_a = ? OR medicamento_b = ?""",
            (medicamento_id,) * 3).fetchall()
        return [r["outro"] for r in linhas]

    def _salvar_relacionados(self, medicamento_id: int, ids: list[int]) -> None:
        conn = self.db.conn
        conn.execute("DELETE FROM medicamentos_relacionados "
                     "WHERE medicamento_a = ? OR medicamento_b = ?",
                     (medicamento_id, medicamento_id))
        for outro in dict.fromkeys(ids):               # remove repetidos, mantém a ordem
            if outro == medicamento_id:
                continue
            ativo = conn.execute("SELECT 1 FROM medicamentos WHERE id = ? AND ativo = 1",
                                 (outro,)).fetchone()
            if ativo:
                a, b = sorted((medicamento_id, outro))
                conn.execute("INSERT OR IGNORE INTO medicamentos_relacionados "
                             "(medicamento_a, medicamento_b) VALUES (?, ?)", (a, b))
