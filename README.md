# ⚡ PyClean Pro - Optimizador y Limpiador de PC para Windows

Una aplicación moderna, rápida y segura desarrollada en Python para analizar, limpiar archivos basura y optimizar el rendimiento de tu PC con Windows.

---

## 🚀 Características Principales

1. **Limpieza Inteligente de Archivos Basura:**
   - **Temporales de Usuario (`%TEMP%`):** Restos de instaladores y aplicaciones cerradas.
   - **Temporales del Sistema (`C:\Windows\Temp`):** Archivos temporales de servicios y procesos del sistema operativo.
   - **Papelera de Reciclaje:** Vaciado directo y seguro mediante la API Win32 de Windows (`SHEmptyRecycleBinW`).
   - **Caché de Navegadores Web:** Limpieza de datos temporales y caché de imágenes en **Google Chrome, Microsoft Edge, Brave y Mozilla Firefox** *(nunca borra contraseñas, historial ni sesiones activas)*.
   - **Reportes de Bloqueo y WER (`CrashDumps`):** Archivos de volcado generados tras caídas de programas.
   - **Caché de Miniaturas (`thumbcache`):** Restos de miniaturas obsoletas del Explorador de Windows.
   - **Caché de Windows Update (`SoftwareDistribution\Download`):** Instaladores descargados de actualizaciones ya instaladas.
   - **Archivos Prefetch:** Registros antiguos de precarga de Windows.

2. **Gráficas Visuales Interactivas (Canvas Nativo):**
   - **Gráfico Donut de Disco (C:):** Muestra el anillo circular de espacio ocupado vs libre con porcentaje y gigabytes restantes en tiempo real.
   - **Gráfico Donut de Memoria RAM:** Visualización del consumo de RAM activo frente a la memoria disponible.
   - **Gráfico de Barras de Distribución de Basura:** Barras horizontales por categoría (Temporales de usuario, Chrome, Edge, Brave, Windows Update, Papelera, etc.) con colores temáticos y proporción de espacio ocupado.

3. **Optimización del Sistema:**
   - **Liberación de Memoria RAM:** Compacta las páginas y working sets de los procesos activos liberando memoria inmediata.
   - **Vaciado de Caché DNS (`ipconfig /flushdns`):** Agiliza la navegación y resuelve problemas de resolución de red.
   - **Monitor en Tiempo Real:** Visualización gráfica del estado general del equipo.

4. **Seguridad y Confianza:**
   - **Modo Escaneo (Scan Only):** Permite ver cuánto espacio exacto se puede liberar antes de borrar cualquier archivo.
   - **Protección contra Bloqueos:** Omite silenciosamente archivos que estén en uso en ese momento por programas abiertos, sin colgarse ni mostrar errores críticos.
   - **Cero dependencias externas obligatorias:** Funciona nativamente con las librerías estándar de Python (`tkinter`, `ctypes`, `shutil`, `threading`).

---

## 🖥️ Cómo Ejecutar

### Opción 1: Interfaz Gráfica (Recomendado)
Haz doble clic en:
- **`run.bat`**: Inicia la interfaz gráfica estándar en modo oscuro.
- **`run_admin.bat`**: Inicia la interfaz con permisos de Administrador para poder limpiar carpetas del sistema (`Windows\Temp`, `SoftwareDistribution` y Prefetch).

O desde la terminal:
```bash
python main.py
```

---

### Opción 2: Modo Consola (CLI / Automatización)
Puedes ejecutar tareas directamente desde la terminal o programarlas en el Programador de Tareas de Windows:

```bash
# Escanear el sistema y ver cuánto espacio hay para liberar:
python main.py --scan

# Limpiar directamente los archivos basura:
python main.py --clean

# Optimizar y liberar memoria RAM:
python main.py --ram

# Vaciar la caché DNS:
python main.py --dns

# Ejecutar optimización completa (RAM + DNS + Limpieza):
python main.py --all
```

---

## 📁 Estructura del Proyecto

- [`cleaner.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/cleaner.py): Motor central de análisis, limpieza y llamadas al API de Windows.
- [`charts.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/charts.py): Módulo de gráficas interactivas nativas (anillos Donut y barras proporcionales).
- [`gui.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/gui.py): Interfaz gráfica en modo oscuro con Tkinter/TTK y soporte de pestañas.
- [`main.py`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/main.py): Punto de entrada (soporte para GUI y CLI).
- [`run.bat`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/run.bat): Lanzador rápido de doble clic.
- [`run_admin.bat`](file:///c:/Users/hmcar/Documents/controlAuto/cleanerpc/run_admin.bat): Lanzador con elevación UAC de Administrador.
