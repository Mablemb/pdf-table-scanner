# Teste de Instalação - PDF Table Scanner

"""
Script para verificar se todas as dependências estão instaladas corretamente.
Execute este arquivo para validar sua instalação.
"""

import sys
import platform

def test_python_version():
    """Testa se a versão do Python é compatível"""
    print("🐍 Testando versão do Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 6:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Versão muito antiga")
        print("   Necessário Python 3.6+")
        return False

def test_dependencies():
    """Testa se todas as dependências estão disponíveis"""
    dependencies = [
        ("PyQt5", "PyQt5"),
        ("PyMuPDF", "fitz"),
        ("Pillow", "PIL")
    ]
    
    all_ok = True
    
    for name, module in dependencies:
        try:
            print(f"📦 Testando {name}...")
            imported = __import__(module)
            
            # Tenta obter versão quando possível
            version = ""
            if hasattr(imported, '__version__'):
                version = f" v{imported.__version__}"
            elif hasattr(imported, 'version'):
                if isinstance(imported.version, tuple):
                    version = f" v{'.'.join(map(str, imported.version))}"
                else:
                    version = f" v{imported.version}"
            elif module == "PyQt5" and hasattr(imported, 'Qt'):
                version = f" v{imported.Qt.PYQT_VERSION_STR}"
            elif module == "fitz" and hasattr(imported, 'version'):
                version = f" v{imported.version[0]}"
            
            print(f"✅ {name}{version} - OK")
        
        except ImportError as e:
            print(f"❌ {name} - ERRO: {e}")
            print(f"   Execute: pip install {name}")
            all_ok = False
        except Exception as e:
            print(f"⚠️ {name} - Importado mas com problemas: {e}")
    
    return all_ok

def test_gui_availability():
    """Testa se a interface gráfica pode ser inicializada"""
    try:
        print("🖥️ Testando disponibilidade da interface gráfica...")
        from PyQt5.QtWidgets import QApplication
        
        # Tenta criar uma aplicação (sem exibir)
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        print("✅ Interface gráfica - OK")
        return True
    
    except Exception as e:
        print(f"❌ Interface gráfica - ERRO: {e}")
        if "DISPLAY" in str(e) or "xcb" in str(e).lower():
            print("   Problema: Sem servidor X11/Display disponível")
            print("   Solução: Execute em ambiente gráfico ou use SSH com -X")
        return False

def test_file_access():
    """Testa se é possível acessar arquivos necessários"""
    import os
    
    print("📁 Testando acesso a arquivos...")
    
    # Testa acesso ao arquivo principal
    main_file = "extrator_tabelas_pdf.py"
    if os.path.exists(main_file):
        print(f"✅ {main_file} - Encontrado")
    else:
        print(f"❌ {main_file} - Não encontrado")
        return False
    
    # Testa se pode criar arquivos temporários
    try:
        test_file = "test_write_permission.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("✅ Permissões de escrita - OK")
    except Exception as e:
        print(f"❌ Permissões de escrita - ERRO: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Testa funcionalidades básicas do PDF Table Scanner"""
    try:
        print("⚙️ Testando funcionalidades básicas...")
        
        # Importa as classes principais
        from PyQt5.QtWidgets import QApplication, QWidget
        from PyQt5.QtGui import QImage, QPainter
        from PyQt5.QtCore import QRect, QPoint
        import fitz
        
        # Testa criação de imagem
        img = QImage(100, 100, QImage.Format_RGB888)
        img.fill(0)
        
        # Testa operações básicas
        rect = QRect(QPoint(10, 10), QPoint(50, 50))
        
        print("✅ Funcionalidades básicas - OK")
        return True
        
    except Exception as e:
        print(f"❌ Funcionalidades básicas - ERRO: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 PDF Table Scanner - Teste de Instalação")
    print("=" * 50)
    print(f"Sistema: {platform.system()} {platform.release()}")
    print(f"Arquitetura: {platform.machine()}")
    print("=" * 50)
    
    tests = [
        ("Versão do Python", test_python_version),
        ("Dependências", test_dependencies),
        ("Interface Gráfica", test_gui_availability),
        ("Acesso a Arquivos", test_file_access),
        ("Funcionalidades Básicas", test_basic_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro inesperado no teste: {e}")
            results.append((test_name, False))
    
    # Relatório final
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Testes passaram: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 INSTALAÇÃO OK!")
        print("Execute: python extrator_tabelas_pdf.py")
        return 0
    else:
        print(f"\n❌ {total - passed} teste(s) falharam")
        print("Verifique as mensagens de erro acima")
        print("Consulte INSTALL.md para mais informações")
        return 1

if __name__ == "__main__":
    sys.exit(main())
