"""
Script de prueba para verificar que el backend funciona correctamente
Ejecutar después de instalar las dependencias: pip install -r requirements.txt
"""
import sys
import os

def test_imports():
    """Prueba que todos los imports funcionen"""
    print("Probando imports...")
    try:
        from flask import Flask
        from flask_cors import CORS
        print("✓ Flask y flask-cors importados correctamente")
    except ImportError as e:
        print(f"✗ Error importando Flask: {e}")
        return False
    
    try:
        from document_processor import DocumentProcessor
        print("✓ DocumentProcessor importado correctamente")
    except ImportError as e:
        print(f"✗ Error importando DocumentProcessor: {e}")
        return False
    
    try:
        from pdf_converter import PDFConverter
        print("✓ PDFConverter importado correctamente")
    except ImportError as e:
        print(f"✗ Error importando PDFConverter: {e}")
        return False
    
    try:
        from app import app
        print("✓ App Flask importado correctamente")
    except ImportError as e:
        print(f"✗ Error importando app: {e}")
        return False
    
    return True

def test_initialization():
    """Prueba que los objetos se inicialicen correctamente"""
    print("\nProbando inicialización...")
    try:
        from document_processor import DocumentProcessor
        from pdf_converter import PDFConverter
        
        processor = DocumentProcessor()
        print("✓ DocumentProcessor inicializado")
        
        converter = PDFConverter()
        print(f"✓ PDFConverter inicializado (LibreOffice: {converter.libreoffice_path is not None}, unoconv: {converter.unoconv_path is not None})")
        
        return True
    except Exception as e:
        print(f"✗ Error en inicialización: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_start():
    """Prueba que la app Flask se pueda crear"""
    print("\nProbando creación de app Flask...")
    try:
        from app import app
        print("✓ App Flask creada correctamente")
        print(f"✓ Configuración MAX_CONTENT_LENGTH: {app.config.get('MAX_CONTENT_LENGTH')}")
        return True
    except Exception as e:
        print(f"✗ Error creando app Flask: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("PRUEBA DEL BACKEND - ExamenNaval")
    print("=" * 60)
    
    all_ok = True
    
    all_ok = test_imports() and all_ok
    all_ok = test_initialization() and all_ok
    all_ok = test_app_start() and all_ok
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ TODAS LAS PRUEBAS PASARON")
        print("=" * 60)
        print("\nEl backend está listo para usar.")
        print("Para iniciar el servidor, ejecuta:")
        print("  python app.py")
        print("\nO con gunicorn:")
        print("  gunicorn -w 4 -b 0.0.0.0:5000 app:app")
        sys.exit(0)
    else:
        print("✗ ALGUNAS PRUEBAS FALLARON")
        print("=" * 60)
        print("\nPor favor, instala las dependencias:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

