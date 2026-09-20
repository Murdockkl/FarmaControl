"""Testes da interface: abrem a janela de verdade e agem como o usuário agiria.

Precisam de uma tela (no Linux sem monitor, use:  xvfb-run -a python -m pytest).
Se não houver tela disponível, os testes são pulados automaticamente.
"""
from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

pytest.importorskip("customtkinter")

from farmacia.contexto import Contexto                              # noqa: E402
from farmacia.dominio import ENTRADA, SAIDA                         # noqa: E402
from farmacia.servicos.medicamentos import SIT_BAIXO                # noqa: E402
from farmacia.ui.app import App                                     # noqa: E402


def _tem_tela() -> bool:
    try:
        raiz = tk.Tk()
        raiz.destroy()
        return True
    except tk.TclError:
        return False


pytestmark = pytest.mark.skipif(not _tem_tela(), reason="sem tela (use xvfb-run)")


@pytest.fixture
def abrir(tmp_path):
    """Devolve uma função que abre o sistema sobre o mesmo banco (para fechar e reabrir)."""
    abertos: list[App] = []
    caminho = tmp_path / "dados" / "farmacia.db"

    def _abrir() -> SimpleNamespace:
        app = App(Contexto(caminho))
        app.mensagens, app.erros = [], []
        app.report_callback_exception = lambda e, v, tb: app.erros.append(v)
        app.confirmar = lambda *a, **k: True                       # "Sim" em qualquer confirmação
        app.mensagem = lambda titulo, texto, tipo="info": app.mensagens.append((titulo, texto, tipo))
        abertos.append(app)
        app.update()
        return app

    yield _abrir
    for app in abertos:
        try:
            app.destroy()
        except tk.TclError:
            pass


def linhas(tabela) -> list[tuple]:
    return [tuple(tabela.arvore.item(i, "values")) for i in tabela.arvore.get_children()]


def cadastrar(app: App, **campos) -> int:
    """Abre o formulário de novo medicamento, preenche e clica em Salvar."""
    padrao = dict(nome="Paracetamol 750 mg", principio_ativo="Paracetamol", laboratorio="Lab Teste",
                  categoria="Analgésico", dosagem="750", unidade_medida="mg",
                  forma_farmaceutica="Comprimido", quantidade_atual="20", estoque_minimo="10",
                  preco_compra="4,20", preco_venda="8,90", setor="Medicamentos", corredor="A",
                  estante="02", prateleira="03", lote="L001", data_validade="08/2027")
    padrao.update(campos)
    app.abrir_formulario()
    app.update()
    form = app.modais[-1]
    for chave, valor in padrao.items():
        form._definir(chave, valor)
    form.chave_generico.select()
    form.salvar()
    app.update()
    return max(m.id for m in app.ctx.medicamentos.listar())


