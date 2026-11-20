# ⚡ PyClean Pro v2.7.0

**Suite integral de escritorio para limpieza segura, análisis visual de disco, monitoreo de procesos y red, diagnóstico de hardware, privacidad y bóveda local de contraseñas cifrada (Windows y macOS).**

Construida en **Python 3.10+** con una interfaz moderna 100% offline impulsada por **PyWebView + HTML/CSS/JS + GSAP 3.12.5**, respaldo automático en **Tkinter** (`--legacy-gui`) y una **CLI completa con 24 banderas** para automatización.

---

## 📚 Índice de Documentación

| Documento | Descripción |
|---|---|
| **[Guía de Usuario](docs/GUIA_USUARIO.md)** | Recorrido por las 13 vistas (4 grupos), temas Oscuro/OLED/Claro, categorías de limpieza (20 Windows / 9 macOS) e interfaz clásica `--legacy-gui`. |
| **[Referencia CLI](docs/CLI.md)** | Referencia exhaustiva de las 24 banderas de `main.py`, compatibilidad con `--json`/`--export` y recetas de automatización. |
| **[Seguridad y Bóveda](docs/SEGURIDAD_Y_BOVEDA.md)** | Especificación criptográfica de `vault.py` (AES-256-GCM + PBKDF2-HMAC-SHA256 600k), salvaguardas de limpieza y modelo de amenazas. |
| **[Arquitectura y Puente API](docs/ARQUITECTURA.md)** | Diagrama Mermaid de capas, 5 motores backend, frontend offline, referencia de los 56 métodos de `PyCleanAPI`, rutas por SO y suite de 21 tests. |
| **[Compilación y Releases](docs/COMPILACION_Y_RELEASE.md)** | Compilación local Windows (`.exe`/Setup) y macOS (`.app`/`.dmg`), pipeline GitHub Actions, firma Authenticode y verificación `SHA256SUMS.txt`. |
| **[Historial de Cambios](CHANGELOG.md)** | Registro cronológico de versiones desde `v2.0.0` hasta `v2.6.0`. |

---

## 🖥️ Matriz de Compatibilidad por Plataforma

| Módulo / Funcionalidad | Windows 10/11 | macOS | Linux (desde fuente) |
|---|:---:|:---:|:---:|
| **Instalador / Binario oficial en Releases** | ✅ `.exe` portable y `Setup.exe` | ✅ `.dmg` (`PyCleanPro.app`) | ⚙️ Solo código fuente |
| **Limpieza inteligente por categorías** | ✅ 20 categorías (15 usuario / 5 Admin) | ✅ 9 categorías nativas | ⚠️ Parcial (solo rutas comunes) |
| **Mapa de Disco, Treemap y Archivos Gigantes** | ✅ Completo | ✅ Completo | ✅ Completo |
| **Monitor de Procesos, Interfaces IPv4 y Ping** | ✅ Completo | ✅ Completo | ✅ Completo |
| **Selector rápido de DNS y Vaciar DNS** | ✅ (`netsh` / `ipconfig`, Admin) | ❌ Solo Windows | ❌ Solo Windows |
| **Salud de Hardware (S.M.A.R.T., TRIM, Batería)** | ✅ Completo (TRIM requiere Admin) | ⚠️ Solo carga básica de batería | ⚠️ Solo carga básica de batería |
| **Bóveda Local de Contraseñas (AES-256-GCM)** | ✅ Completo (`clip` 30 s) | ✅ Completo (`pbcopy` 30 s) | ⚠️ Sin auto-copiado al portapapeles |
| **Triturador Seguro, Duplicados SHA-256 y Descargas** | ✅ Completo | ✅ Completo | ✅ Completo |
| **Desinstalador + Residuos, Inicio Rápido y Telemetría** | ✅ Completo (Admin para HKLM/servicios) | ❌ Solo Windows | ❌ Solo Windows |
| **Gestor del Menú Contextual (Clic Derecho)** | ✅ Reversible (`LegacyDisable`) | ❌ Solo Windows | ❌ Solo Windows |
| **Programador de Tareas (`PyCleanPro_AutoClean`)** | ✅ (`schtasks`, Admin) | ❌ Solo Windows | ❌ Solo Windows |

---

## ✨ Resumen de Módulos (Interfaz v2.6.0)

La interfaz moderna organiza sus **13 vistas** en **4 grupos** de la barra lateral, con selector de tema (**Oscuro / OLED / Claro**), barra superior de acciones rápidas y consola de registro en vivo colapsable:

