#!/bin/bash
# Script para facilitar o uso do PDF Table Scanner

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PDF Table Scanner - Launcher${NC}"
echo -e "${BLUE}================================${NC}"

# Verifica se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Ambiente virtual não encontrado!${NC}"
    echo -e "${YELLOW}Execute primeiro: python -m venv .venv${NC}"
    exit 1
fi

# Define o executável Python correto
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON=".venv/Scripts/python.exe"
    PIP=".venv/Scripts/pip.exe"
else
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
fi

# Verifica se o Python existe
if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}❌ Python não encontrado no ambiente virtual!${NC}"
    exit 1
fi

# Menu de opções
echo -e "${GREEN}Escolha uma opção:${NC}"
echo "1. 🎯 Executar PDF Table Scanner"
echo "2. 🧪 Executar teste de instalação"
echo "3. 📊 Executar processador de JSONL"
echo "4. 📦 Instalar/atualizar dependências"
echo "5. 📋 Mostrar pacotes instalados"
echo "6. 🐍 Entrar no Python interativo"
echo "7. ❓ Mostrar informações do sistema"

read -p "Digite sua escolha (1-7): " choice

case $choice in
    1)
        echo -e "${GREEN}🎯 Iniciando PDF Table Scanner...${NC}"
        $PYTHON extrator_tabelas_pdf.py
        ;;
    2)
        echo -e "${GREEN}🧪 Executando teste de instalação...${NC}"
        $PYTHON test_installation.py
        ;;
    3)
        echo -e "${GREEN}📊 Executando processador de JSONL...${NC}"
        $PYTHON processar_jsonl.py
        ;;
    4)
        echo -e "${GREEN}📦 Instalando/atualizando dependências...${NC}"
        $PIP install -r requirements.txt
        ;;
    5)
        echo -e "${GREEN}📋 Pacotes instalados:${NC}"
        $PIP list
        ;;
    6)
        echo -e "${GREEN}🐍 Entrando no Python interativo...${NC}"
        $PYTHON
        ;;
    7)
        echo -e "${GREEN}❓ Informações do sistema:${NC}"
        echo -e "${YELLOW}Python:${NC} $($PYTHON --version)"
        echo -e "${YELLOW}Pip:${NC} $($PIP --version)"
        echo -e "${YELLOW}Ambiente virtual:${NC} $(pwd)/.venv"
        echo -e "${YELLOW}Sistema operacional:${NC} $OSTYPE"
        ;;
    *)
        echo -e "${RED}❌ Opção inválida!${NC}"
        exit 1
        ;;
esac
