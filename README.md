# PDF Table Scanner

![Python](https://img.shields.io/badge/python-v3.6+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-v5.15+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

> **English**: Interactive desktop application for extracting tables from PDF documents with visual selection and multi-page support.

> **Português**: Aplicação desktop interativa para extração de tabelas de documentos PDF com seleção visual e suporte multi-página.

Um extrator de tabelas de PDF com interface gráfica que permite selecionar e extrair tabelas de documentos PDF como imagens PNG.

## 📋 Descrição

O PDF Table Scanner é uma aplicação desktop desenvolvida em Python que permite:
- Abrir documentos PDF
- Visualizar páginas do PDF em uma interface gráfica
- Selecionar áreas de tabelas através de cliques do mouse
- Extrair tabelas que se estendem por múltiplas páginas
- Salvar as tabelas selecionadas como imagens PNG

## 🚀 Funcionalidades

- **Interface Gráfica Intuitiva**: Aplicação desktop com PyQt5
- **Visualização de PDF**: Renderização de páginas PDF em alta qualidade (150 DPI)
- **Seleção Interativa**: Seleção de áreas através de dois cliques do mouse
- **Tabelas Multi-página**: Suporte para tabelas que se estendem por várias páginas
- **Preview Visual**: Visualização em tempo real da área sendo selecionada
- **Exportação Automática**: Salvamento automático das tabelas como imagens PNG
- **Visualizador de Tabelas**: Interface dedicada para visualizar tabelas extraídas
- **Conversão para JSONL**: Ferramenta para converter tabelas em formato estruturado JSON
- **Editor de Estrutura**: Interface intuitiva para editar metadados e estrutura das tabelas

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **PyQt5** - Interface gráfica
- **PyMuPDF (fitz)** - Processamento de documentos PDF
- **PIL/Pillow** - Manipulação de imagens
- **pandas** - Processamento de dados (opcional, para scripts auxiliares)
- **openpyxl** - Exportação para Excel (opcional)

## 📦 Instalação

### Pré-requisitos

Certifique-se de ter Python 3.6+ instalado em seu sistema.

### Dependências

Instale as dependências necessárias:

```bash
pip install PyQt5 PyMuPDF Pillow pandas openpyxl
```

Ou use o arquivo de requisitos:

```bash
pip install -r requirements.txt
```

### Clone do Repositório

```bash
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
```

## 🎯 Como Usar

### 1. Executar a Aplicação

```bash
python extrator_tabelas_pdf.py
```

### 2. Abrir um PDF

1. Clique no botão "Escolher PDF"
2. Selecione o arquivo PDF desejado
3. As páginas serão carregadas na interface

### 3. Selecionar Tabelas

#### Tabela em uma única página:
1. Clique no primeiro ponto (canto superior esquerdo da tabela)
2. Clique no segundo ponto (canto inferior direito da tabela)
3. Uma área vermelha mostrará a seleção

#### Tabela em múltiplas páginas:
1. Clique no primeiro ponto na página inicial da tabela
2. Clique no segundo ponto na página final da tabela
3. Áreas azuis mostrarão a seleção nas páginas envolvidas

### 4. Salvar Tabelas

1. Clique no botão "Salvar Tabelas Selecionadas"
2. Escolha a pasta de destino
3. As tabelas serão salvas com nomes descritivos

### 5. Visualizar e Converter Tabelas

1. Clique no botão "Visualizar Tabelas Extraídas"
2. Selecione uma tabela na lista suspensa
3. Preencha os metadados (fonte, título)
4. Configure as subseções da tabela:
   - Adicione o nome da subseção
   - Defina os cabeçalhos (separados por vírgula)
   - Preencha os dados na tabela interativa
5. Use os botões para adicionar/remover linhas e colunas
6. Visualize o preview JSON na aba correspondente
7. Salve em formato JSONL individual ou exporte todas

#### Formato JSONL Gerado

O sistema gera arquivos JSONL seguindo esta estrutura:

```json
{
  "type": "table",
  "source": "Nome da fonte",
  "title": "Título da tabela",
  "text": [
    {
      "subsection": "Nome da subseção",
      "headers": ["Cabeçalho 1", "Cabeçalho 2", "Cabeçalho 3"],
      "rows": [
        ["Dado 1", "Dado 2", "Dado 3"],
        ["Dado 4", "Dado 5", "Dado 6"]
      ]
    }
  ]
}
```

## 📁 Estrutura do Projeto

```
pdf-table-scanner/
├── extrator_tabelas_pdf.py    # Aplicação principal
├── processar_jsonl.py         # Script para processar dados JSONL
├── LivrosPDF/                 # Pasta com PDFs de exemplo
│   ├── Manual-BLS.pdf
│   ├── apostilafinal.pdf
│   └── ...
├── tabelas/                   # Pasta com tabelas extraídas
│   ├── Manual-BLS_pagina_1_tabela_1.png
│   ├── Manual-BLS_pagina_1_tabela_1.jsonl
│   └── ...
├── dados_processados/         # Dados processados (Excel, CSV)
├── README.md                  # Este arquivo
├── JSONL_GUIDE.md            # Guia de conversão JSONL
└── requirements.txt           # Dependências do projeto
```

## 🖱️ Controles da Interface

- **Clique Esquerdo**: Selecionar pontos para definir área da tabela
- **Scroll**: Navegar pelas páginas do PDF
- **Preview em Tempo Real**: Visualização da área sendo selecionada

### Indicadores Visuais

- **Linha Vermelha Tracejada**: Preview da seleção em uma única página
- **Linha Azul Tracejada**: Preview da seleção em múltiplas páginas
- **Retângulo Vermelho**: Seleção confirmada em uma única página
- **Retângulos Azuis**: Seleção confirmada em múltiplas páginas

## 📋 Formato de Saída

As tabelas extraídas são salvas com o seguinte padrão de nomenclatura:

- **Página única**: `{nome_pdf}_pagina_{numero}_tabela_{indice}.png`
- **Múltiplas páginas**: `{nome_pdf}_pagina_{inicio}-{fim}_tabela_{indice}.png`

Exemplo:
- `Manual-BLS_pagina_1_tabela_1.png`
- `Manual-BLS_pagina_1-2_tabela_2.png`

## 🔧 Configurações

### Qualidade da Renderização

A aplicação renderiza PDFs com 150 DPI por padrão. Para alterar, modifique a linha no código:

```python
pix = page.get_pixmap(dpi=150)  # Altere o valor do DPI aqui
```

### Cores da Interface

As cores dos indicadores visuais podem ser personalizadas:

```python
# Seleção em página única
self.image_labels[page_idx1].add_rect(rect, color=QColor(255, 0, 0))  # Vermelho

# Seleção em múltiplas páginas  
self.image_labels[page_idx1].add_rect(rect1, color=QColor(0, 0, 255))  # Azul
```

## 🐛 Solução de Problemas

### Erro de Importação do PyQt5

```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt5

# Fedora/CentOS
sudo dnf install python3-qt5

# macOS
brew install pyqt5
```

### Erro de Importação do PyMuPDF

```bash
pip install --upgrade PyMuPDF
```

### PDF não abre

Verifique se:
- O arquivo PDF não está corrompido
- Você tem permissões de leitura no arquivo
- O PDF não está protegido por senha

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👥 Autores

- **Mablemb** - *Desenvolvimento inicial* - [Mablemb](https://github.com/Mablemb)

## 📞 Suporte

Para suporte, abra uma issue no [GitHub](https://github.com/Mablemb/pdf-table-scanner/issues) ou entre em contato através do email.

## 🎯 Próximas Funcionalidades

- [ ] Suporte para OCR nas tabelas extraídas
- [ ] Exportação para formatos CSV/Excel
- [ ] Detecção automática de tabelas
- [ ] Interface para edição de seleções
- [ ] Suporte para batch processing
- [ ] Histórico de extrações

## 📊 Processamento de Dados

### Script de Processamento Automático

O projeto inclui um script Python (`processar_jsonl.py`) para processar os arquivos JSONL gerados:

```bash
python processar_jsonl.py
```

#### Funcionalidades do Script:
- **Carregamento de JSONL**: Lê todos os arquivos `.jsonl` da pasta `tabelas/`
- **Conversão para DataFrame**: Converte dados em estruturas pandas
- **Exportação para Excel**: Cria arquivo Excel com múltiplas abas
- **Exportação para CSV**: Gera arquivos CSV individuais por subseção
- **Relatórios**: Gera relatórios textuais das tabelas
- **Análises Específicas**: Inclui análises customizadas (ex: Escala Glasgow)

#### Exemplo de Uso Programático:

```python
from processar_jsonl import carregar_jsonl, extrair_dados_tabela

# Carrega dados
dados = carregar_jsonl("tabelas/exemplo.jsonl")

# Converte para DataFrames
for tabela in dados:
    dataframes = extrair_dados_tabela(tabela)
    
    # Processa cada subseção
    for df in dataframes:
        print(f"Subseção: {df.attrs['subsection']}")
        print(df.head())
```

---

⭐ **Se este projeto foi útil para você, considere dar uma estrela no GitHub!**