### 1. General
- **Dashboard:** Medidores circulares SVG animados (GSAP) de disco y RAM, contador animado de espacio recuperable y desglose por categoría.
- **Limpieza:** 20 categorías en Windows y 9 nativas en macOS con filtro de retención de 24 horas, protección contra enlaces simbólicos/*junctions*, lista blanca de exclusiones y aviso contextual de navegadores abiertos.
- **Archivos Top:** Listado de los 100 archivos basura más pesados detectados en el último escaneo con acceso directo al explorador de archivos.

### 2. Sistema y Hardware
- **Mapa de Disco:** Tarjetas de particiones con sistema de archivos y uso, **Treemap visual interactivo** con clasificación por tipo de archivo y **Cazador de Archivos Gigantes** (>100 MB a >2 GB).
- **Monitor y Red (`sys_monitor.py`):** Top 35 procesos por RAM/CPU con protección de 18 procesos críticos del sistema, adaptadores IPv4, presets DNS en 1 clic (Cloudflare, Google, AdGuard, DHCP) y test de latencia Ping.
- **Salud Hardware (`hardware_health.py`):** Diagnóstico S.M.A.R.T. de discos físicos, optimización **SSD TRIM** (`Optimize-Volume -ReTrim`) y salud/desgaste/ciclos de batería.
- **Inicio Rápido:** Activación y desactivación reversible de programas de inicio de Windows (`Run` ↔ `RunDisabled`).

### 3. Seguridad y Privacidad
- **Bóveda (`vault.py`):** Gestor local de contraseñas *Zero-Knowledge* 100% offline con **PBKDF2-HMAC-SHA256** (600,000 iteraciones) + **AES-256-GCM**, generador CSPRNG, medidor de entropía, auto-bloqueo tras 5 minutos, limpieza del portapapeles a los 30 segundos y respaldos cifrados `.vault`.
- **Privacidad:** Auditoría y mitigación reversible de servicios de telemetría de Windows (`DiagTrack`, `dmwappushservice`, `WerSvc`) y directiva `AllowTelemetry`.
- **Herramientas:** Triturador seguro de archivos (1 o 3 pasadas), buscador de duplicados por hash SHA-256 y auditor de descargas antiguas (>30/60/90 días).

### 4. Gestión
- **Desinstalador:** Catálogo de aplicaciones instaladas desde el Registro de Windows con detección y limpieza opcional de carpetas residuales huérfanas.
- **Menú Contextual (`context_menu.py`):** Auditoría y ocultación/reactivación 100% reversible de entradas de terceros en el menú clic derecho del Explorador de Windows (`LegacyDisable`). *(No instala accesos de PyClean en el menú contextual).*
- **Ajustes:** Configuración de antigüedad mínima de archivos, exclusiones y Programador de Tareas de Windows (`PyCleanPro_AutoClean`).

---

## 📦 Instalación Rápida

### Opción A: Descargar Binarios Oficiales (Recomendado)

Descarga los instaladores precompilados desde la sección **[GitHub Releases](https://github.com/chemkes1999/cleanerpc/releases)**:

- **Windows (Instalador):** `PyCleanPro-Setup.exe` — Asistente Inno Setup 6 en español e inglés con accesos directos y registro en Panel de Control.
- **Windows (Portable):** `PyCleanPro.exe` — Ejecutable independiente sin instalación.
- **macOS:** `PyCleanPro-macOS.dmg` — Abre el `.dmg` y arrastra `PyCleanPro.app` a la carpeta **Aplicaciones**.
  > **Nota sobre macOS Gatekeeper:** Si la aplicación no cuenta con notarización de Apple, al abrirla por primera vez haz **clic derecho → Abrir** y confirma **Abrir**.
  > **Nota sobre Windows SmartScreen:** Si el binario no está firmado con certificado Authenticode, haz clic en **Más información → Ejecutar de todas formas**.

#### Verificar integridad con `SHA256SUMS.txt`

```powershell
# Windows (PowerShell)
Get-FileHash .\PyCleanPro-Setup.exe -Algorithm SHA256
```

```bash
# macOS / Linux
shasum -a 256 PyCleanPro-macOS.dmg
```

Compara el hash obtenido con el publicado en el archivo `SHA256SUMS.txt` del mismo release.

---

### Opción B: Ejecutar desde Código Fuente

Requiere **Python 3.10 o superior** (se recomienda **Python 3.11**).

```bash
git clone https://github.com/chemkes1999/cleanerpc.git
cd cleanerpc
pip install -r requirements.txt
```

Para desarrollo, pruebas y compilación local:

```bash
pip install -r requirements-dev.txt
```

---

## 🚀 Inicio Rápido (GUI y CLI)

### Interfaz Gráfica

```bash
# Abrir interfaz moderna (PyWebView + GSAP, con respaldo automático a Tkinter)
python main.py

# En macOS / Linux
python3 main.py

# Forzar interfaz clásica en Tkinter (subconjunto de funciones v2.0)
python main.py --legacy-gui
```

En Windows también puedes usar los lanzadores incluidos: [`run.bat`](run.bat) (usuario estándar) o [`run_admin.bat`](run_admin.bat) (con elevación UAC para limpiar caché de Windows Update, Prefetch, TRIM o telemetría).

### Línea de Comandos (Ejemplos Frecuentes)

```bash
# Escanear espacio recuperable sin borrar archivos
python main.py --scan

# Simular limpieza en una unidad específica
python main.py --dry-run --drive D:\

# Optimizar RAM, vaciar DNS y limpiar todas las categorías
python main.py --all

# Diagnóstico de hardware (S.M.A.R.T. y batería) en formato JSON
python main.py --hardware --json

# Exportar reporte de escaneo a JSON o texto plano
python main.py --scan --export reporte.json

# Buscar duplicados por contenido SHA-256
python main.py --duplicates "C:\Users\Usuario\Documentos"
```

Consulta las **24 banderas disponibles** y sus reglas de combinación en la **[Referencia CLI completa](docs/CLI.md)**.

---

## 🧪 Pruebas Unitarias

El proyecto incluye una suite de **21 pruebas unitarias** distribuidas en 2 archivos:
- [`tests/test_cleaner.py`](tests/test_cleaner.py) — **13 pruebas** (limpieza, filtro de retención, triturador, duplicados, reportes, descargas, residuos, particiones, treemap, archivos gigantes y salvaguardas).
- [`tests/test_v24_modules.py`](tests/test_v24_modules.py) — **8 pruebas** (procesos críticos, validación DNS, XML de batería, validación TRIM, menú contextual, ciclo de vida de la bóveda, fortaleza de contraseñas y categorías macOS).

```bash
pytest tests/ -v
```

---

## 📁 Estructura del Proyecto

```text
cleanerpc/
├── main.py                              # Punto de entrada unificado (GUI moderna, --legacy-gui y CLI con 24 banderas)
├── web_gui.py                           # Host PyWebView y puente API JS↔Python (PyCleanAPI: 56 métodos públicos)
├── gui.py                               # Interfaz clásica de respaldo en Tkinter (4 pestañas)
├── charts.py                            # Gráficos Canvas para la interfaz Tkinter (DonutChart, HorizontalBarBreakdown)
├── cleaner.py                           # Motor principal de limpieza (20 Windows / 9 macOS), disco, apps y herramientas
├── sys_monitor.py                       # Monitor de procesos (18 críticos protegidos), red IPv4, DNS y Ping
├── hardware_health.py                   # Diagnóstico S.M.A.R.T., SSD TRIM y salud/desgaste de batería
├── context_menu.py                      # Auditor y gestor reversible del menú contextual de Windows (LegacyDisable)
├── vault.py                             # Bóveda local cifrada Zero-Knowledge (AES-256-GCM + PBKDF2-HMAC-SHA256 600k)
├── web/                                 # Frontend SPA 100% offline (cero CDNs)
│   ├── index.html                       # Estructura de 13 vistas, barra lateral agrupada, consola y modales
│   ├── style.css                        # Estilos y 3 temas visuales (Oscuro, OLED, Claro)
│   ├── app.js                           # Controlador principal, animaciones GSAP y modo mock de navegador
│   ├── modules_v24.js                   # Controladores UI para Monitor/Red, Hardware, Menú Contextual y Bóveda
│   ├── ui_kit.js                        # Gestor de temas, notificaciones Toast y modal de confirmación
│   └── gsap.min.js                      # Librería GSAP 3.12.5 empaquetada localmente
├── tests/                               # Suite de 21 pruebas unitarias (pytest)
│   ├── test_cleaner.py                  # 13 pruebas del motor principal y análisis de disco
│   └── test_v24_modules.py              # 8 pruebas de módulos v2.4–v2.5 y bóveda
├── assets/                              # Íconos multiplataforma (.ico, .icns, .png)
├── docs/                                # Documentación técnica y guías de usuario en español
│   ├── GUIA_USUARIO.md                  # Guía completa de la interfaz y módulos
│   ├── CLI.md                           # Referencia de las 24 banderas de línea de comandos
│   ├── SEGURIDAD_Y_BOVEDA.md            # Criptografía de la bóveda, salvaguardas y modelo de amenazas
│   ├── ARQUITECTURA.md                  # Arquitectura, puente PyCleanAPI (56 métodos) y rutas por SO
│   └── COMPILACION_Y_RELEASE.md         # Empaquetado Windows/macOS, GitHub Actions y verificación SHA-256
├── .github/workflows/build-release.yml  # Pipeline CI/CD multi-OS (Windows, macOS y GitHub Release)
├── build_exe.py                         # Compilación ejecutable portable Windows (PyInstaller)
├── build_installer.py                   # Compilación instalador Windows (Inno Setup 6)
├── build_macos.py                       # Compilación bundle .app e imagen .dmg en macOS
├── installer.iss                        # Script Inno Setup 6 para PyCleanPro-Setup.exe
├── version_info.txt                     # Metadatos PE de versión para Windows (2.6.0.0)
├── build.bat / run.bat / run_admin.bat  # Scripts auxiliares de compilación y lanzamiento en Windows
├── requirements.txt                     # Dependencias de ejecución (pywebview, psutil, cryptography)
├── requirements-dev.txt                 # Dependencias de desarrollo y empaquetado (pytest, pyinstaller)
├── CHANGELOG.md                         # Historial de versiones (v2.0.0 – v2.6.0)
└── README.md                            # Documentación principal del proyecto
```

---

## 📄 Licencia

Actualmente este repositorio **no incluye un archivo `LICENSE` publicado**. Antes de redistribuir o incorporar el código en proyectos de terceros, consulta con el autor del repositorio (`chemkes1999`) para confirmar los términos de licencia aplicables.
