"""Modelos, exceções e regras de negócio simples (alertas de estoque e validade)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .config import LIMITE_CENTAVOS, LIMITE_QUANTIDADE
from .texto import (descricao_localizacao, descricao_localizacao_curta, limpar_espacos,
                    rotulo_medicamento, texto_localizacao)

# ------------------------------------------------------------------ constantes
ENTRADA = "ENTRADA"
SAIDA = "SAIDA"
TIPOS_MOVIMENTACAO = (ENTRADA, SAIDA)
ROTULO_TIPO = {ENTRADA: "Entrada", SAIDA: "Saída"}

ALERTA_VENCIDO = "vencido"
ALERTA_SEM_ESTOQUE = "sem_estoque"
ALERTA_ESTOQUE_BAIXO = "estoque_baixo"
ALERTA_PROXIMO_VENCIMENTO = "proximo_vencimento"
ROTULO_ALERTA = {
    ALERTA_VENCIDO: "Vencido",
    ALERTA_SEM_ESTOQUE: "Sem estoque",
    ALERTA_ESTOQUE_BAIXO: "Estoque baixo",
    ALERTA_PROXIMO_VENCIMENTO: "Vence em breve",
}


# ------------------------------------------------------------------- exceções
class FarmaciaError(Exception):
    """Erro esperado, com mensagem pronta para mostrar ao usuário."""


class ValidacaoError(FarmaciaError):
    def __init__(self, erros: dict[str, str] | str):
        if isinstance(erros, str):
            erros = {"_geral": erros}
        self.erros = erros
        super().__init__("\n".join(erros.values()))


class EstoqueInsuficienteError(FarmaciaError):
    pass


class DuplicadoError(FarmaciaError):
    def __init__(self, mensagem: str, existente_id: int):
        super().__init__(mensagem)
        self.existente_id = existente_id


class NaoEncontradoError(FarmaciaError):
    pass


class BackupError(FarmaciaError):
    pass


# ---------------------------------------------------------------------- alertas
def calcular_alertas(quantidade: int, minimo: int, validade: date | None,
                     hoje: date, dias_alerta: int) -> list[str]:
    """Lista de alertas do medicamento, do mais grave para o menos grave.

    Regras:
      * estoque baixo: quantidade atual <= estoque mínimo (sem estoque quando = 0);
      * vencido / próximo do vencimento: só valem se ainda existem unidades.
    """
    alertas: list[str] = []
    if quantidade > 0 and validade is not None:
        if validade < hoje:
            alertas.append(ALERTA_VENCIDO)
        elif validade <= hoje + timedelta(days=dias_alerta):
            alertas.append(ALERTA_PROXIMO_VENCIMENTO)
    if quantidade == 0:
        alertas.append(ALERTA_SEM_ESTOQUE)
    elif quantidade <= minimo:
        alertas.append(ALERTA_ESTOQUE_BAIXO)
    ordem = [ALERTA_VENCIDO, ALERTA_SEM_ESTOQUE, ALERTA_ESTOQUE_BAIXO, ALERTA_PROXIMO_VENCIMENTO]
    return sorted(alertas, key=ordem.index)


# ------------------------------------------------------- dados de entrada (form)
@dataclass
class MedicamentoDados:
    """Dados de um medicamento já convertidos (números, datas), prontos para salvar."""
    nome: str = ""
    principio_ativo: str = ""
    nome_generico: str = ""
    eh_generico: bool = False
    laboratorio: str = ""
    categoria: str = ""
    dosagem: str = ""
    unidade_medida: str = ""
    forma_farmaceutica: str = ""
    quantidade_atual: int = 0
    estoque_minimo: int = 0
    preco_compra_centavos: int = 0
    preco_venda_centavos: int = 0
    setor: str = ""
    corredor: str = ""
    estante: str = ""
    prateleira: str = ""
    gaveta: str = ""
    lote: str = ""
    data_fabricacao: date | None = None
    data_validade: date | None = None
    observacoes: str = ""
    relacionados: list[int] = field(default_factory=list)

    _CAMPOS_TEXTO = ("nome", "principio_ativo", "nome_generico", "laboratorio", "categoria",
                     "dosagem", "unidade_medida", "forma_farmaceutica", "setor", "corredor",
                     "estante", "prateleira", "gaveta", "lote")

    def normalizar(self) -> None:
        """Tira espaços sobrando dos campos de texto."""
        for campo in self._CAMPOS_TEXTO:
            setattr(self, campo, limpar_espacos(getattr(self, campo)))
        self.observacoes = (self.observacoes or "").strip()

    def validar(self, hoje: date | None = None) -> dict[str, str]:
        """Devolve {campo: mensagem}. Dicionário vazio = tudo certo."""
        hoje = hoje or date.today()
        erros: dict[str, str] = {}
        if not limpar_espacos(self.nome):
            erros["nome"] = "Informe o nome do medicamento."
        elif len(self.nome) > 150:
            erros["nome"] = "O nome pode ter no máximo 150 caracteres."
        if not limpar_espacos(self.principio_ativo):
            erros["principio_ativo"] = "Informe o princípio ativo."
        elif len(self.principio_ativo) > 150:
            erros["principio_ativo"] = "O princípio ativo pode ter no máximo 150 caracteres."
        if not 0 <= self.quantidade_atual <= LIMITE_QUANTIDADE:
            erros["quantidade_atual"] = "A quantidade deve ser um número inteiro, sem negativos."
        if not 0 <= self.estoque_minimo <= LIMITE_QUANTIDADE:
            erros["estoque_minimo"] = "O estoque mínimo deve ser um número inteiro, sem negativos."
        if not 0 <= self.preco_compra_centavos <= LIMITE_CENTAVOS:
            erros["preco_compra"] = "Informe um preço de compra válido (ex.: 4,50)."
        if not 0 <= self.preco_venda_centavos <= LIMITE_CENTAVOS:
            erros["preco_venda"] = "Informe um preço de venda válido (ex.: 8,90)."
        if self.data_fabricacao and self.data_fabricacao > hoje:
            erros["data_fabricacao"] = "A data de fabricação não pode estar no futuro."
        if self.data_fabricacao and self.data_validade and self.data_validade < self.data_fabricacao:
            erros["data_validade"] = "A validade não pode ser anterior à data de fabricação."
        for campo, limite in (("dosagem", 40), ("unidade_medida", 30), ("forma_farmaceutica", 60),
                              ("laboratorio", 100), ("categoria", 60), ("lote", 40),
                              ("nome_generico", 150)):
            if len(getattr(self, campo)) > limite:
                erros.setdefault(campo, f"Use no máximo {limite} caracteres.")
        return erros

    def validar_ou_levantar(self, hoje: date | None = None) -> None:
        self.normalizar()
        erros = self.validar(hoje)
        if erros:
            raise ValidacaoError(erros)


# ---------------------------------------------------------------- modelos de leitura
@dataclass
class Medicamento:
    id: int
    nome: str
    principio_ativo: str
    nome_generico: str
    eh_generico: bool
    laboratorio: str
    categoria: str
    dosagem: str
    unidade_medida: str
    forma_farmaceutica: str
    quantidade_atual: int
    estoque_minimo: int
    preco_compra_centavos: int
    preco_venda_centavos: int
    setor: str
    corredor: str
    estante: str
    prateleira: str
    gaveta: str
    lote: str
    data_fabricacao: date | None
    data_validade: date | None
    observacoes: str
    demo: bool
    criado_em: datetime | None = None
    atualizado_em: datetime | None = None
    relacionados: list["Medicamento"] = field(default_factory=list)

    # -- textos prontos ------------------------------------------------------
    @property
    def dosagem_completa(self) -> str:
        return f"{self.dosagem} {self.unidade_medida}".strip()

    @property
    def rotulo(self) -> str:
        """Nome com a dosagem (sem repetir), para listas e históricos."""
        return rotulo_medicamento(self.nome, self.dosagem, self.unidade_medida)

    @property
    def localizacao(self) -> str:
        return descricao_localizacao(self.setor, self.corredor, self.estante,
                                     self.prateleira, self.gaveta)

    @property
    def localizacao_curta(self) -> str:
        return descricao_localizacao_curta(self.setor, self.corredor, self.estante,
                                           self.prateleira, self.gaveta)

    @property
    def localizacao_completa(self) -> str:
        return descricao_localizacao(self.setor, self.corredor, self.estante,
                                     self.prateleira, self.gaveta, incluir_setor=True)

    @property
    def localizacao_busca(self) -> str:
        return texto_localizacao(self.setor, self.corredor, self.estante,
                                 self.prateleira, self.gaveta)

    # -- valores ---------------------------------------------------------------
    @property
    def valor_custo_centavos(self) -> int:
        return self.quantidade_atual * self.preco_compra_centavos

    @property
    def valor_venda_centavos(self) -> int:
        return self.quantidade_atual * self.preco_venda_centavos

    # -- alertas -------------------------------------------------------------
    def alertas(self, hoje: date, dias_alerta: int) -> list[str]:
        return calcular_alertas(self.quantidade_atual, self.estoque_minimo,
                                self.data_validade, hoje, dias_alerta)

    def dias_para_vencer(self, hoje: date) -> int | None:
        return (self.data_validade - hoje).days if self.data_validade else None


@dataclass
class Movimentacao:
    id: int
    medicamento_id: int
    medicamento: str            # nome (com dosagem) para exibição
    excluido: bool              # o medicamento foi excluído do cadastro depois
    tipo: str
    quantidade: int
    estoque_anterior: int
    estoque_posterior: int
    motivo: str
    observacao: str
    data_hora: datetime

    @property
    def quantidade_com_sinal(self) -> int:
        return self.quantidade if self.tipo == ENTRADA else -self.quantidade

    @property
    def rotulo_tipo(self) -> str:
        return ROTULO_TIPO.get(self.tipo, self.tipo)


@dataclass
class Resumo:
    total_medicamentos: int = 0
    total_unidades: int = 0
    estoque_baixo: int = 0
    vencidos: int = 0
    proximos_vencimento: int = 0
    valor_custo_centavos: int = 0
    valor_venda_centavos: int = 0
    dias_alerta: int = 30