def test_interface_passos_1_a_15(abrir):
    # ---- 1. cadastrar medicamento pelo formulário
    app = abrir()
    med_id = cadastrar(app)
    assert app.erros == [] and app.modais == []            # o formulário fechou sozinho
    med = app.ctx.medicamentos.obter(med_id)
    assert med.nome == "Paracetamol 750 mg" and med.quantidade_atual == 20
    assert med.data_validade == date(2027, 8, 31) and med.eh_generico
    assert (med.corredor, med.estante, med.prateleira) == ("A", "02", "03")

    # ---- 2 e 3. fechar o sistema e abrir de novo
    app._sair()
    app = abrir()

    # ---- 4. o medicamento continua cadastrado (e aparece na tabela)
    tabela = app.navegar("medicamentos").tabela
    assert [l[1] for l in linhas(tabela)] == ["Paracetamol 750 mg"]
    assert linhas(tabela)[0][5] == "Corredor A · Est. 02 · Prat. 03"

    # ---- 5. adicionar estoque (entrada de 30: 20 -> 50)
    app.abrir_movimentacao(med_id, ENTRADA)
    app.update()
    dialogo = app.modais[-1]
    dialogo.formulario.quantidade.insert(0, "30")
    dialogo.formulario._atualizar_previa()
    assert "Novo estoque: 50" in dialogo.formulario.previa.cget("text")
    dialogo.formulario.confirmar()
    app.update()
    assert app.ctx.medicamentos.obter(med_id).quantidade_atual == 50 and app.modais == []

    # ---- 6. retirar estoque (saída de 5: 50 -> 45)
    app.abrir_movimentacao(med_id, SAIDA)
    app.update()
    form = app.modais[-1].formulario
    form.quantidade.insert(0, "5")
    form.confirmar()
    app.update()
    assert app.ctx.medicamentos.obter(med_id).quantidade_atual == 45

    # ---- 7. tentar retirar mais do que existe: erro na tela e nada muda
    app.abrir_movimentacao(med_id, SAIDA)
    app.update()
    dialogo = app.modais[-1]
    dialogo.formulario.quantidade.insert(0, "60")
    dialogo.formulario._atualizar_previa()
    assert "insuficiente" in dialogo.formulario.previa.cget("text")
    dialogo.formulario.confirmar()
    assert "Estoque insuficiente" in dialogo.formulario.erro.cget("text")
    assert app.ctx.medicamentos.obter(med_id).quantidade_atual == 45
    assert app.modais == [dialogo]                          # a janela continua aberta para corrigir
    dialogo.fechar()

    # ---- 8. pesquisar por princípio ativo
    pagina = app.navegar("medicamentos")
    pagina.busca.definir("paracetamol")
    assert len(linhas(pagina.tabela)) == 1
    pagina.busca.definir("dipirona")
    assert linhas(pagina.tabela) == []

    # ---- 9. pesquisar por localização
    pagina.busca.definir("Corredor A")
    assert len(linhas(pagina.tabela)) == 1
    pagina.busca.definir("Corredor B")
    assert linhas(pagina.tabela) == []
    pagina.busca.definir("")

    # ---- 10. editar medicamento
    app.abrir_formulario(med_id)
    app.update()
    form = app.modais[-1]
    assert form.campos["nome"].get() == "Paracetamol 750 mg"
    assert str(form.campos["quantidade_atual"].cget("state")) == "disabled"      # estoque só por Entrada/Saída
    form._definir("nome", "Paracetamol 750 mg Editado")
    form._definir("corredor", "C")
    form.salvar()
    app.update()
    editado = app.ctx.medicamentos.obter(med_id)
    assert editado.nome.endswith("Editado") and editado.corredor == "C"
    assert editado.quantidade_atual == 45
    assert linhas(app.navegar("medicamentos").tabela)[0][1] == "Paracetamol 750 mg Editado"

    # ---- 12. histórico (antes de excluir)
    historico = app.navegar("historico")
    historico.atualizar()
    tipos = [(l[3], l[4], l[5], l[6], l[7]) for l in linhas(historico.tabela)]
    assert tipos == [("Saída", "-5", "50", "45", "Venda"),
                     ("Entrada", "+30", "20", "50", "Compra"),
                     ("Entrada", "+20", "0", "20", "Estoque inicial")]

    # ---- 11. excluir medicamento (confirmação já respondida "Sim" pelo teste)
    app.excluir_medicamento(med_id)
    app.update()
    assert app.ctx.medicamentos.obter(med_id) is None
    assert linhas(app.navegar("medicamentos").tabela) == []
    # ---- 12. ...e o histórico continua lá
    historico = app.navegar("historico")
    assert len(linhas(historico.tabela)) == 3
    assert all("(excluído)" in l[2] for l in linhas(historico.tabela))
    assert app.erros == [] and app.mensagens == []


