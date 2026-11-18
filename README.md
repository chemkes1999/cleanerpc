# ⚡ PyClean Pro v2.1 - Suite de Optimización, Limpieza y Privacidad para Windows

Una aplicación profesional, moderna, rápida y segura desarrollada en Python para analizar, limpiar archivos residuales, auditar el arranque de Windows, triturar archivos confidenciales, encontrar duplicados y optimizar el rendimiento del sistema operativo.

---

## 🚀 Novedades y Características Principales

### 1. Limpieza Inteligente y Segura (20 Categorías)
- **Filtro de Antigüedad por Seguridad (Retention Filter):** Protege archivos temporales modificados recientemente (< 24 horas por defecto) para no dañar instaladores en ejecución o descargas activas.
- **Protección contra Directory Junctions (Puntos de Montaje):** Previene atravesar o eliminar carpetas vinculadas que apunten a documentos personales o discos externos.
- **Detección de Procesos en Ejecución:** Avisa en tiempo real si Chrome, Edge, Firefox, Spotify o Discord están abiertos para evitar bloqueos y corrupción de datos de caché.
- **Lista Blanca de Exclusiones (Whitelist):** Permite configurar carpetas o rutas que **nunca** se eliminarán ni modificarán.
- **Temporales de Usuario y del Sistema:** Limpieza de `%TEMP%`, `C:\Windows\Temp` y `Prefetch`.
- **Papelera de Reciclaje:** Vaciado silencioso mediante la API Win32 (`SHEmptyRecycleBinW`).
- **Navegadores Web (Soporte Multi-Perfil):**
  - **Google Chrome, Microsoft Edge, Brave, Mozilla Firefox, Opera / Opera GX y Vivaldi.**
  - Escanea automáticamente todos los perfiles (`Default`, `Profile 1`, `Profile 2`, etc.).
  - *Nunca toca contraseñas, historial, marcadores ni sesiones abiertas.*
- **Herramientas de Desarrollo y Apps:**
  - Caché de **Visual Studio Code** (`Cache`, `CachedData`, extensiones VSIX temporales).
  - Paquetes descargados de **Pip (Python)**, **NPM / PNPM / Yarn (Node.js)** y **Cargo (Rust)**.
  - Caché multimedia de **Discord** y almacenamiento local de **Spotify**.
- **Windows System Extra:**
  - Caché de **Windows Update** (`SoftwareDistribution\Download`).
  - Archivos de **Optimización de Distribución** (`DeliveryOptimization`).
  - Archivos de registro y logs antiguos de Windows (`C:\Windows\Logs` y `Panther`).
  - Reportes de caídas y volcados de error (`CrashDumps` y WER).
  - Miniaturas del explorador (`thumbcache` e `iconcache`) y componentes web (`INetCache`).

---

### 2. Dashboard Gráfico Interactivo y Moderno (Animaciones GSAP + PyWebView)
- **Interfaz Moderna con GSAP (GreenSock Animation Platform):**
  - Gráficos SVG circulares animados con easing dinámico para Disco y Memoria RAM.
  - Contadores de bytes y archivos animados en tiempo real (`0 B` -> `XX.XX GB`).
  - Banner dinámico de advertencia cuando hay navegadores en ejecución.
  - Pestaña de **Herramientas Avanzadas** (Triturador de archivos y Buscador de duplicados).
  - Botón de **Exportación de Informes** de diagnóstico a formatos `.json` o `.txt`.
  - Transiciones suaves entre pestañas y animaciones de entrada fluidas.
  - Barra de progreso interactiva con efecto de resplandor.
  - Consola de logs integrada y colapsable con auto-scroll y etiquetas cromáticas.
