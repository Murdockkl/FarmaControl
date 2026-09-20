# FarmaControl — gerenciamento local de farmácia

Sistema desktop para cadastrar medicamentos, pesquisar (inclusive por localização física), controlar
entradas e saídas de estoque e acompanhar alertas de estoque baixo e validade.

* Funciona **100% no seu computador**, sem internet, servidor ou banco externo.
* Tecnologias: **Python 3.10+**, **SQLite** (já vem com o Python) e **CustomTkinter** (interface moderna).
* Todos os dados ficam em um único arquivo: `dados/farmacia.db`.

---

## 1. Como executar

### Windows
1. Instale o Python em <https://www.python.org/downloads/> (marque **"Add Python to PATH"**).
2. Dê um duplo clique em **`executar.bat`**. Na primeira vez ele instala as bibliotecas sozinho
   (precisa de internet só nesse momento).

Ou, pelo terminal, dentro desta pasta:

```
pip install -r requirements.txt
python main.py
```

### Linux / macOS
```
./executar.sh          # ou:  pip install -r requirements.txt && python3 main.py
```
No Linux pode ser necessário instalar o Tkinter: `sudo apt install python3-tk`.

### Dependências
| Biblioteca | Para quê |
|---|---|
| `customtkinter` | interface gráfica moderna |
| `openpyxl` | exportar relatórios para Excel |
| `reportlab` | exportar relatórios para PDF |

(`sqlite3` e `tkinter` fazem parte do Python.) Para desenvolver: `pip install -r requirements-dev.txt`.

---

## 2. Estrutura das pastas

```
FarmaControl/
├── farmacia
│   ├── servicos
│   │   ├── __init__.py
│   │   ├── backup.py
│   │   ├── configuracoes.py
│   │   ├── demonstracao.py
│   │   ├── estoque.py
│   │   ├── exportacao.py
│   │   ├── medicamentos.py
│   │   └── relatorios.py
│   ├── ui
│   │   ├── dialogos
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── detalhes.py
│   │   │   ├── formulario.py
│   │   │   └── movimentacao.py
│   │   ├── paginas
│   │   │   ├── __init__.py
│   │   │   ├── configuracoes.py
│   │   │   ├── dashboard.py
│   │   │   ├── estoque.py
│   │   │   ├── historico.py
│   │   │   ├── medicamentos.py
│   │   │   └── relatorios.py
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── tema.py
│   │   └── widgets.py
│   ├── __init__.py
│   ├── banco.py
│   ├── config.py
│   ├── contexto.py
│   ├── dominio.py
│   ├── texto.py
│   └── validacao.py
├── tests
│   ├── __init__.py
│   ├── test_fluxo_completo.py
│   └── test_interface.py
├── .gitignore
├── build_exe.bat
├── build_exe.sh
├── executar.bat
├── executar.sh
├── main.py
├── requirements-dev.txt
└── requirements.txt
```

Cada camada tem uma responsabilidade:

* **`banco.py`**: conexão SQLite, criação das tabelas, transações, cópia/restauração do arquivo.
* **`servicos/`**: regras de negócio (cadastro, estoque, relatórios, backup…). **Não conhecem a interface.**
* **`ui/`**: telas e janelas. Só chamam os serviços; não escrevem SQL.
* **`dominio.py`, `validacao.py`, `texto.py`**: modelos, alertas, conversão dos textos digitados e formatação pt-BR.
* **`ui/tema.py`**: cores e fontes. Para mudar o visual, é o único arquivo a editar.
* **`config.py`**: listas de formas farmacêuticas, unidades e motivos de movimentação.

---

## 3. Uso rápido

* **Início**: cartões com totais, listas de estoque baixo, vencidos/próximos do vencimento e últimas
  movimentações. Clique em um cartão para abrir a lista já filtrada.
* **Medicamentos**: pesquisa rápida (nome, princípio ativo, genérico, laboratório, categoria, localização,
  lote ou código), filtros, colunas ordenáveis (clique no título), duplo clique para ver detalhes,
  botão direito para o menu de ações. Atalho **Ctrl+N** = novo medicamento.
* **Detalhes**: tudo em uma tela, com **"Onde encontrar"** em destaque (Corredor → Estante → Prateleira)
  e os botões **Entrada / Saída / Editar**.
* **Estoque**: escolha o medicamento à esquerda; à direita, informe entrada ou saída. Antes de confirmar,
  aparece a prévia "Estoque atual → Novo estoque". Saída maior que o estoque é bloqueada com mensagem clara.
* **Histórico**: filtro por período, medicamento e tipo (entrada/saída).
* **Relatórios**: estoque atual, estoque baixo, vencidos, próximos do vencimento, movimentações e valor do
  estoque, com exportação para **PDF, Excel e CSV**.
* **Configurações**: nome da farmácia, prazo do alerta de validade, backup/restauração e dados de demonstração.

### Dados de demonstração
Em **Configurações → Adicionar dados de demonstração** (ou no botão da tela inicial vazia) entram
15 medicamentos **fictícios**, com estoque, validades e histórico variados para você testar tudo. Eles ficam
marcados como demonstração (aviso nos detalhes e nas observações) e podem ser removidos de uma vez em
**Configurações → Remover dados de demonstração**, sem afetar os dados reais. Nomes comerciais, laboratórios
e as relações entre medicamentos da demonstração são inventados.

---

## 4. Como o banco de dados funciona

O SQLite guarda tudo em `dados/farmacia.db`. Tabelas:

