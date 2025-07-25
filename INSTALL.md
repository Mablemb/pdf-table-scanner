# Guia de Instalação - PDF Table Scanner

## 🚀 Instalação Rápida

### Opção 1: Instalação Automática (Recomendada)

```bash
# Clone o repositório
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python extrator_tabelas_pdf.py
```

### Opção 2: Instalação Manual

```bash
# Instale as dependências uma por uma
pip install PyQt5>=5.15.0
pip install PyMuPDF>=1.20.0
pip install Pillow>=8.0.0
```

## 🖥️ Requisitos do Sistema

### Requisitos Mínimos
- **Python**: 3.6 ou superior
- **RAM**: 2GB mínimo (4GB recomendado)
- **Espaço em Disco**: 100MB para a aplicação + espaço para PDFs
- **Sistema Operacional**: Windows 7+, macOS 10.12+, Linux (Ubuntu 16.04+)

### Requisitos Recomendados
- **Python**: 3.8 ou superior
- **RAM**: 8GB ou mais
- **CPU**: Processador multi-core para melhor performance
- **Monitor**: 1920x1080 ou superior

## 🐧 Instalação no Linux

### Ubuntu/Debian

```bash
# Atualize o sistema
sudo apt update && sudo apt upgrade

# Instale Python e pip (se não estiver instalado)
sudo apt install python3 python3-pip

# Instale dependências do sistema para PyQt5
sudo apt install python3-pyqt5 python3-pyqt5-dev

# Clone e configure o projeto
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
pip3 install -r requirements.txt

# Execute a aplicação
python3 extrator_tabelas_pdf.py
```

### Fedora/CentOS/RHEL

```bash
# Instale Python e pip
sudo dnf install python3 python3-pip

# Instale dependências do sistema
sudo dnf install python3-qt5 python3-qt5-devel

# Clone e configure o projeto
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
pip3 install -r requirements.txt

# Execute a aplicação
python3 extrator_tabelas_pdf.py
```

### Arch Linux

```bash
# Instale dependências
sudo pacman -S python python-pip python-pyqt5

# Clone e configure o projeto
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
pip install -r requirements.txt

# Execute a aplicação
python extrator_tabelas_pdf.py
```

## 🍎 Instalação no macOS

### Usando Homebrew

```bash
# Instale Homebrew (se não estiver instalado)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instale Python
brew install python

# Instale PyQt5
brew install pyqt5

# Clone e configure o projeto
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
pip3 install -r requirements.txt

# Execute a aplicação
python3 extrator_tabelas_pdf.py
```

### Usando MacPorts

```bash
# Instale Python e PyQt5
sudo port install python39 py39-pyqt5

# Clone e configure o projeto
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
pip3 install -r requirements.txt

# Execute a aplicação
python3 extrator_tabelas_pdf.py
```

## 🪟 Instalação no Windows

### Opção 1: Usando pip

```cmd
# Baixe e instale Python do site oficial (python.org)
# Certifique-se de marcar "Add to PATH" durante a instalação

# Abra o Command Prompt ou PowerShell
# Clone o repositório (ou baixe o ZIP)
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python extrator_tabelas_pdf.py
```

### Opção 2: Usando Anaconda

```cmd
# Baixe e instale Anaconda
# Abra o Anaconda Prompt

# Crie um ambiente virtual
conda create -n pdf-scanner python=3.8
conda activate pdf-scanner

# Instale as dependências
conda install pyqt
pip install PyMuPDF Pillow

# Clone e execute
git clone https://github.com/Mablemb/pdf-table-scanner.git
cd pdf-table-scanner
python extrator_tabelas_pdf.py
```

## 🐍 Ambiente Virtual (Recomendado)

### Usando venv

```bash
# Crie um ambiente virtual
python3 -m venv pdf-scanner-env

# Ative o ambiente
# Linux/macOS:
source pdf-scanner-env/bin/activate
# Windows:
pdf-scanner-env\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python extrator_tabelas_pdf.py
```

