# Guia de Conversão de Tabelas para JSONL

Este guia explica como usar a nova funcionalidade de visualização e conversão de tabelas extraídas para o formato JSONL estruturado.

## 🎯 Visão Geral

A funcionalidade de conversão permite transformar imagens de tabelas extraídas em dados estruturados no formato JSON Lines (JSONL), facilitando o processamento posterior dos dados.

## 🚀 Como Usar

### 1. Acessando o Visualizador

Após extrair tabelas do PDF:

1. Clique no botão **"Visualizar Tabelas Extraídas"** na interface principal
2. O visualizador será aberto em uma nova janela

### 2. Interface do Visualizador

A interface é dividida em duas partes principais:

#### Painel Esquerdo - Visualização
- **Seletor de Tabelas**: Lista suspensa com todas as imagens de tabelas
- **Visualização de Imagem**: Mostra a imagem da tabela selecionada

#### Painel Direito - Editor de Dados
- **Aba Metadados**: Campos para tipo, fonte e título
- **Aba Estrutura da Tabela**: Editor para subseções e dados
- **Aba Preview JSON**: Visualização do JSON gerado

### 3. Preenchendo Metadados

Na aba **"Metadados"**:

```
Tipo: table (padrão)
Fonte: Nome da fonte (ex: "Escala de Coma de Glasgow")
Título: Título da tabela (ex: "TABELA 1 – Escala de Coma de Glasgow")
```

### 4. Configurando Subseções

Na aba **"Estrutura da Tabela"**:

1. **Adicionar Subseção**: Clique em "Adicionar Subseção"
2. **Nome da Subseção**: Digite o nome (ex: "Resposta ocular")
3. **Cabeçalhos**: Digite os cabeçalhos separados por vírgula
4. **Dados**: Preencha a tabela interativa com os dados

#### Gerenciando a Tabela de Dados

- **+ Linha**: Adiciona uma nova linha
- **- Linha**: Remove a última linha
- **+ Coluna**: Adiciona uma nova coluna
- **- Coluna**: Remove a última coluna

### 5. Exemplo Prático

Para a **Escala de Coma de Glasgow**:

#### Metadados:
- **Tipo**: table
- **Fonte**: Escala de Coma de Glasgow
- **Título**: TABELA 1 – Escala de Coma de Glasgow

#### Subseção 1: Resposta ocular
- **Nome**: Resposta ocular
- **Cabeçalhos**: Critério, Classificação, Pontos
- **Dados**:
  ```
  Olhos abertos previamente à estimulação | Espontânea | 4
  Abertura ocular após ordem em voz normal | Ao som | 3
  Abertura ocular após estimulação na extremidade | À pressão | 2
  Ausência de abertura ocular | Ausente | 1
  Olhos fechados devido a fator local | Não testável | NT
  ```

#### Subseção 2: Resposta verbal
- **Nome**: Resposta verbal
- **Cabeçalhos**: Critério, Classificação, Pontos
- **Dados**: (similar ao exemplo acima)

### 6. Visualizando o JSON

Na aba **"Preview JSON"**:

1. Clique em **"Atualizar Preview"**
2. Visualize o JSON gerado
3. Verifique se a estrutura está correta

### 7. Salvando os Dados

#### Opção 1: Salvar Tabela Individual
1. Clique em **"Salvar JSONL"**
2. Escolha o local e nome do arquivo
3. O arquivo será salvo com extensão `.jsonl`

#### Opção 2: Exportar Todas as Tabelas
1. Clique em **"Exportar Todas"**
2. Todas as tabelas configuradas serão salvas em um arquivo único

## 📋 Formato de Saída

### Estrutura do JSON

```json
{
  "type": "table",
  "source": "Escala de Coma de Glasgow",
  "title": "TABELA 1 – Escala de Coma de Glasgow",
  "text": [
    {
      "subsection": "Resposta ocular",
      "headers": ["Critério", "Classificação", "Pontos"],
      "rows": [
        ["Olhos abertos previamente à estimulação", "Espontânea", "4"],
        ["Abertura ocular após ordem em voz normal ou em voz alta", "Ao som", "3"],
        ["Abertura ocular após estimulação na extremidade dos dedos (10 s)", "À pressão", "2"],
        ["Ausência de abertura ocular, sem fatores de interferência", "Ausente", "1"],
        ["Olhos fechados devido a fator local", "Não testável", "NT"]
      ]
    },
    {
      "subsection": "Resposta verbal",
      "headers": ["Critério", "Classificação", "Pontos"],
      "rows": [
        ["Resposta adequada relativamente ao nome, local e data", "Orientada", "5"],
        ["Resposta não orientada, mas comunicação coerente", "Confusa", "4"],
        ["Palavras isoladas, inteligíveis", "Palavras", "3"],
        ["Apenas gemidos ou ruídos ininteligíveis", "Sons", "2"],
        ["Ausência de resposta audível, sem fatores de interferência", "Ausente", "1"],
        ["Fator que interfere com a comunicação", "Não testável", "NT"]
      ]
    }
  ]
}
```

### Arquivo JSONL

O arquivo final será salvo no formato JSON Lines, onde cada linha é um objeto JSON válido:

```jsonl
{"type": "table", "source": "Escala de Coma de Glasgow", "title": "TABELA 1 – Escala de Coma de Glasgow", "text": [...]}
```

## 🎨 Dicas de Uso

### 1. Preenchimento Eficiente
- Use **Tab** para navegar entre células da tabela
- Copie e cole dados de outras fontes quando apropriado
- Use os botões de adicionar/remover para ajustar o tamanho da tabela

### 2. Estruturação de Dados
- Mantenha consistência nos cabeçalhos entre subseções similares
- Use nomes descritivos para subseções
- Verifique o preview JSON antes de salvar

### 3. Organização de Arquivos
- Os arquivos JSONL são salvos por padrão na pasta `tabelas/`
- Use nomes descritivos para facilitar identificação
- Mantenha backup dos arquivos originais (imagens)

## 🔧 Solução de Problemas

### Tabela não carrega
- Verifique se há imagens na pasta `tabelas/`
- Certifique-se de que as imagens têm extensões válidas (.png, .jpg, .jpeg)

### Dados não aparecem no preview
- Clique em "Atualizar Preview" após fazer alterações
- Verifique se os campos obrigatórios estão preenchidos

### Erro ao salvar
- Verifique permissões de escrita na pasta de destino
- Certifique-se de que o nome do arquivo é válido

## 📚 Casos de Uso

### 1. Pesquisa Médica
- Conversão de escalas médicas (Glasgow, APACHE, etc.)
- Tabelas de dosagem de medicamentos
- Protocolos de atendimento

### 2. Dados Financeiros
- Tabelas de preços
- Relatórios financeiros
- Planilhas de orçamento

### 3. Dados Científicos
- Resultados experimentais
- Tabelas de referência
- Classificações e taxonomias

## 🚀 Próximos Passos

Após gerar os arquivos JSONL, você pode:

1. **Importar em bancos de dados**
2. **Processar com scripts Python/R**
3. **Integrar com sistemas de ML/IA**
4. **Criar dashboards e visualizações**
5. **Fazer análises estatísticas**

---

💡 **Dica**: Mantenha sempre uma cópia das imagens originais para referência e possíveis ajustes futuros!
