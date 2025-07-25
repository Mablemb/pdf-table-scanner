#!/usr/bin/env python3
"""
Exemplo de script para processar arquivos JSONL gerados pelo PDF Table Scanner.

Este script demonstra como carregar e processar os dados estruturados das tabelas.
"""

import json
import os
import pandas as pd
from typing import List, Dict, Any

def carregar_jsonl(arquivo_path: str) -> List[Dict[Any, Any]]:
    """
    Carrega dados de um arquivo JSONL.
    
    Args:
        arquivo_path (str): Caminho para o arquivo JSONL
        
    Returns:
        List[Dict]: Lista de objetos JSON
    """
    dados = []
    try:
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    dados.append(json.loads(linha))
        return dados
    except Exception as e:
        print(f"Erro ao carregar {arquivo_path}: {e}")
        return []

def extrair_dados_tabela(tabela_json: Dict[Any, Any]) -> List[pd.DataFrame]:
    """
    Converte dados de tabela JSON em DataFrames do pandas.
    
    Args:
        tabela_json (Dict): Dados da tabela em formato JSON
        
    Returns:
        List[pd.DataFrame]: Lista de DataFrames, um para cada subseção
    """
    dataframes = []
    
    print(f"\n📊 Processando: {tabela_json.get('title', 'Tabela sem título')}")
    print(f"🏷️ Fonte: {tabela_json.get('source', 'Fonte não especificada')}")
    
    for subsecao in tabela_json.get('text', []):
        nome_subsecao = subsecao.get('subsection', 'Subseção sem nome')
        headers = subsecao.get('headers', [])
        rows = subsecao.get('rows', [])
        
        if not rows:
            print(f"⚠️ Subseção '{nome_subsecao}' está vazia")
            continue
        
        # Cria DataFrame
        try:
            if headers:
                df = pd.DataFrame(rows, columns=headers)
            else:
                df = pd.DataFrame(rows)
            
            # Adiciona metadados como atributos
            df.attrs['subsection'] = nome_subsecao
            df.attrs['source'] = tabela_json.get('source', '')
            df.attrs['title'] = tabela_json.get('title', '')
            
            dataframes.append(df)
            
            print(f"✅ Subseção '{nome_subsecao}': {len(rows)} linhas, {len(headers)} colunas")
            
        except Exception as e:
            print(f"❌ Erro ao processar subseção '{nome_subsecao}': {e}")
    
    return dataframes

def analisar_tabela_glasgow(df: pd.DataFrame) -> None:
    """
    Exemplo de análise específica para a Escala de Glasgow.
    
    Args:
        df (pd.DataFrame): DataFrame com dados da escala
    """
    if 'Pontos' not in df.columns:
        return
    
    print(f"\n🔍 Análise da {df.attrs.get('subsection', 'tabela')}:")
    
    # Converte pontos para numérico (ignora 'NT')
    pontos_numericos = pd.to_numeric(df['Pontos'], errors='coerce')
    pontos_validos = pontos_numericos.dropna()
    
    if not pontos_validos.empty:
        print(f"   📈 Pontuação mínima: {pontos_validos.min()}")
        print(f"   📈 Pontuação máxima: {pontos_validos.max()}")
        print(f"   📊 Número de critérios: {len(df)}")
        print(f"   🔢 Critérios com pontuação numérica: {len(pontos_validos)}")

def exportar_para_excel(dataframes: List[pd.DataFrame], arquivo_saida: str) -> None:
    """
    Exporta DataFrames para um arquivo Excel com múltiplas abas.
    
    Args:
        dataframes (List[pd.DataFrame]): Lista de DataFrames
        arquivo_saida (str): Caminho do arquivo Excel de saída
    """
    try:
        with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
            for i, df in enumerate(dataframes):
                nome_aba = df.attrs.get('subsection', f'Tabela_{i+1}')
                # Remove caracteres inválidos para nomes de aba
                nome_aba = nome_aba.replace('/', '_').replace('\\', '_')[:31]
                
                df.to_excel(writer, sheet_name=nome_aba, index=False)
        
        print(f"✅ Dados exportados para: {arquivo_saida}")
        
    except Exception as e:
        print(f"❌ Erro ao exportar para Excel: {e}")

def exportar_para_csv(dataframes: List[pd.DataFrame], pasta_saida: str) -> None:
    """
    Exporta cada DataFrame para um arquivo CSV separado.
    
    Args:
        dataframes (List[pd.DataFrame]): Lista de DataFrames
        pasta_saida (str): Pasta de destino
    """
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)
    
    for i, df in enumerate(dataframes):
        nome_subsecao = df.attrs.get('subsection', f'tabela_{i+1}')
        nome_arquivo = f"{nome_subsecao.replace(' ', '_').replace('/', '_')}.csv"
        caminho_arquivo = os.path.join(pasta_saida, nome_arquivo)
        
        try:
            df.to_csv(caminho_arquivo, index=False, encoding='utf-8')
            print(f"✅ CSV salvo: {caminho_arquivo}")
        except Exception as e:
            print(f"❌ Erro ao salvar CSV {nome_arquivo}: {e}")

