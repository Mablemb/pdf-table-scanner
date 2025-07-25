# Changelog

Todas as mudanças importantes do projeto PDF Table Scanner serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### 🎯 Planejado
- Suporte para OCR nas tabelas extraídas
- Exportação para formatos CSV/Excel
- Detecção automática de tabelas
- Interface para edição de seleções
- Suporte para batch processing
- Histórico de extrações

## [1.0.0] - 2025-01-XX

### ✨ Adicionado
- Interface gráfica completa com PyQt5
- Visualização de páginas PDF em alta qualidade (150 DPI)
- Seleção interativa de áreas de tabelas com dois cliques
- Suporte para tabelas que se estendem por múltiplas páginas
- Preview visual em tempo real da área sendo selecionada
- Exportação automática de tabelas como imagens PNG
- Sistema de nomenclatura automática para arquivos salvos
- Indicadores visuais coloridos para diferentes tipos de seleção
- Suporte para scroll através das páginas do PDF
- Limpeza automática de seleções após salvamento

### 🎨 Interface
- Botão "Escolher PDF" para seleção de arquivos
- Área de scroll responsiva para visualização de páginas
- Botão "Salvar Tabelas Selecionadas" para exportação
- Preview com linhas tracejadas (vermelho para página única, azul para múltiplas páginas)
- Retângulos sólidos para seleções confirmadas

### 🔧 Funcionalidades Técnicas
- Renderização de PDF usando PyMuPDF (fitz)
- Manipulação de imagens com PIL/Pillow
- Sistema de coordenadas para seleções precisas
- Combinação automática de imagens para tabelas multi-página
- Gerenciamento de memória otimizado para PDFs grandes

### 📁 Estrutura de Arquivos
- `extrator_tabelas_pdf.py` - Aplicação principal
- `LivrosPDF/` - Diretório com PDFs de exemplo
- `tabelas/` - Diretório para tabelas extraídas
- `README.md` - Documentação principal
- `DOCUMENTATION.md` - Documentação técnica detalhada
- `INSTALL.md` - Guia de instalação completo
- `requirements.txt` - Dependências do projeto

### 🐛 Correções
- Correção de importações duplicadas no início do arquivo
- Melhoria na detecção de eventos de mouse
- Otimização do sistema de preview visual
- Correção na combinação de imagens multi-página

### 📚 Documentação
- README completo com instruções de uso
- Documentação técnica detalhada
- Guia de instalação para múltiplos sistemas operacionais
- Exemplos de uso e screenshots
- Seção de solução de problemas
- Roadmap de funcionalidades futuras

### 🔒 Segurança
- Validação de arquivos PDF antes da abertura
- Verificação de permissões de escrita antes do salvamento
- Tratamento de erros robusto

---

## 🏷️ Formato das Versões

Este projeto usa [Semantic Versioning](https://semver.org/):

- **MAJOR**: Mudanças incompatíveis na API
- **MINOR**: Funcionalidades adicionadas de forma compatível
- **PATCH**: Correções de bugs compatíveis

## 📋 Tipos de Mudanças

- `✨ Adicionado` para novas funcionalidades
- `🔄 Modificado` para mudanças em funcionalidades existentes
- `❌ Descontinuado` para funcionalidades que serão removidas
- `🗑️ Removido` para funcionalidades removidas
- `🐛 Corrigido` para correções de bugs
- `🔒 Segurança` para vulnerabilidades corrigidas

---

## 🤝 Como Contribuir com o Changelog

Ao fazer mudanças no projeto:

1. Adicione suas mudanças na seção `[Não Lançado]`
2. Use o formato apropriado de tipos de mudanças
3. Seja descritivo mas conciso
4. Inclua referências de issues quando aplicável
5. Mova itens para uma nova versão quando lançar

Exemplo:
```markdown
### ✨ Adicionado
- Nova funcionalidade de detecção automática de tabelas (#123)
- Suporte para arquivos protegidos por senha (#456)

### 🐛 Corrigido
- Correção de crash ao abrir PDFs muito grandes (#789)
- Melhoria na precisão da seleção em telas de alta resolução (#101)
```