### Usando conda

```bash
# Crie um ambiente conda
conda create -n pdf-scanner python=3.8
conda activate pdf-scanner

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
python extrator_tabelas_pdf.py
```

## 🔍 Verificação da Instalação

Execute este script para verificar se tudo está funcionando:

```python
# teste_instalacao.py
try:
    import sys
    print(f"✅ Python {sys.version}")
    
    import PyQt5
    print(f"✅ PyQt5 {PyQt5.Qt.PYQT_VERSION_STR}")
    
    import fitz
    print(f"✅ PyMuPDF {fitz.version[0]}")
    
    from PIL import Image
    print(f"✅ Pillow {Image.__version__ if hasattr(Image, '__version__') else 'instalado'}")
    
    print("\n🎉 Todas as dependências estão instaladas corretamente!")
    print("Execute: python extrator_tabelas_pdf.py")
    
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("Execute: pip install -r requirements.txt")
```

## 🛠️ Solução de Problemas

### Erro: "No module named 'PyQt5'"

```bash
# Linux
sudo apt install python3-pyqt5-dev

# macOS
brew install pyqt5

# Windows/Geral
pip install PyQt5
```

### Erro: "No module named 'fitz'"

```bash
pip install PyMuPDF
```

### Erro: "Permission denied" no Linux

```bash
# Adicione ao PATH do usuário
export PATH=$PATH:~/.local/bin

# Ou instale para o usuário
pip install --user -r requirements.txt
```

### Erro de Display no Linux (X11)

```bash
# Se executando via SSH
ssh -X usuario@servidor

# Ou instale dependências X11
sudo apt install xauth xorg
```

### Problemas de Performance

```bash
# Para PDFs grandes, aumente a memória virtual
# Linux:
sudo sysctl vm.max_map_count=262144

# Ou reduza o DPI no código (linha 65):
pix = page.get_pixmap(dpi=100)  # ao invés de 150
```

## 📦 Criando um Executável

### Usando PyInstaller

```bash
# Instale PyInstaller
pip install pyinstaller

# Crie o executável
pyinstaller --onefile --windowed extrator_tabelas_pdf.py

# O executável estará em dist/
```

### Usando cx_Freeze

```bash
# Instale cx_Freeze
pip install cx_Freeze

# Crie o setup.py
cat > setup.py << EOF
from cx_Freeze import setup, Executable

setup(
    name="PDF Table Scanner",
    version="1.0",
    description="Extrator de Tabelas PDF",
    executables=[Executable("extrator_tabelas_pdf.py")]
)
EOF

# Compile
python setup.py build
```

## 🔄 Atualizações

### Atualizando Dependências

```bash
# Atualize todas as dependências
pip install --upgrade -r requirements.txt

# Ou individualmente
pip install --upgrade PyQt5 PyMuPDF Pillow
```

### Atualizando o Projeto

```bash
# Pull das últimas mudanças
git pull origin main

# Reinstale dependências se necessário
pip install -r requirements.txt
```

## 📞 Suporte à Instalação

Se você encontrar problemas durante a instalação:

1. **Verifique a versão do Python**: `python --version`
2. **Verifique o pip**: `pip --version`
3. **Teste as importações** com o script de verificação acima
4. **Consulte os logs de erro** para detalhes específicos
5. **Abra uma issue** no GitHub com:
   - Sistema operacional
   - Versão do Python
   - Mensagem de erro completa
   - Passos que levaram ao erro

## ✅ Checklist de Instalação

- [ ] Python 3.6+ instalado
- [ ] pip funcionando corretamente
- [ ] PyQt5 instalado e funcionando
- [ ] PyMuPDF instalado
- [ ] Pillow instalado
- [ ] Projeto clonado/baixado
- [ ] Aplicação executando sem erros
- [ ] Interface gráfica aparecendo
- [ ] Capaz de abrir um PDF teste

---

🎯 **Dica**: Mantenha sempre as dependências atualizadas para melhor compatibilidade e segurança!