def test_interface_validacoes_do_formulario(abrir):
    app = abrir()
    app.abrir_formulario()
    app.update()
    form = app.modais[-1]
    form.salvar()                                           # tudo vazio
    assert app.ctx.medicamentos.total() == 0 and app.modais == [form]
    assert "Nome do medicamento" in form.banner_texto.cget("text")
    assert "Princípio ativo" in form.banner_texto.cget("text")
    assert form.campos["nome"].cget("border_color") != form.campos["lote"].cget("border_color")

    form._definir("nome", "X")
    form._definir("principio_ativo", "Y")
    form._definir("quantidade_atual", "-5")
    form._definir("estoque_minimo", "2,5")
    form._definir("preco_venda", "abc")
    form._definir("data_validade", "31/02/2027")
    form._definir("data_fabricacao", "01/01/2999")
    form.salvar()
    texto = form.banner_texto.cget("text")
    for trecho in ("Quantidade atual", "Estoque mínimo", "Preço de venda", "Data de validade",
                   "Data de fabricação"):
        assert trecho in texto, trecho
    assert app.ctx.medicamentos.total() == 0

    form.fechar()
    assert app.modais == [] and app.erros == []


def test_interface_duplicado_e_lote_diferente(abrir):
    app = abrir()
    cadastrar(app)
    app.abrir_formulario()
    app.update()
    form = app.modais[-1]
    for chave, valor in dict(nome="paracetamol 750 mg", principio_ativo="Paracetamol",
                             laboratorio="lab teste", dosagem="750", unidade_medida="mg",
                             forma_farmaceutica="Comprimido", lote="L001").items():
        form._definir(chave, valor)
    form.salvar()
    assert app.ctx.medicamentos.total() == 1
    assert "Já existe" in form.banner_texto.cget("text")
    form._definir("lote", "L002")                           # outro lote: permitido
    form.salvar()
    app.update()
    assert app.ctx.medicamentos.total() == 2 and app.erros == []


def test_interface_alertas_dashboard_e_validade(abrir):
    app = abrir()
    cadastrar(app, nome="Baixo", quantidade_atual="3", estoque_minimo="5", lote="A",
              data_validade="")
    vencido = date.today() - timedelta(days=2)
    cadastrar(app, nome="Vencido", lote="B", data_validade=vencido.strftime("%d/%m/%Y"))
    perto = date.today() + timedelta(days=10)
    cadastrar(app, nome="Perto", lote="C", data_validade=perto.strftime("%d/%m/%Y"))
    dash = app.navegar("dashboard")
    dash.atualizar()
    assert dash.c_total.valor.cget("text") == "3"
    assert dash.c_baixo.valor.cget("text") == "1"
    assert dash.c_venc.valor.cget("text") == "1"
    assert "1 já vencido" in dash.c_venc.detalhe.cget("text")
    assert [l[0] for l in linhas(dash.t_baixo)] == ["Baixo 750 mg"]
    assert sorted(l[0] for l in linhas(dash.t_venc)) == ["Perto 750 mg", "Vencido 750 mg"]
    # filtros da tela de medicamentos
    app.ver_medicamentos(SIT_BAIXO)
    assert [l[1] for l in linhas(app.paginas["medicamentos"].tabela)] == ["Baixo"]
    pagina = app.paginas["medicamentos"]
    pagina.menu_situacao.set("Vencidos")
    pagina.atualizar()
    assert [l[1] for l in linhas(pagina.tabela)] == ["Vencido"]
    assert linhas(pagina.tabela)[0][7] == "Vencido"
    # o prazo de alerta é configurável
    config = app.navegar("configuracoes")
    config.dias.delete(0, "end")
    config.dias.insert(0, "3")
    config._salvar_dias()
    assert "dashboard" in app._sujas                          # ficou marcada para atualizar
    assert app.navegar("dashboard").c_venc.valor.cget("text") == "0"   # ao abrir, já reflete os 3 dias
    config = app.navegar("configuracoes")
    config.dias.delete(0, "end")
    config.dias.insert(0, "abc")
    config._salvar_dias()
    assert "Informe um número inteiro" in config.msg_dias.cget("text")
    assert app.erros == []


