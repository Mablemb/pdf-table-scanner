# Contribuindo para o PDF Table Scanner

Obrigado por seu interesse em contribuir com o PDF Table Scanner! Este documento fornece diretrizes e informações para contribuidores.

## 📋 Índice

1. [Como Contribuir](#como-contribuir)
2. [Reportando Bugs](#reportando-bugs)
3. [Sugerindo Melhorias](#sugerindo-melhorias)
4. [Desenvolvimento](#desenvolvimento)
5. [Padrões de Código](#padrões-de-código)
6. [Processo de Pull Request](#processo-de-pull-request)
7. [Configuração do Ambiente](#configuração-do-ambiente)

## 🤝 Como Contribuir

Existem várias maneiras de contribuir:

- 🐛 **Reportar bugs**
- 💡 **Sugerir melhorias**
- 📝 **Melhorar documentação**
- 💻 **Contribuir com código**
- 🧪 **Escrever testes**
- 🌍 **Traduzir a interface**

## 🐛 Reportando Bugs

Antes de reportar um bug:

1. **Verifique se já foi reportado** nas [Issues](https://github.com/Mablemb/pdf-table-scanner/issues)
2. **Teste com a versão mais recente**
3. **Reproduza o problema** com passos claros

### Template para Bug Report

```markdown
**Descrição do Bug**
Uma descrição clara e concisa do que é o bug.

**Para Reproduzir**
Passos para reproduzir o comportamento:
1. Vá para '...'
2. Clique em '....'
3. Faça scroll até '....'
4. Veja o erro

**Comportamento Esperado**
Uma descrição clara do que você esperava que acontecesse.

**Screenshots**
Se aplicável, adicione screenshots para ajudar a explicar o problema.

**Ambiente:**
- SO: [ex: Windows 10, Ubuntu 20.04, macOS Big Sur]
- Versão do Python: [ex: 3.8.5]
- Versão do PyQt5: [ex: 5.15.4]
- Versão do projeto: [ex: 1.0.0]

**Informações Adicionais**
Qualquer outro contexto sobre o problema aqui.
```

## 💡 Sugerindo Melhorias

Para sugerir uma melhoria:

1. **Abra uma Issue** com o label `enhancement`
2. **Descreva a funcionalidade** detalhadamente
3. **Explique o caso de uso** e benefícios
4. **Considere implementações alternativas**

### Template para Feature Request

```markdown
**A funcionalidade está relacionada a um problema? Descreva.**
Uma descrição clara do problema. Ex: Estou sempre frustrado quando [...]

**Descreva a solução que você gostaria**
Uma descrição clara do que você quer que aconteça.

**Descreva alternativas consideradas**
Uma descrição clara de soluções ou funcionalidades alternativas.

**Contexto Adicional**
Qualquer outro contexto ou screenshots sobre a funcionalidade aqui.
```

## 💻 Desenvolvimento

### Configuração do Ambiente

```bash
# 1. Fork o repositório no GitHub

# 2. Clone seu fork
git clone https://github.com/SEU_USUARIO/pdf-table-scanner.git
cd pdf-table-scanner

# 3. Adicione o repositório original como upstream
git remote add upstream https://github.com/Mablemb/pdf-table-scanner.git

# 4. Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# 5. Instale dependências de desenvolvimento
pip install -r requirements.txt
pip install -r requirements-dev.txt  # quando existir

# 6. Crie uma branch para sua feature
git checkout -b feature/nova-funcionalidade
```

### Estrutura do Projeto

```
pdf-table-scanner/
├── extrator_tabelas_pdf.py    # Aplicação principal
├── LivrosPDF/                 # PDFs de teste
├── tabelas/                   # Saída de exemplo
├── tests/                     # Testes (futuro)
├── docs/                      # Documentação adicional (futuro)
├── README.md                  # Documentação principal
├── DOCUMENTATION.md           # Docs técnicas
├── INSTALL.md                 # Guia de instalação
├── CONTRIBUTING.md            # Este arquivo
├── CHANGELOG.md               # Histórico de mudanças
└── requirements.txt           # Dependências
```

## 📏 Padrões de Código

### Estilo Python

Seguimos o [PEP 8](https://pep8.org/) com algumas adaptações:

```python
# ✅ Correto
def carregar_pdf(self, caminho_arquivo):
    """
    Carrega um arquivo PDF e renderiza suas páginas.
    
    Args:
        caminho_arquivo (str): Caminho para o arquivo PDF
        
    Returns:
        bool: True se carregado com sucesso
    """
    try:
        self.doc = fitz.open(caminho_arquivo)
        return True
    except Exception as e:
        logging.error(f"Erro ao carregar PDF: {e}")
        return False

# ❌ Incorreto
def carregarPdf(self,caminhoArquivo):
    self.doc=fitz.open(caminhoArquivo)
```

### Comentários e Documentação

```python
# ✅ Bons comentários
class PDFTableExtractor(QWidget):
    """
    Widget principal para extração de tabelas de PDF.
    
    Esta classe gerencia a interface gráfica e coordena as operações
    de visualização, seleção e extração de tabelas.
    """
    
    def __init__(self):
        super().__init__()
        self.selections = []  # Lista de seleções: [(start, end), ...]
        self.init_ui()

# ❌ Comentários desnecessários
x = x + 1  # Incrementa x em 1
```

### Tratamento de Erros

```python
# ✅ Tratamento específico
try:
    self.doc = fitz.open(self.pdf_path)
except fitz.FileNotFoundError:
    QMessageBox.critical(self, "Erro", "Arquivo PDF não encontrado")
except fitz.FileDataError:
    QMessageBox.critical(self, "Erro", "Arquivo PDF corrompido")
except Exception as e:
    QMessageBox.critical(self, "Erro", f"Erro inesperado: {e}")

# ❌ Captura genérica demais
try:
    # código que pode falhar
    pass
except:
    pass
```

### Nomes de Variáveis

```python
# ✅ Nomes descritivos
page_index = 0
selection_rectangle = QRect()
pdf_document_path = "/path/to/file.pdf"

# ❌ Nomes não descritivos
i = 0
rect = QRect()
path = "/path/to/file.pdf"
```

## 🔄 Processo de Pull Request

### Antes de Submeter

1. **Teste sua mudança** completamente
2. **Atualize a documentação** se necessário
3. **Adicione testes** quando aplicável
4. **Execute linting** e corrija problemas
5. **Verifique se não quebrou funcionalidades existentes**

### Criando o Pull Request

1. **Commit suas mudanças**:
   ```bash
   git add .
   git commit -m "feat: adiciona detecção automática de tabelas"
   ```

2. **Push para seu fork**:
   ```bash
   git push origin feature/nova-funcionalidade
   ```

3. **Abra um Pull Request** no GitHub

### Template para Pull Request

```markdown
**Descrição**
Breve descrição das mudanças realizadas.

**Tipo de Mudança**
- [ ] Bug fix (mudança que corrige um problema)
- [ ] Nova funcionalidade (mudança que adiciona funcionalidade)
- [ ] Breaking change (correção ou funcionalidade que quebra compatibilidade)
- [ ] Atualização de documentação

**Como Foi Testado?**
Descreva os testes realizados para verificar as mudanças.

**Checklist:**
- [ ] Meu código segue os padrões do projeto
- [ ] Realizei auto-revisão do código
- [ ] Comentei o código em partes difíceis de entender
- [ ] Atualizei a documentação correspondente
- [ ] Minhas mudanças não geram novos warnings
- [ ] Testei que funciona conforme esperado
```

### Convenções de Commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Tipos principais
feat: nova funcionalidade
fix: correção de bug
docs: mudanças na documentação
style: formatação, pontos e vírgulas, etc
refactor: mudança de código que não adiciona funcionalidade nem corrige bugs
test: adição ou correção de testes
chore: mudanças no processo de build, ferramentas auxiliares, etc

# Exemplos
git commit -m "feat: adiciona suporte para OCR em tabelas"
git commit -m "fix: corrige crash ao abrir PDFs grandes"
git commit -m "docs: atualiza guia de instalação"
git commit -m "refactor: simplifica lógica de seleção"
```

## 🧪 Testes

### Executando Testes

```bash
# Quando implementados
python -m pytest tests/
python -m pytest tests/ --cov=extrator_tabelas_pdf
```

### Escrevendo Testes

```python
import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
from extrator_tabelas_pdf import PDFTableExtractor

class TestPDFTableExtractor(unittest.TestCase):
    
    def setUp(self):
        if not QApplication.instance():
            self.app = QApplication([])
        self.extractor = PDFTableExtractor()
    
    def test_abrir_pdf_valido(self):
        """Testa abertura de PDF válido"""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_open.return_value = mock_doc
            
            resultado = self.extractor.abrir_pdf("test.pdf")
            
            self.assertTrue(resultado)
            mock_open.assert_called_once_with("test.pdf")
```

## 🌍 Tradução

Para adicionar suporte a um novo idioma:

1. Crie arquivo `translations/pt_BR.py` (exemplo)
2. Adicione strings traduzidas
3. Implemente sistema de carregamento
4. Teste com o novo idioma

## 📝 Documentação

### Atualizando Documentação

- **README.md**: Informações gerais e uso básico
- **DOCUMENTATION.md**: Documentação técnica detalhada
- **INSTALL.md**: Guias de instalação
- **CHANGELOG.md**: Histórico de mudanças

### Adicionando Screenshots

1. Use formato PNG ou JPG
2. Mantenha resolução entre 800-1200px de largura
3. Salve em `docs/images/` (quando existir)
4. Use nomes descritivos: `interface-principal.png`

## 🏷️ Versionamento

Seguimos [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Mudanças incompatíveis
- **MINOR** (0.1.0): Novas funcionalidades compatíveis
- **PATCH** (0.0.1): Correções de bugs

## 🎉 Reconhecimento

Contribuidores são reconhecidos:

- No README.md
- Nos releases do GitHub
- Em comentários no código (para contribuições significativas)

## 💬 Comunicação

- **Issues**: Para bugs e sugestões
- **Discussions**: Para perguntas gerais
- **Email**: Para questões sensíveis

## 📜 Código de Conduta

Este projeto adere ao [Contributor Covenant](https://www.contributor-covenant.org/). Ao participar, você concorda em manter um ambiente respeitoso e acolhedor.

---

## 🙏 Agradecimentos

Obrigado por considerar contribuir com o PDF Table Scanner! Sua ajuda é muito valiosa para tornar esta ferramenta ainda melhor.

**Lembre-se**: Nenhuma contribuição é pequena demais. Desde correção de typos até grandes funcionalidades, toda ajuda é bem-vinda! 🚀
