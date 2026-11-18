# ⚡ PyClean Pro v2.3 - Suite Integral de Optimización, Mantenimiento y Privacidad para Windows

Una aplicación profesional, moderna, rápida y segura desarrollada en Python para analizar y limpiar archivos residuales, auditar y desinstalar aplicaciones sin dejar restos huérfanos, explorar visualmente particiones y carpetas con Treemap interactivo, cazar archivos gigantes, programar mantenimientos automáticos con Windows Task Scheduler, mitigar la telemetría del sistema, triturar archivos confidenciales de forma irrecuperable y optimizar el rendimiento del sistema operativo.

---

## 🚀 Novedades y Características Principales

### 1. 🗺️ Mapa de Almacenamiento, Particiones y Treemap (Nuevo en v2.3)
- **Vista de Particiones y Unidades de Disco:**
  - Detecta todas las unidades (`C:\`, `D:\`, discos externos, USBs) mostrando nombre de volumen, sistema de archivos (`NTFS`, `FAT32`, etc.), espacio libre/total y medidor de uso visual.
- **Explorador Visual de Carpetas y Treemap:**
  - Bloques proporcionales de color estilo *WinDirStat / WizTree* que representan visualmente el peso de cada subcarpeta o archivo.
  - Navegación interactiva con migas de pan (*breadcrumbs*) y botón "Subir Nivel".
  - Clasificación de almacenamiento por tipos de archivos: **Videos**, **Comprimidos e ISOs**, **Ejecutables**, **Documentos** e **Imágenes**.
- **🐘 Cazador de Archivos Gigantes:**
  - Localiza al instante los archivos más pesados del disco (> 100 MB, > 500 MB, > 1 GB o > 2 GB) con filtros rápidos.
  - Acciones directas: **Abrir en Explorador de Windows**, **Triturar de forma segura** o **Eliminar**.

---

### 2. 📦 Instalador Oficial para Windows (Nuevo en v2.3)
- **Instalador Completo (`PyCleanPro-Setup.exe`):**
  - Script oficial Inno Setup 6 ([`installer.iss`](file:///installer.iss)) para generar un instalador con asistente moderno en español e inglés.
  - Crea accesos directos en el **Menú Inicio** y opcionalmente en el **Escritorio**.
  - Registra el programa limpiamente en la configuración de Windows y Panel de Control ("Agregar o quitar programas").
  - Compilación automática con [`build_installer.py`](file:///build_installer.py) o mediante el menú de [`build.bat`](file:///build.bat).
  - Integrado en el flujo de CI/CD de GitHub Actions para publicar tanto el ejecutable portable como el instalador Setup en cada release.

---

### 3. Limpieza Inteligente y Segura (20 Categorías)
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

### 4. Desinstalador Limpio y Mantenimiento Avanzado
- **📦 Desinstalador Limpio de Aplicaciones con Escáner de Residuos:**
  - Cataloga todas las aplicaciones instaladas en Windows desde el Registro (`HKLM`, `HKCU` y `Wow6432Node`).
  - Permite buscar en tiempo real, visualizar tamaño estimado y ejecutar desinstalaciones nativas.
  - **Detección de Residuos Huérfanos:** Tras desinstalar, rastrea carpetas huérfanas en `%APPDATA%`, `%LOCALAPPDATA%` y `%PROGRAMDATA%` para eliminarlas de forma definitiva.
- **⏰ Programador de Mantenimiento Automático (Task Scheduler):**
  - Configura una tarea programada nativa en Windows (`schtasks`) para ejecutar la optimización silenciosa periódica (semanal o diaria) sin intervención del usuario.
- **🛡️ Optimizador de Telemetría y Privacidad:**
  - Audita y permite pausar o desactivar servicios de recolección diagnóstica (`DiagTrack`, `dmwappushservice`, `WerSvc`) y configurar la directiva `DataCollection` en el Registro.
- **📂 Auditor de Descargas Pesadas y Antiguas:**
  - Identifica instaladores (`.iso`, `.exe`, `.msi`, `.zip`) en la carpeta `Descargas` con más de 30, 60 o 90 días sin abrir para recuperar gigabytes rápidamente.

---

### 5. Dashboard Gráfico Interactivo y Moderno (Animaciones GSAP + PyWebView)
- **Interfaz Moderna con GSAP (GreenSock Animation Platform):**
  - Gráficos SVG circulares animados con easing dinámico para Disco y Memoria RAM.
  - Contadores de bytes y archivos animados en tiempo real (`0 B` -> `XX.XX GB`).
  - Banner dinámico de advertencia cuando hay navegadores en ejecución.
  - Pestañas de **Mapa de Disco**, **Desinstalador**, **Privacidad**, **Herramientas Avanzadas** (Triturador y Duplicados) y **Ajustes**.
  - Botón de **Exportación de Informes** de diagnóstico a formatos `.json` o `.txt`.
  - Consola de logs integrada y colapsable con auto-scroll y etiquetas cromáticas.
- **Soporte Multi-Disco:** Selector dinámico de unidades (`C:\`, `D:\`, etc.) con estadísticas en gigabytes y porcentaje en tiempo real.
- **Compatibilidad Dual:** Incluye tanto la interfaz moderna con GSAP como la interfaz gráfica clásica en Tkinter (`--legacy-gui`).

---

### 6. Herramientas Avanzadas de Rendimiento y Seguridad
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

### 7. Estabilidad, Testing y CI/CD Automático
- **Cero bloqueos en desarrollo:** Compatibilidad multiplataforma y stubs para `winreg`/`ctypes` que permiten ejecutar tests y desarrollo en cualquier sistema operativo.
- **Suite de Pruebas Automatizadas:** 13 tests unitarios en `tests/` que validan seguridad, cálculo de antigüedad, triturador, duplicados, auditoría de descargas, mapa de disco, treemap y fallbacks.
- **Compilador a Ejecutable Portable e Instalador Setup:** Scripts incluidos con PyInstaller e Inno Setup (`build_exe.py`, `build_installer.py`, `build.bat`) para compilar binarios sin necesidad de Python instalado.
- **GitHub Actions CI/CD ([`.github/workflows/build-release.yml`](file:///.github/workflows/build-release.yml)):** Flujo automático en `windows-latest` que compila tanto `PyCleanPro.exe` como `PyCleanPro-Setup.exe` y los adjunta como assets descargables en los Releases de GitHub al crear tags `v*`.

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

# Listar aplicaciones instaladas en el sistema:
python main.py --apps

# Auditar instaladores antiguos en Descargas (> 30 días):
python main.py --downloads-audit 30

# Activar tarea semanal de mantenimiento automático:
python main.py --schedule on

# Mitigar servicios de telemetría y diagnósticos de Windows:
python main.py --privacy on

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
pytest tests/ -v
```

---

## 📁 Estructura del Proyecto

- [`cleaner.py`](file:///home/antigravity/chemkes1999/cleanerpc/cleaner.py): Motor central de análisis, limpieza segura, llamadas Win32 API, filtro de antigüedad, protección de junctions, triturador seguro, detector de duplicados, desinstalador, auditor de descargas y telemetría.
- [`main.py`](file:///home/antigravity/chemkes1999/cleanerpc/main.py): Punto de entrada con soporte completo para GUI y CLI (incluyendo `--apps`, `--downloads-audit`, `--schedule`, `--privacy`, `--shred`, etc.).
- [`web_gui.py`](file:///home/antigravity/chemkes1999/cleanerpc/web_gui.py): API PyWebView que conecta el frontend con el motor Python.
- [`web/`](file:///home/antigravity/chemkes1999/cleanerpc/web): Interfaz moderna (HTML, CSS y JS con animaciones fluidas GSAP).
- [`tests/`](file:///home/antigravity/chemkes1999/cleanerpc/tests): Suite de 10 pruebas unitarias automatizadas (`test_cleaner.py`).
- [`.github/workflows/build-release.yml`](file:///home/antigravity/chemkes1999/cleanerpc/.github/workflows/build-release.yml): Pipeline de CI/CD para compilación de `.exe` y releases en GitHub.
- [`build_exe.py`](file:///home/antigravity/chemkes1999/cleanerpc/build_exe.py) / [`build.bat`](file:///home/antigravity/chemkes1999/cleanerpc/build.bat): Compilador a binario `.exe` único vía PyInstaller.
- [`gui.py`](file:///home/antigravity/chemkes1999/cleanerpc/gui.py) / [`charts.py`](file:///home/antigravity/chemkes1999/cleanerpc/charts.py): Interfaz clásica basada en Tkinter (`--legacy-gui`).
- [`requirements.txt`](file:///home/antigravity/chemkes1999/cleanerpc/requirements.txt): Dependencias de producción.
- [`requirements-dev.txt`](file:///home/antigravity/chemkes1999/cleanerpc/requirements-dev.txt): Dependencias de desarrollo y testing.