def gerar_relatorio_tabela(tabela_json: Dict[Any, Any]) -> str:
    """
    Gera um relatório textual da tabela.
    
    Args:
        tabela_json (Dict): Dados da tabela em JSON
        
    Returns:
        str: Relatório formatado
    """
    relatorio = []
    relatorio.append("=" * 60)
    relatorio.append(f"RELATÓRIO DA TABELA")
    relatorio.append("=" * 60)
    relatorio.append(f"Título: {tabela_json.get('title', 'N/A')}")
    relatorio.append(f"Fonte: {tabela_json.get('source', 'N/A')}")
    relatorio.append(f"Tipo: {tabela_json.get('type', 'N/A')}")
    relatorio.append("")
    
    for i, subsecao in enumerate(tabela_json.get('text', []), 1):
        relatorio.append(f"SUBSEÇÃO {i}: {subsecao.get('subsection', 'N/A')}")
        relatorio.append("-" * 40)
        
        headers = subsecao.get('headers', [])
        rows = subsecao.get('rows', [])
        
        relatorio.append(f"Cabeçalhos: {', '.join(headers) if headers else 'Nenhum'}")
        relatorio.append(f"Número de linhas: {len(rows)}")
        relatorio.append("")
        
        # Mostra algumas linhas de exemplo
        if rows:
            relatorio.append("Primeiras linhas:")
            for j, row in enumerate(rows[:3], 1):
                relatorio.append(f"  {j}. {' | '.join(map(str, row))}")
            if len(rows) > 3:
                relatorio.append(f"  ... e mais {len(rows) - 3} linhas")
        relatorio.append("")
    
    return "\n".join(relatorio)

def main():
    """Função principal - exemplo de uso"""
    print("🔄 Processador de Tabelas JSONL - PDF Table Scanner")
    print("=" * 60)
    
    # Configurações
    pasta_tabelas = "tabelas"
    pasta_saida = "dados_processados"
    
    # Verifica se a pasta existe
    if not os.path.exists(pasta_tabelas):
        print(f"❌ Pasta '{pasta_tabelas}' não encontrada!")
        return
    
    # Encontra arquivos JSONL
    arquivos_jsonl = [f for f in os.listdir(pasta_tabelas) if f.endswith('.jsonl')]
    
    if not arquivos_jsonl:
        print(f"❌ Nenhum arquivo JSONL encontrado em '{pasta_tabelas}'")
        return
    
    print(f"📁 Encontrados {len(arquivos_jsonl)} arquivo(s) JSONL:")
    for arquivo in arquivos_jsonl:
        print(f"   📄 {arquivo}")
    
    # Processa cada arquivo
    todos_dataframes = []
    
    for arquivo in arquivos_jsonl:
        caminho_arquivo = os.path.join(pasta_tabelas, arquivo)
        print(f"\n🔍 Processando: {arquivo}")
        
        # Carrega dados
        dados = carregar_jsonl(caminho_arquivo)
        
        if not dados:
            continue
        
        # Processa cada tabela no arquivo
        for tabela in dados:
            dataframes = extrair_dados_tabela(tabela)
            todos_dataframes.extend(dataframes)
            
            # Análise específica para Glasgow
            for df in dataframes:
                if 'glasgow' in df.attrs.get('source', '').lower():
                    analisar_tabela_glasgow(df)
            
            # Gera relatório
            relatorio = gerar_relatorio_tabela(tabela)
            nome_relatorio = f"relatorio_{arquivo.replace('.jsonl', '.txt')}"
            caminho_relatorio = os.path.join(pasta_tabelas, nome_relatorio)
            
            try:
                with open(caminho_relatorio, 'w', encoding='utf-8') as f:
                    f.write(relatorio)
                print(f"📄 Relatório salvo: {caminho_relatorio}")
            except Exception as e:
                print(f"❌ Erro ao salvar relatório: {e}")
    
    if todos_dataframes:
        print(f"\n📊 Total de DataFrames processados: {len(todos_dataframes)}")
        
        # Exporta dados
        if not os.path.exists(pasta_saida):
            os.makedirs(pasta_saida)
        
        # Exportar para Excel
        arquivo_excel = os.path.join(pasta_saida, "todas_tabelas.xlsx")
        exportar_para_excel(todos_dataframes, arquivo_excel)
        
        # Exportar para CSV
        pasta_csv = os.path.join(pasta_saida, "csv")
        exportar_para_csv(todos_dataframes, pasta_csv)
        
        print(f"\n✅ Processamento concluído!")
        print(f"📁 Arquivos de saída em: {pasta_saida}")
    
    else:
        print("❌ Nenhum dado foi processado.")

if __name__ == "__main__":
    # Exemplo de como usar as funções individualmente
    
    # Para testar com um arquivo específico:
    # dados = carregar_jsonl("tabelas/exemplo.jsonl")
    # for tabela in dados:
    #     dfs = extrair_dados_tabela(tabela)
    #     exportar_para_excel(dfs, "exemplo.xlsx")
    
    main()