def test_interface_backup_restaurar_e_demo(abrir, tmp_path, monkeypatch):
    from tkinter import filedialog
    app = abrir()
    med_id = cadastrar(app)
    destino = tmp_path / "backup.db"
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(destino))
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(destino))
    config = app.navegar("configuracoes")

    config._backup()                                        # fazer backup
    assert destino.exists() and destino.stat().st_size > 0
    app.ctx.estoque.saida(med_id, 7, "Venda")               # muda depois do backup
    app.dados_alterados()
    assert app.ctx.medicamentos.obter(med_id).quantidade_atual == 13

    config._restaurar()                                     # restaurar
    assert app.ctx.medicamentos.obter(med_id).quantidade_atual == 20
    assert any(m[0] == "Backup restaurado" for m in app.mensagens)
    assert list((tmp_path / "dados" / "copias_antes_de_restaurar").glob("*.db"))

    destino.write_text("não sou um banco")                  # arquivo inválido é recusado
    config._restaurar()
    assert any(m[0] == "Arquivo inválido" for m in app.mensagens)
    assert app.ctx.medicamentos.obter(med_id).quantidade_atual == 20

    app.adicionar_demo()                                    # dados de demonstração
    assert app.ctx.medicamentos.total() == 16
    config.atualizar()
    assert str(config.btn_rem_demo.cget("state")) == "normal"
    config._remover_demo()
    assert app.ctx.medicamentos.total() == 1 and app.erros == []


def test_interface_relatorios_e_exportacao(abrir, tmp_path, monkeypatch):
    from tkinter import filedialog
    app = abrir()
    app.adicionar_demo()
    pagina = app.navegar("relatorios")
    for chave in ("estoque_atual", "estoque_baixo", "vencidos", "proximos_vencimento",
                  "movimentacoes", "valor_estoque"):
        pagina.escolher(chave)
        assert pagina.relatorio.tipo == chave
    pagina.escolher("estoque_atual")
    assert len(linhas(pagina.tabela)) == 15
    for formato in ("csv", "xlsx", "pdf"):
        destino = tmp_path / f"relatorio.{formato}"
        monkeypatch.setattr(filedialog, "asksaveasfilename", lambda d=destino, **k: str(d))
        pagina.exportar(formato)
        assert destino.exists() and destino.stat().st_size > 200, formato
    # período inválido no relatório de movimentações
    pagina.escolher("movimentacoes")
    pagina.data_ini.delete(0, "end")
    pagina.data_ini.insert(0, "31/02/2026")
    pagina.gerar()
    assert "Período inválido" in pagina.erro.cget("text")
    assert app.erros == []


def test_interface_detalhes_estoque_e_historico(abrir):
    app = abrir()
    app.adicionar_demo()
    med = next(m for m in app.ctx.medicamentos.listar() if m.nome == "Paracetamol Genérico"
               and m.dosagem == "750")
    app.abrir_detalhes(med.id)
    app.update()
    detalhes = app.modais[-1]
    assert "PARACETAMOL GENÉRICO 750 MG" in [w.cget("text") for w in _rotulos(detalhes)]
    assert "Corredor A → Estante 02 → Prateleira 03" in [w.cget("text") for w in _rotulos(detalhes)]
    detalhes.fechar()

    # tela de Estoque: escolher, registrar entrada, ver o novo estoque
    est = app.navegar("estoque")
    est.selecionar_medicamento(med.id, ENTRADA)
    est.formulario.quantidade.insert(0, "10")
    est.formulario.confirmar()
    app.update()
    assert app.ctx.medicamentos.obter(med.id).quantidade_atual == med.quantidade_atual + 10
    assert est.estoque_atual.cget("text") == str(med.quantidade_atual + 10)
    assert linhas(est.historico)[0][1] == "+10"

    # histórico: filtro por tipo e por texto
    hist = app.navegar("historico")
    hist.tipo.set("Entradas")
    hist.busca.definir("febrolyn")
    assert all(l[3] == "Entrada" and "Febrolyn" in l[2] for l in linhas(hist.tabela))
    hist.data_ini.delete(0, "end")
    hist.data_ini.insert(0, "99/99/9999")
    hist.atualizar()
    assert "Período inválido" in hist.erro.cget("text")
    assert app.erros == []


def _rotulos(raiz):
    import customtkinter as ctk
    achados = []

    def visitar(w):
        if isinstance(w, ctk.CTkLabel):
            achados.append(w)
        for f in w.winfo_children():
            visitar(f)
    visitar(raiz)
    return achados
