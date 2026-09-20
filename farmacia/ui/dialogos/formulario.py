"""Janela de cadastro e edição de medicamentos."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ...config import FORMAS_FARMACEUTICAS, UNIDADES_MEDIDA
from ...dominio import DuplicadoError, FarmaciaError, Medicamento, MedicamentoDados, ValidacaoError
from ...texto import codigo, fmt_data, fmt_numero_decimal
from ...validacao import converter_data, converter_dinheiro, converter_inteiro
from ..tema import COR, botao, fonte
from ..widgets import Cartao, Col, TabelaDados, limpar_entrada, titulo_secao
from .base import Dialogo

_ROTULOS = {
    "nome": "Nome do medicamento", "principio_ativo": "Princípio ativo",
    "nome_generico": "Nome genérico", "laboratorio": "Laboratório", "categoria": "Categoria",
    "dosagem": "Dosagem", "unidade_medida": "Unidade de medida",
    "forma_farmaceutica": "Forma farmacêutica", "quantidade_atual": "Quantidade atual",
    "estoque_minimo": "Estoque mínimo", "preco_compra": "Preço de compra",
    "preco_venda": "Preço de venda", "setor": "Setor", "corredor": "Corredor",
    "estante": "Estante", "prateleira": "Prateleira", "gaveta": "Gaveta", "lote": "Lote",
    "data_fabricacao": "Data de fabricação", "data_validade": "Data de validade",
}


class SeletorRelacionados(ctk.CTkFrame):
    """Escolha de medicamentos semelhantes/de referência entre os já cadastrados."""

    def __init__(self, master, app, ignorar_id: int | None, iniciais: list[Medicamento]):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.ignorar_id = ignorar_id
        self.selecionados: dict[int, Medicamento] = {m.id: m for m in iniciais}
        self._resultados: dict[str, Medicamento] = {}
        self._agendado = None
        self.columnconfigure(0, weight=1)

        self.busca = ctk.CTkEntry(
            self, height=36, font=fonte(13), corner_radius=8, border_color=COR.borda,
            fg_color=COR.cartao, placeholder_text="Pesquise um medicamento já cadastrado para relacionar")
        self.busca.grid(row=0, column=0, sticky="ew")
        self.busca.bind("<KeyRelease>", self._digitou, add="+")

        self.tabela = TabelaDados(
            self, [Col("nome", "Medicamento", 250), Col("ativo", "Princípio ativo", 160),
                   Col("local", "Localização", 200)],
            altura=4, ao_abrir=lambda _iid: self._adicionar(), ordenavel=False,
            mensagem_vazia="Nenhum medicamento encontrado.")
        self.botao_adicionar = botao(self, "Adicionar à lista", self._adicionar, tipo="suave", altura=32)

        self.lista = ctk.CTkFrame(self, fg_color=COR.linha, corner_radius=8)
        self.lista.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self._desenhar_lista()

    # -- pesquisa ----------------------------------------------------------------
    def _digitou(self, _e=None):
        if self._agendado:
            self.after_cancel(self._agendado)
        self._agendado = self.after(250, self._pesquisar)

    def _pesquisar(self):
        self._agendado = None
        texto = self.busca.get().strip()
        if len(texto) < 2:
            self.tabela.grid_remove()
            self.botao_adicionar.grid_remove()
            return
        excluir = tuple(self.selecionados) + ((self.ignorar_id,) if self.ignorar_id else ())
        achados = self.app.ctx.medicamentos.listar(texto, limite=30, excluir_ids=excluir)
        self._resultados = {str(m.id): m for m in achados}
        self.tabela.definir_linhas([
            {"iid": m.id, "valores": {"nome": m.rotulo, "ativo": m.principio_ativo,
                                      "local": m.localizacao_curta}} for m in achados])
        self.tabela.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.botao_adicionar.grid(row=2, column=0, sticky="e", pady=(6, 0))

    def _adicionar(self):
        iid = self.tabela.selecionado()
        med = self._resultados.get(iid) if iid else None
        if not med:
            return
        self.selecionados[med.id] = med
        limpar_entrada(self.busca)
        self._pesquisar()
        self._desenhar_lista()

    def _remover(self, med_id: int):
        self.selecionados.pop(med_id, None)
        self._desenhar_lista()

    def _desenhar_lista(self):
        for w in self.lista.winfo_children():
            w.destroy()
        if not self.selecionados:
            ctk.CTkLabel(self.lista, text="Nenhum medicamento relacionado.", font=fonte(12),
                         text_color=COR.texto_suave).pack(anchor="w", padx=12, pady=8)
            return
        for med in self.selecionados.values():
            linha = ctk.CTkFrame(self.lista, fg_color="transparent")
            linha.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(linha, text=f"{med.rotulo}  ·  {med.principio_ativo}", font=fonte(13),
                         text_color=COR.texto, anchor="w").pack(side="left", padx=(4, 0))
            ctk.CTkButton(linha, text="Remover", width=70, height=24, font=fonte(12),
                          fg_color="transparent", hover_color=COR.perigo_fundo,
                          text_color=COR.perigo,
                          command=lambda i=med.id: self._remover(i)).pack(side="right")

    def obter_ids(self) -> list[int]:
        return list(self.selecionados)


class DialogoFormulario(Dialogo):
    """Cadastro (medicamento_id=None) ou edição de um medicamento."""

    def __init__(self, app, medicamento_id: int | None = None,
                 ao_salvar: Callable[[int], None] | None = None):
        self.medicamento_id = medicamento_id
        self.editando = medicamento_id is not None
        self.med = app.ctx.medicamentos.obter(medicamento_id) if self.editando else None
        titulo = "Editar medicamento" if self.editando else "Novo medicamento"
        super().__init__(app, titulo, 900, 780)
        self.ao_salvar = ao_salvar
        self.campos: dict[str, ctk.CTkBaseClass] = {}

        # ----- cabeçalho
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=26, pady=(20, 6))
        ctk.CTkLabel(topo, text=titulo, font=fonte(22, "bold"), text_color=COR.texto).pack(anchor="w")
        subtitulo = (f"{self.med.rotulo}  ·  código {codigo(self.med.id)}" if self.med else
                     "Campos com * são obrigatórios. Todos os outros podem ser preenchidos depois.")
        ctk.CTkLabel(topo, text=subtitulo, font=fonte(13), text_color=COR.texto_suave).pack(anchor="w")

        self.banner = ctk.CTkFrame(topo, fg_color=COR.perigo_fundo, corner_radius=8)
        self.banner_texto = ctk.CTkLabel(self.banner, text="", font=fonte(13), text_color=COR.perigo,
                                         anchor="w", justify="left", wraplength=780)
        self.banner_texto.pack(fill="x", padx=14, pady=10)

        # ----- rodapé fixo (criado antes da área rolável para ficar sempre visível)
        rodape = ctk.CTkFrame(self, fg_color=COR.cartao, corner_radius=0)
        rodape.pack(side="bottom", fill="x")
        botao(rodape, "Salvar alterações" if self.editando else "Salvar medicamento",
              self.salvar, largura=190, altura=40).pack(side="right", padx=(8, 26), pady=14)
        botao(rodape, "Cancelar", self.fechar, tipo="secundario", largura=110, altura=40).pack(
            side="right", pady=14)

        self.rolagem = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rolagem.pack(fill="both", expand=True, padx=(18, 10), pady=(0, 0))
        self._montar_secoes()
        if self.med:
            self._preencher(self.med)
        self.exibir()
        self.after(150, lambda: self.campos["nome"].focus_set())

    # ------------------------------------------------------------------ construção
    def _secao(self, titulo: str) -> ctk.CTkFrame:
        cartao = Cartao(self.rolagem)
        cartao.pack(fill="x", padx=8, pady=(6, 8))
        titulo_secao(cartao, titulo).pack(anchor="w", padx=20, pady=(14, 2))
        grade = ctk.CTkFrame(cartao, fg_color="transparent")
        grade.pack(fill="x", padx=12, pady=(0, 14))
        for c in range(3):
            grade.columnconfigure(c, weight=1, uniform="col")
        return grade

    def _campo(self, grade, chave: str, rotulo: str, linha: int, coluna: int, *, span: int = 1,
               tipo: str = "entrada", valores: list[str] | None = None, dica: str = "",
               obrigatorio: bool = False):
        celula = ctk.CTkFrame(grade, fg_color="transparent")
        celula.grid(row=linha, column=coluna, columnspan=span, sticky="new", padx=8, pady=(6, 4))
        ctk.CTkLabel(celula, text=rotulo + (" *" if obrigatorio else ""), font=fonte(12),
                     text_color=COR.texto_suave, anchor="w").pack(anchor="w")
        if tipo == "combo":
            w = ctk.CTkComboBox(celula, values=valores or [""], height=36, font=fonte(13),
                                dropdown_font=fonte(13), corner_radius=8, border_color=COR.borda,
                                fg_color=COR.cartao, button_color=COR.borda,
                                button_hover_color="#C5D3D0", text_color=COR.texto,
                                dropdown_text_color=COR.texto, dropdown_fg_color=COR.cartao,
                                dropdown_hover_color=COR.primaria_suave)
            w.set("")
        elif tipo == "texto":
            w = ctk.CTkTextbox(celula, height=76, font=fonte(13), corner_radius=8, border_width=1,
                               border_color=COR.borda, fg_color=COR.cartao, text_color=COR.texto)
        else:
            w = ctk.CTkEntry(celula, height=36, font=fonte(13), corner_radius=8,
                             border_color=COR.borda, fg_color=COR.cartao, text_color=COR.texto,
                             placeholder_text=dica)
        w.pack(fill="x", pady=(2, 0))
        self.campos[chave] = w
        return celula

    def _montar_secoes(self) -> None:
        ctx = self.app.ctx
        # -- informações principais
        g = self._secao("Informações principais")
        self._campo(g, "nome", "Nome do medicamento", 0, 0, span=2, obrigatorio=True,
                    dica="Ex.: Paracetamol 750 mg")
        self._campo(g, "laboratorio", "Laboratório / fabricante", 0, 2, tipo="combo",
                    valores=ctx.medicamentos.listar_laboratorios() or [""])
        self._campo(g, "principio_ativo", "Princípio ativo", 1, 0, span=2, obrigatorio=True,
                    dica="Ex.: Paracetamol")
        self._campo(g, "categoria", "Categoria", 1, 2, tipo="combo",
                    valores=ctx.medicamentos.listar_categorias() or [""])
        self._campo(g, "dosagem", "Dosagem", 2, 0, dica="Ex.: 750")
        self._campo(g, "unidade_medida", "Unidade de medida", 2, 1, tipo="combo",
                    valores=UNIDADES_MEDIDA)
        self._campo(g, "forma_farmaceutica", "Forma farmacêutica", 2, 2, tipo="combo",
                    valores=FORMAS_FARMACEUTICAS)

        # -- estoque e preços
        g = self._secao("Estoque e preços")
        c = self._campo(g, "quantidade_atual", "Quantidade atual", 0, 0, dica="Ex.: 20")
        self._campo(g, "estoque_minimo", "Estoque mínimo", 0, 1, dica="Ex.: 10")
        self._campo(g, "preco_compra", "Preço de compra (R$)", 1, 0, dica="Ex.: 4,50")
        self._campo(g, "preco_venda", "Preço de venda (R$)", 1, 1, dica="Ex.: 8,90")
        if self.editando:
            ctk.CTkLabel(c, text="Para alterar o estoque, use Entrada ou Saída.", font=fonte(11),
                         text_color=COR.texto_suave, anchor="w").pack(anchor="w")
        else:
            ctk.CTkLabel(c, text="Registra uma entrada de \"Estoque inicial\".", font=fonte(11),
                         text_color=COR.texto_suave, anchor="w").pack(anchor="w")

        # -- localização
        g = self._secao("Localização na farmácia")
        self._campo(g, "setor", "Setor", 0, 0, tipo="combo",
                    valores=ctx.medicamentos.listar_setores() or ["Medicamentos"])
        self._campo(g, "corredor", "Corredor", 0, 1, dica="Ex.: A")
        self._campo(g, "estante", "Estante", 0, 2, dica="Ex.: 02")
        self._campo(g, "prateleira", "Prateleira", 1, 0, dica="Ex.: 03")
        self._campo(g, "gaveta", "Gaveta", 1, 1, dica="Ex.: 1 (se houver)")

        # -- lote e validade
        g = self._secao("Lote e validade")
        self._campo(g, "lote", "Lote", 0, 0, dica="Ex.: L001")
        self._campo(g, "data_fabricacao", "Data de fabricação", 0, 1, dica="dd/mm/aaaa ou mm/aaaa")
        self._campo(g, "data_validade", "Data de validade", 0, 2, dica="dd/mm/aaaa ou mm/aaaa")

        # -- informações farmacêuticas
        g = self._secao("Informações farmacêuticas")
        celula = ctk.CTkFrame(g, fg_color="transparent")
        celula.grid(row=0, column=0, sticky="ew", padx=8, pady=(20, 4))
        self.chave_generico = ctk.CTkSwitch(celula, text="É um medicamento genérico", font=fonte(13),
                                            text_color=COR.texto, progress_color=COR.primaria)
        self.chave_generico.pack(anchor="w")
        self._campo(g, "nome_generico", "Nome genérico correspondente", 0, 1, span=2,
                    dica="Ex.: Paracetamol 750 mg Genérico")
        celula = ctk.CTkFrame(g, fg_color="transparent")
        celula.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(celula, text="Medicamentos semelhantes / referências", font=fonte(12),
                     text_color=COR.texto_suave, anchor="w").pack(anchor="w")
        ctk.CTkLabel(celula, text="Somente o que você cadastrar aqui é considerado relacionado. "
                                  "O sistema não sugere equivalências por conta própria.",
                     font=fonte(11), text_color=COR.texto_suave, anchor="w").pack(anchor="w", pady=(0, 4))
        self.seletor = SeletorRelacionados(
            celula, self.app, self.medicamento_id, self.med.relacionados if self.med else [])
        self.seletor.pack(fill="x")
        self._campo(g, "observacoes", "Observações", 2, 0, span=3, tipo="texto")

    def _preencher(self, m: Medicamento) -> None:
        valores = {
            "nome": m.nome, "principio_ativo": m.principio_ativo, "nome_generico": m.nome_generico,
            "laboratorio": m.laboratorio, "categoria": m.categoria, "dosagem": m.dosagem,
            "unidade_medida": m.unidade_medida, "forma_farmaceutica": m.forma_farmaceutica,
            "quantidade_atual": str(m.quantidade_atual), "estoque_minimo": str(m.estoque_minimo),
            "preco_compra": fmt_numero_decimal(m.preco_compra_centavos),
            "preco_venda": fmt_numero_decimal(m.preco_venda_centavos),
            "setor": m.setor, "corredor": m.corredor, "estante": m.estante,
            "prateleira": m.prateleira, "gaveta": m.gaveta, "lote": m.lote,
            "data_fabricacao": fmt_data(m.data_fabricacao, ""),
            "data_validade": fmt_data(m.data_validade, ""), "observacoes": m.observacoes,
        }
        for chave, texto in valores.items():
            self._definir(chave, texto)
        if m.eh_generico:
            self.chave_generico.select()
        self.campos["quantidade_atual"].configure(state="disabled")     # só via Entrada/Saída

    # ------------------------------------------------------------------- leitura
    def _definir(self, chave: str, texto: str) -> None:
        w = self.campos[chave]
        if isinstance(w, ctk.CTkTextbox):
            w.delete("1.0", "end")
            w.insert("1.0", texto)
        elif isinstance(w, ctk.CTkComboBox):
            w.set(texto)
        else:
            if texto:
                w.delete(0, "end")
                w.insert(0, texto)
            else:
                limpar_entrada(w)

    def _texto(self, chave: str) -> str:
        w = self.campos[chave]
        if isinstance(w, ctk.CTkTextbox):
            return w.get("1.0", "end").strip()
        return w.get().strip()

    def _coletar(self) -> tuple[MedicamentoDados, dict[str, str]]:
        erros: dict[str, str] = {}

        def converter(chave, funcao, padrao, **kw):
            try:
                return funcao(self._texto(chave), **kw)
            except ValueError as e:
                erros[chave] = str(e)
                return padrao

        quantidade = (self.med.quantidade_atual if self.editando
                      else converter("quantidade_atual", converter_inteiro, 0))
        dados = MedicamentoDados(
            nome=self._texto("nome"), principio_ativo=self._texto("principio_ativo"),
            nome_generico=self._texto("nome_generico"), eh_generico=bool(self.chave_generico.get()),
            laboratorio=self._texto("laboratorio"), categoria=self._texto("categoria"),
            dosagem=self._texto("dosagem"), unidade_medida=self._texto("unidade_medida"),
            forma_farmaceutica=self._texto("forma_farmaceutica"),
            quantidade_atual=quantidade,
            estoque_minimo=converter("estoque_minimo", converter_inteiro, 0),
            preco_compra_centavos=converter("preco_compra", converter_dinheiro, 0),
            preco_venda_centavos=converter("preco_venda", converter_dinheiro, 0),
            setor=self._texto("setor"), corredor=self._texto("corredor"),
            estante=self._texto("estante"), prateleira=self._texto("prateleira"),
            gaveta=self._texto("gaveta"), lote=self._texto("lote"),
            data_fabricacao=converter("data_fabricacao", converter_data, None),
            data_validade=converter("data_validade", converter_data, None, fim_do_mes=True),
            observacoes=self._texto("observacoes"), relacionados=self.seletor.obter_ids())
        dados.normalizar()
        for chave, msg in dados.validar().items():
            erros.setdefault(chave, msg)
        return dados, erros

    # ------------------------------------------------------------------- salvar
    def salvar(self) -> None:
        self._limpar_erros()
        dados, erros = self._coletar()
        novo_id = self.medicamento_id
        if not erros:
            try:
                if self.editando:
                    self.app.ctx.medicamentos.atualizar(self.medicamento_id, dados)
                else:
                    novo_id = self.app.ctx.medicamentos.criar(dados)
            except ValidacaoError as e:
                erros = e.erros
            except DuplicadoError as e:
                erros = {"nome": str(e)}
            except FarmaciaError as e:
                erros = {"_geral": str(e)}
        if erros:
            self._mostrar_erros(erros)
            return
        self.app.aviso(("Alterações salvas: " if self.editando else "Medicamento cadastrado: ")
                       + dados.nome, "ok")
        self.app.dados_alterados()
        if self.ao_salvar:
            self.ao_salvar(novo_id)
        self.fechar()

    def _limpar_erros(self) -> None:
        self.banner.pack_forget()
        for w in self.campos.values():
            try:
                w.configure(border_color=COR.borda)
            except Exception:
                pass

    def _mostrar_erros(self, erros: dict[str, str]) -> None:
        linhas = ["Não foi possível salvar. Corrija o que está marcado em vermelho:"]
        primeiro = None
        for chave, msg in erros.items():
            rotulo = _ROTULOS.get(chave)
            linhas.append(f"•  {rotulo}: {msg}" if rotulo and not msg.startswith("Já existe")
                          else f"•  {msg}")
            w = self.campos.get(chave)
            if w is not None:
                try:
                    w.configure(border_color=COR.perigo)
                except Exception:
                    pass
                primeiro = primeiro or w
        self.banner_texto.configure(text="\n".join(linhas))
        self.banner.pack(fill="x", pady=(10, 2))
        if primeiro is not None:
            self.after(30, lambda: self._rolar_ate(primeiro))

    def _rolar_ate(self, widget) -> None:
        try:
            self.update_idletasks()
            total = max(self.rolagem.winfo_height(), 1)
            y = widget.winfo_rooty() - self.rolagem.winfo_rooty()
            self.rolagem._parent_canvas.yview_moveto(max(0.0, (y - 60) / total))
            widget.focus_set()
        except Exception:
            pass
