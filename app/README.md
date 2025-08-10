Read Like A King - Desktop (Prototipo simple)

Contenido:
- main.py : aplicación principal
- requirements.txt : dependencias (pip install -r requirements.txt)

Requisitos para ejecutar localmente:
- Python 3.8+
- pip install -r requirements.txt
- En Windows: para abrir CBR necesitas instalar 'unrar' y que 'unrar.exe' esté en PATH, o instalar WinRAR.

Ejecutar:
python main.py

Para generar .exe con PyInstaller (en Windows):
1. pip install pyinstaller
2. pyinstaller --onefile --add-data "<path_to_tcl_tk>" main.py (opcionalmente incluir recursos)

GitHub Actions (ya incluido) puede compilar el exe en un runner windows-latest.
