# Documentação Técnica - PDF Table Scanner

## 📖 Índice

1. [Arquitetura do Sistema](#arquitetura-do-sistema)
2. [Classes e Métodos](#classes-e-métodos)
3. [Fluxo de Dados](#fluxo-de-dados)
4. [API Reference](#api-reference)
5. [Configurações Avançadas](#configurações-avançadas)
6. [Debugging](#debugging)

## 🏗️ Arquitetura do Sistema

O PDF Table Scanner é construído usando o padrão MVC (Model-View-Controller) adaptado para PyQt5:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDF Document  │    │  PDFTableEx-    │    │   PDFPageLabel  │
│     (Model)     │◄──►│   tractor       │◄──►│     (View)      │
│                 │    │  (Controller)   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Componentes Principais

- **PDFTableExtractor**: Classe principal que gerencia a interface e coordena as operações
- **PDFPageLabel**: Widget customizado para exibição e interação com páginas PDF
- **Seleções**: Sistema de coordenadas para definir áreas de extração

## 🔧 Classes e Métodos

### PDFTableExtractor

Classe principal da aplicação que herda de `QWidget`.

#### Atributos Principais

```python
self.pdf_path: str          # Caminho do arquivo PDF
self.doc: fitz.Document     # Documento PyMuPDF
self.page_images: List[QImage]  # Imagens renderizadas das páginas
self.selections: List[Tuple]    # Lista de seleções de tabelas
self.image_labels: List[PDFPageLabel]  # Widgets das páginas
self.global_select_points: List[Tuple] # Pontos de seleção global
```

#### Métodos Principais

##### `init_ui()`
Inicializa a interface gráfica com os componentes principais:
- Botão para abrir PDF
- Área de scroll para visualização
- Botão para salvar tabelas

##### `open_pdf()`
```python
def open_pdf(self):
    """
    Abre um diálogo para seleção de arquivo PDF
    e carrega o documento selecionado.
    """
```

##### `load_pdf()`
```python
def load_pdf(self):
    """
    Carrega o PDF selecionado, renderiza as páginas
    e cria os widgets de visualização.
    
    Processo:
    1. Abre documento com PyMuPDF
    2. Renderiza cada página em 150 DPI
    3. Converte para QImage
    4. Cria PDFPageLabel para cada página
    """
```

##### `add_selection(selection)`
```python
def add_selection(self, selection):
    """
    Adiciona uma nova seleção de tabela.
    
    Args:
        selection (tuple): ((page_idx1, point1), (page_idx2, point2))
        
    Comportamento:
    - Página única: Desenha retângulo vermelho
    - Múltiplas páginas: Desenha retângulos azuis
    """
```

##### `register_click(page_idx, pos)`
```python
def register_click(self, page_idx, pos):
    """
    Registra um clique do usuário para seleção.
    
    Args:
        page_idx (int): Índice da página
        pos (QPoint): Posição do clique
        
    Lógica:
    - Primeiro clique: Inicia seleção
    - Segundo clique: Finaliza seleção
    """
```

##### `save_tables()`
```python
def save_tables(self):
    """
    Salva todas as tabelas selecionadas como imagens PNG.
    
    Processo:
    1. Solicita diretório de destino
    2. Para cada seleção:
       - Extrai região da imagem
       - Combina páginas se necessário
       - Salva com nome descritivo
    3. Limpa seleções ativas
    """
```

### PDFPageLabel

Widget customizado que herda de `QLabel` para exibir páginas PDF com capacidade de seleção.

#### Atributos

```python
self.image: QImage          # Imagem da página
self.page_idx: int          # Índice da página
self.parent: PDFTableExtractor  # Referência ao controlador principal
self.rects: List[Tuple]     # Lista de retângulos desenhados
```

#### Métodos Principais

##### `mousePressEvent(event)`
```python
def mousePressEvent(self, event):
    """
    Manipula eventos de clique do mouse.
    
    Funcionalidade:
    - Primeiro clique: Inicia preview
    - Segundo clique: Finaliza seleção
    - Atualiza visualização de todos os labels
    """
```

##### `paintEvent(event)`
```python
def paintEvent(self, event):
    """
    Renderiza a página e os elementos visuais.
    
    Desenha:
    - Imagem da página PDF
    - Retângulos de seleções confirmadas
    - Preview em tempo real da seleção atual
    - Polígonos para seleções multi-página
    """
```

##### `mouseMoveEvent(event)`
```python
def mouseMoveEvent(event):
    """
    Atualiza preview durante movimento do mouse.
    """
```

## 📊 Fluxo de Dados

### 1. Carregamento de PDF

```mermaid
graph TD
    A[Usuário seleciona PDF] --> B[open_pdf()]
    B --> C[load_pdf()]
    C --> D[PyMuPDF abre documento]
    D --> E[Renderiza páginas em 150 DPI]
    E --> F[Converte para QImage]
    F --> G[Cria PDFPageLabel]
    G --> H[Adiciona ao layout]
```

### 2. Seleção de Tabela

```mermaid
graph TD
    A[Usuário clica na página] --> B[mousePressEvent()]
    B --> C[register_click()]
    C --> D{Primeiro clique?}
    D -->|Sim| E[Inicia preview]
    D -->|Não| F[Finaliza seleção]
    F --> G[add_selection()]
    G --> H[Desenha retângulos]
```

### 3. Extração e Salvamento

```mermaid
graph TD
    A[Usuário clica 'Salvar'] --> B[save_tables()]
    B --> C[Seleciona diretório]
    C --> D[Para cada seleção]
    D --> E{Página única?}
    E -->|Sim| F[Extrai retângulo]
    E -->|Não| G[Combina páginas]
    F --> H[Salva PNG]
    G --> H
    H --> I[Limpa seleções]
```

## 📚 API Reference

### Estrutura de Seleção

```python
selection = ((page_idx1, QPoint), (page_idx2, QPoint))
```

- `page_idx1`: Índice da página inicial (0-based)
- `page_idx2`: Índice da página final (0-based)
- `QPoint`: Coordenadas x,y do clique

### Códigos de Cor

```python
# Cores usadas na interface
SELECTION_PREVIEW = QColor(255, 0, 0)      # Vermelho - Preview página única
MULTI_PAGE_PREVIEW = QColor(0, 0, 255)     # Azul - Preview multi-página
CONFIRMED_SINGLE = QColor(255, 0, 0)       # Vermelho - Seleção confirmada
CONFIRMED_MULTI = QColor(0, 0, 255)        # Azul - Seleção multi-página
```

### Formatos de Arquivo

```python
# Padrão de nomenclatura para arquivos salvos
SINGLE_PAGE = "{pdf_name}_pagina_{page_num}_tabela_{index}.png"
MULTI_PAGE = "{pdf_name}_pagina_{start_page}-{end_page}_tabela_{index}.png"
```

## ⚙️ Configurações Avançadas

### Ajustar Qualidade de Renderização

```python
# Em load_pdf(), linha ~65
pix = page.get_pixmap(dpi=150)  # Padrão: 150 DPI

# Opções recomendadas:
# - 72 DPI: Velocidade máxima, qualidade básica
# - 150 DPI: Balanceado (padrão)
# - 300 DPI: Alta qualidade, uso intensivo de memória
```

### Personalizar Cores

```python
# Em add_selection(), modificar cores dos retângulos
self.image_labels[page_idx].add_rect(rect, color=QColor(255, 0, 0))  # Vermelho

# Em paintEvent(), modificar cores do preview
pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)  # Linha tracejada vermelha
```

### Modificar Espessura das Linhas

```python
# Em paintEvent(), ajustar espessura
pen = QPen(color, 2, Qt.SolidLine)  # 2 pixels de espessura

# Opções:
# - 1: Linha fina
# - 2: Padrão
# - 3+: Linha grossa
```

## 🐛 Debugging

### Logs de Debug

Para adicionar logs de debug, insira estas linhas nos métodos:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

def register_click(self, page_idx, pos):
    logging.debug(f"Clique registrado: página {page_idx}, posição {pos}")
    # ... resto do método
```

### Pontos de Verificação

#### Verificar Carregamento de PDF

```python
def load_pdf(self):
    print(f"Carregando PDF: {self.pdf_path}")
    print(f"Número de páginas: {len(self.doc)}")
    # ... resto do método
```

#### Verificar Seleções

```python
def add_selection(self, selection):
    print(f"Nova seleção: {selection}")
    print(f"Total de seleções: {len(self.selections)}")
    # ... resto do método
```

#### Verificar Salvamento

```python
def save_tables(self):
    print(f"Salvando {len(self.selections)} tabelas")
    # ... resto do método
```

### Problemas Comuns

#### 1. Imagem não aparece
```python
# Verificar se a imagem foi carregada corretamente
if img.isNull():
    print("Erro: Imagem não foi carregada")
```

#### 2. Seleção não funciona
```python
# Verificar eventos de mouse
def mousePressEvent(self, event):
    print(f"Mouse pressionado: {event.pos()}")
    # ... resto do método
```

#### 3. Arquivo não salva
```python
# Verificar permissões e caminho
import os
if not os.access(out_dir, os.W_OK):
    print(f"Erro: Sem permissão de escrita em {out_dir}")
```

### Ferramentas de Profiling

Para medir performance:

```python
import time

def load_pdf(self):
    start_time = time.time()
    # ... código do método
    end_time = time.time()
    print(f"Carregamento levou {end_time - start_time:.2f} segundos")
```

## 📋 Checklist de Manutenção

- [ ] Testar com PDFs de diferentes tamanhos
- [ ] Verificar uso de memória com PDFs grandes
- [ ] Testar seleções em diferentes resoluções
- [ ] Validar nomenclatura de arquivos salvos
- [ ] Testar compatibilidade com diferentes versões do Qt
- [ ] Verificar comportamento com PDFs protegidos
- [ ] Testar interface em diferentes sistemas operacionais

---

Esta documentação deve ser atualizada sempre que mudanças significativas forem feitas no código.
