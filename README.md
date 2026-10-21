# ⚡ PyClean Pro v2.0 - Suite de Optimización y Limpieza de PC para Windows

Una aplicación moderna, rápida y segura desarrollada en Python para analizar, limpiar archivos residuales, auditar el arranque de Windows y optimizar el rendimiento del sistema operativo.

---

## 🚀 Novedades y Características Principales

### 1. Limpieza Inteligente y Segura (18 Categorías)
- **Filtro de Antigüedad por Seguridad (Retention Filter):** Protege archivos temporales modificados recientemente (< 24 horas por defecto) para no dañar instaladores en ejecución o descargas activas.
- **Lista Blanca de Exclusiones (Whitelist):** Permite configurar carpetas o rutas que **nunca** se eliminarán ni modificarán.
- **Temporales de Usuario y del Sistema:** Limpieza de `%TEMP%`, `C:\Windows\Temp` y `Prefetch`.
- **Papelera de Reciclaje:** Vaciado silencioso mediante la API Win32 (`SHEmptyRecycleBinW`).
- **Navegadores Web (Soporte Multi-Perfil):**
  - **Google Chrome, Microsoft Edge, Brave, Mozilla Firefox, Opera / Opera GX y Vivaldi.**
  - Escanea automáticamente todos los perfiles (`Default`, `Profile 1`, `Profile 2`, etc.).
  - *Nunca toca contraseñas, historial, marcadores ni sesiones abiertas.*
- **Herramientas de Desarrollo y Apps:**
  - Caché de **Visual Studio Code** (`Cache`, `CachedData`, extensiones VSIX temporales).
  - Caché multimedia de **Discord** y almacenamiento temporal de **Spotify**.
- **Windows System Extra:**
  - Caché de **Windows Update** (`SoftwareDistribution\Download`).
  - Archivos de **Optimización de Distribución** (`DeliveryOptimization`).
  - Archivos de registro y logs antiguos de Windows (`C:\Windows\Logs` y `Panther`).
  - Reportes de caídas y volcados de error (`CrashDumps` y WER).
  - Miniaturas del explorador (`thumbcache` e `iconcache`).

---

### 2. Dashboard Gráfico Interactivo y Moderno (Animaciones GSAP + PyWebView)
- **Interfaz Moderna con GSAP (GreenSock Animation Platform):**
  - Gráficos SVG circulares animados con easing dinámico para Disco y Memoria RAM.
  - Contadores de bytes y archivos animados en tiempo real (`0 B` -> `XX.XX GB`).
  - Transiciones suaves entre pestañas y animaciones de entrada fluidas.
  - Barra de progreso interactiva con efecto de resplandor.
  - Consola de logs integrada y colapsable con auto-scroll y etiquetas de colores.
- **Soporte Multi-Disco:** Selector dinámico de unidades (`C:\`, `D:\`, etc.) con estadísticas en gigabytes y porcentaje en tiempo real.
- **Compatibilidad Dual:** Incluye tanto la interfaz moderna con GSAP como la interfaz gráfica clásica en Tkinter (`--legacy-gui`).

---

### 3. Herramientas Avanzadas de Rendimiento
- **🚀 Gestor de Programas de Inicio de Windows:**
  - Lee y cataloga los programas que arrancan automáticamente con el equipo desde el Registro (`HKCU` y `HKLM`).
  - Permite habilitar o deshabilitar cualquier programa de inicio de forma segura (moviéndolo a `RunDisabled` sin borrar entradas críticas).
- **📂 Visor de Archivos Grandes (Top 100):**
  - Botón para inspeccionar los archivos más pesados detectados antes de limpiar, con acceso directo a *"Abrir en Explorador de Windows"*.
- **⚡ Compactación de Memoria RAM:**
  - Vaciado del working set (`EmptyWorkingSet`) de los procesos del usuario para liberar RAM a Standby/Disponible.
- **🌐 Vaciado de Caché DNS:**
  - Ejecución de `ipconfig /flushdns` para resolver fallos de navegación y caché de red.

---

### 4. Estabilidad y Thread-Safety
- **Thread-Safe UI:** Todas las operaciones asíncronas se ejecutan en subprocesos independientes y se despachan de forma segura al hilo principal de Tkinter vía `after(0, ...)`.
- **Cero dependencias externas:** Funciona nativamente con las librerías estándar de Python (`tkinter`, `ctypes`, `shutil`, `winreg`, `threading`).

---

## 🖥️ Cómo Ejecutar

### Opción 1: Interfaz Gráfica (Recomendado)
Haz doble clic en:
- **`run.bat`**: Inicia la interfaz gráfica estándar en modo oscuro.
- **`run_admin.bat`**: Inicia la interfaz con privilegios de Administrador para limpiar carpetas protegidas del sistema (`Windows\Temp`, `SoftwareDistribution`, `Logs` y `Prefetch`).

O desde la terminal:
```bash
python main.py
```

---

### Opción 2: Modo Consola (CLI / Automatización)
Ideal para scripts, tareas programadas en Windows o DevOps:

```bash
# Escanear el sistema y ver espacio recuperable:
python main.py --scan

# Simular limpieza (Dry-Run):
python main.py --dry-run

# Limpiar archivos basura respetando reglas de seguridad:
python main.py --clean

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

## 📁 Estructura del Proyecto

- [`cleaner.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/cleaner.py): Motor central de análisis, limpieza segura, llamadas Win32 API, filtro de antigüedad, configuración y gestión del registro de Windows (`winreg`).
- [`charts.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/charts.py): Módulo de gráficos interactivos Canvas (anillos Donut, barras con scroll y paleta cromática completa).
- [`gui.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/gui.py): Interfaz gráfica moderna en modo oscuro, con 4 pestañas (Dashboard, Limpieza, Inicio de Windows, Configuración) y visor modal de archivos pesados.
- [`main.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/main.py): Punto de entrada con soporte completo para GUI y CLI (incluyendo salida `--json`).
- [`cleaner_config.json`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/cleaner_config.json): Archivo de configuración local persistente (horas de retención y rutas excluidas).
- [`run.bat`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/run.bat): Lanzador rápido estándar.
- [`run_admin.bat`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/run_admin.bat): Lanzador con elevación UAC de Administrador.