| Tabela | Conteúdo |
|---|---|
| `medicamentos` | dados do medicamento, quantidade atual, preços (em centavos), validade, lote |
| `movimentacoes` | histórico: tipo, quantidade, estoque anterior/posterior, motivo, data e hora |
| `categorias`, `laboratorios` | listas reaproveitadas pelos medicamentos |
| `localizacoes` | setor, corredor, estante, prateleira e gaveta |
| `medicamentos_relacionados` | semelhantes/referências (um par = uma linha, vale nos dois sentidos) |
| `configuracoes` | prazo de alerta, nome da farmácia |

Regras importantes (garantidas no programa **e** no próprio banco, por `CHECK`/chaves estrangeiras):

* **Estoque nunca fica negativo.** A quantidade só muda por Entrada/Saída; atualização do estoque e registro no
  histórico acontecem na mesma transação (ou os dois são gravados, ou nenhum).
* **O histórico é coerente**: o banco recusa uma linha em que `estoque_posterior` não bata com a conta.
* Ao cadastrar com quantidade maior que zero, o sistema registra uma entrada **"Estoque inicial"**.
* Na tela de edição a quantidade fica travada (use Entrada/Saída), para não "sumir" com unidades sem registro.
* **Excluir** é uma exclusão lógica: o medicamento some das telas, mas o histórico dele é mantido
  (aparece como "excluído"). Para recuperá-lo, restaure um backup.
* **Cada cadastro representa um produto em um lote.** Duplicidade = mesmo nome, dosagem, unidade, forma,
  laboratório **e lote**. Outro lote do mesmo produto é permitido; para repor o mesmo lote, use Entrada.
* **Alertas**: estoque baixo = `quantidade <= estoque mínimo` (com 0 aparece como "Sem estoque");
  vencido = validade anterior a hoje; próximo do vencimento = vence em até N dias (padrão 30, configurável).
  Vencido/próximo do vencimento só contam se ainda houver unidades em estoque.
* **Valor do estoque**: mostrado a preço de compra (custo) e a preço de venda.
* **Pesquisa** ignora maiúsculas e acentos. `corredor a` encontra só o corredor A; `paracetamol 750` encontra
  o medicamento que tenha as duas palavras em campos diferentes.
* Medicamentos "semelhantes" são **somente os que você relacionar** no cadastro. O sistema nunca conclui
  equivalência por nome parecido nem faz recomendação farmacêutica.
* Datas aceitam `dd/mm/aaaa` ou `mm/aaaa` (validade em `mm/aaaa` vale até o último dia do mês).
* Preços aceitam `8,90`, `8.90` e `R$ 1.234,56`.

---

## 5. Backup e restauração

**Configurações → Fazer backup**: escolha onde salvar (pen drive, nuvem…). O arquivo `.db` é uma cópia completa,
consistente mesmo com o programa aberto.

**Configurações → Restaurar backup**: escolha o arquivo `.db`. O programa confere se ele é válido e se não está
corrompido, pede confirmação e **guarda antes uma cópia dos dados atuais** em
`dados/copias_antes_de_restaurar/`, para que nada se perca por engano.

Backup manual: também basta copiar `dados/farmacia.db` com o programa fechado.

---

## 6. Como criar o executável (.exe)

No Windows, dê um duplo clique em **`build_exe.bat`** (ou rode os comandos abaixo). Ele usa o PyInstaller:

```
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name FarmaControl --collect-all customtkinter main.py
```

O resultado fica em `dist/FarmaControl/FarmaControl.exe`. **Copie a pasta `dist/FarmaControl` inteira** para onde
quiser; os dados ficam na subpasta `dados`, ao lado do `.exe` (se essa pasta não permitir gravação, o programa usa
`C:\Users\<você>\FarmaControl`). Para atualizar o programa, substitua os arquivos mantendo a pasta `dados`.

---

## 7. Testes

```
pip install -r requirements-dev.txt
python -m pytest -v                 # em Linux sem monitor:  xvfb-run -a python -m pytest -v
```

* `tests/test_fluxo_completo.py`: lógica (sem tela): os 15 passos de verificação, validações, duplicidade,
  exportações CSV/Excel/PDF, backup, demonstração.
* `tests/test_interface.py`: abre a janela de verdade e age como o usuário (preenche o formulário, fecha e reabre
  o programa, registra entrada/saída, pesquisa, edita, exclui, faz backup e restaura…). É pulado se não houver tela.

---

## 8. Limitações conhecidas

* Sem controle de usuários/senha: é pensado para um computador de uso local.
* Não há venda/PDV nem leitura de código de barras. A saída de estoque é um registro manual.
* Um lote por cadastro (veja a regra de duplicidade). Não há controle de várias validades dentro de um mesmo cadastro.
* Exclusão pela tela não tem "desfazer" (use backup).
* Pensado para milhares de medicamentos; a tela de Histórico mostra as 2.000 movimentações mais recentes do filtro
  (os relatórios exportam tudo).

## 9. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Falta instalar uma biblioteca" | `pip install -r requirements.txt` |
| Erro `No module named tkinter` (Linux) | `sudo apt install python3-tk` |
| Não consigo exportar (arquivo em uso) | Feche o arquivo no Excel/leitor de PDF e exporte de novo |
| Qualquer erro inesperado | Seus dados continuam salvos. Detalhes em `dados/farmacia.log` |
| Quero mudar os dados de lugar | Feche o programa e copie a pasta `dados` |

Este sistema organiza o estoque; **não substitui a orientação de um farmacêutico**.