- **Soporte Multi-Disco:** Selector dinámico de unidades (`C:\`, `D:\`, etc.) con estadísticas en gigabytes y porcentaje en tiempo real.
- **Compatibilidad Dual:** Incluye tanto la interfaz moderna con GSAP como la interfaz gráfica clásica en Tkinter (`--legacy-gui`).

---

### 3. Herramientas Avanzadas de Rendimiento y Privacidad
- **🗑️ Triturador Seguro de Archivos (File Shredder):**
  - Sobrescribe el contenido de archivos confidenciales con bytes aleatorios (`os.urandom`) y ceros antes de desenlazarlos del sistema de archivos, impidiendo su recuperación forense (soporta 1 pasada rápida o 3 pasadas estándar DoD 5220.22-M).
- **🔍 Buscador de Archivos Duplicados (Duplicate Finder):**
  - Identifica archivos duplicados agrupando por tamaño y calculando firmas criptográficas SHA-256 por bloques para liberar espacio desperdiciado.
- **🚀 Gestor de Programas de Inicio de Windows:**
  - Lee y cataloga los programas que arrancan automáticamente con el equipo desde el Registro (`HKCU` y `HKLM`).
  - Permite habilitar o deshabilitar cualquier programa de inicio de forma segura (moviéndolo a `RunDisabled` sin borrar entradas críticas).
- **⚡ Compactación de Memoria RAM:**
  - Vaciado del working set (`EmptyWorkingSet`) de los procesos del usuario para liberar RAM a Standby/Disponible.
- **🌐 Vaciado de Caché DNS:**
  - Ejecución de `ipconfig /flushdns` para resolver fallos de navegación y caché de red.

---

### 4. Estabilidad, Testing y Empaquetado
- **Cero bloqueos en desarrollo:** Compatibilidad multiplataforma y stubs para `winreg`/`ctypes` que permiten ejecutar tests y desarrollo en cualquier sistema operativo.
- **Suite de Pruebas Automatizadas:** 7 tests unitarios en `tests/` que validan seguridad, cálculo de antigüedad, triturador y duplicados.
- **Compilador a Ejecutable Portable (.exe):** Script incluido con PyInstaller (`build_exe.py` / `build.bat`) para generar un único ejecutable sin necesidad de instalar Python en el equipo de destino.

---

## 🖥️ Cómo Ejecutar

### Opción 1: Interfaz Gráfica (Recomendado)
Haz doble clic en:
- **`run.bat`**: Inicia la interfaz gráfica estándar moderna en modo oscuro.
- **`run_admin.bat`**: Inicia la interfaz con privilegios de Administrador para limpiar carpetas protegidas del sistema (`Windows\Temp`, `SoftwareDistribution`, `Logs` y `Prefetch`).

O desde la terminal:
```bash
python main.py
```

---

### Opción 2: Modo Consola (CLI / Automatización)
Ideal para scripts, tareas programadas en Windows o entornos DevOps:

```bash
# Escanear el sistema y ver espacio recuperable:
python main.py --scan

# Simular limpieza (Dry-Run):
python main.py --dry-run

# Limpiar archivos basura respetando reglas de seguridad:
python main.py --clean

# Triturar y destruir un archivo confidencial de forma irrecuperable:
python main.py --shred C:\Ruta\archivo_secreto.docx --shred-passes 3

# Buscar archivos duplicados en una carpeta:
python main.py --duplicates C:\Users\TuUsuario\Downloads

# Exportar reporte de escaneo a archivo de texto:
python main.py --scan --export C:\Users\TuUsuario\Desktop\reporte.txt

# Listar programas configurados para iniciar con Windows:
python main.py --startup

# Especificar otra unidad de disco (ej. D:\):
python main.py --scan --drive D:\

# Generar un reporte estructurado en formato JSON:
python main.py --scan --json

# Optimizar memoria RAM:
python main.py --ram

# Vaciar la caché DNS:
python main.py --dns

# Ejecutar optimización completa (RAM + DNS + Limpieza):
python main.py --all
```

---

## 📦 Compilación a .exe (Ejecutable Portable)

Para empaquetar la aplicación en un único archivo ejecutable `.exe` que no requiera Python:

1. Instala las dependencias:
   ```bash
   pip install -r requirements-dev.txt
   ```
2. Ejecuta el compilador o haz doble clic en `build.bat`:
   ```bash
   python build_exe.py
   ```
3. El ejecutable portable se generará en la carpeta `dist/PyCleanPro.exe`.

---

## 🧪 Ejecutar Tests

Para ejecutar la suite de pruebas unitarias:
```bash
pytest tests/
```

---

## 📁 Estructura del Proyecto

- [`cleaner.py`](file:///home/antigravity/chemkes1999/cleanerpc/cleaner.py): Motor central de análisis, limpieza segura, llamadas Win32 API, filtro de antigüedad, protección de junctions, triturador seguro, detector de duplicados y auditor de procesos.
- [`main.py`](file:///home/antigravity/chemkes1999/cleanerpc/main.py): Punto de entrada con soporte completo para GUI y CLI (incluyendo `--shred`, `--duplicates`, `--export`, etc.).
- [`web_gui.py`](file:///home/antigravity/chemkes1999/cleanerpc/web_gui.py): API PyWebView que conecta el frontend con el motor Python.
- [`web/`](file:///home/antigravity/chemkes1999/cleanerpc/web): Interfaz moderna (HTML, CSS y JS con animaciones fluidas GSAP).
- [`tests/`](file:///home/antigravity/chemkes1999/cleanerpc/tests): Suite de pruebas unitarias automatizadas (`test_cleaner.py`).
- [`build_exe.py`](file:///home/antigravity/chemkes1999/cleanerpc/build_exe.py) / [`build.bat`](file:///home/antigravity/chemkes1999/cleanerpc/build.bat): Compilador a binario `.exe` único vía PyInstaller.
- [`gui.py`](file:///home/antigravity/chemkes1999/cleanerpc/gui.py) / [`charts.py`](file:///home/antigravity/chemkes1999/cleanerpc/charts.py): Interfaz clásica basada en Tkinter (`--legacy-gui`).
- [`requirements.txt`](file:///home/antigravity/chemkes1999/cleanerpc/requirements.txt): Dependencias de producción.
- [`requirements-dev.txt`](file:///home/antigravity/chemkes1999/cleanerpc/requirements-dev.txt): Dependencias de desarrollo y testing.
