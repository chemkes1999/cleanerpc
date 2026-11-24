# Historial de Cambios (Changelog)

Todos los cambios notables en **PyClean Pro** se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto utiliza [Versionado Semántico](https://semver.org/lang/es/).

## [2.8.0] - 2026-11-24

### Añadido
- **Motor de Limpieza Profunda (`cleaner.py`):**
  - **4 Nuevas Categorías de Limpieza en Windows (24 categorías en total):**
    - `gpu_driver_caches`: Carpetas de instaladores residuales de NVIDIA (`Downloader`, `C:\NVIDIA`) y AMD (`C:\AMD`), junto con cachés de sombreadores GPU (`DXCache`, `GLCache`).
    - `directx_shaders`: Caché compilada de sombreadores gráficos DirectX y Direct3D (`D3DSCache`).
    - `game_caches`: Descargas incompletas y datos temporales de Steam (`htmlcache`, `steamapps\downloading`), Epic Games Launcher (`webcache`, `Logs`) y Battle.net.
    - `windows_recent_history`: Historial de accesos recientes y listas de salto del explorador (`Recent`, `AutomaticDestinations`, `CustomDestinations`).
  - **5 Operaciones Especializadas de Mantenimiento y Limpieza Avanzada:**
    - `run_dism_component_cleanup`: Limpieza profunda del almacén WinSxS con DISM (`/StartComponentCleanup` y `/ResetBase` opcional).
    - `clean_vss_old_shadows`: Purga de instantáneas de sombra VSS antiguas conservando el punto de restauración más reciente.
    - `clean_docker_system`: Poda y saneamiento multiplataforma de imágenes *dangling*, contenedores inactivos y caché de compilación de Docker (`docker system prune -f`).
    - `find_stale_node_modules` y `delete_selected_node_modules`: Cazador y depurador seguro de carpetas `node_modules` en proyectos inactivos (>90 días) con validaciones estrictas contra symlinks y rutas críticas.
- **Nuevo Módulo de Rendimiento y Tuning del Sistema (`sys_optimizer.py`):**
  - `unlock_ultimate_performance_plan`: Desbloqueo y activación del plan oculto de energía *Ultimate Performance* (`e9a42b02-d5df-448d-aa00-03f14749eb61`).
  - `tune_tcp_network`: Optimización de latencia y nivel de autotuning de la pila TCP de Windows mediante `netsh`.
  - `reindex_windows_search`: Reparación y regeneración limpia del índice corrupto o inflado de Windows Search (`Windows.edb`).
  - `get_compact_os_status` y `toggle_compact_os`: Consulta y conmutación de compresión transparente del sistema con CompactOS (`compact.exe /compactos`).
- **Expansión de la API Web (`web_gui.py`):**
  - 10 nuevos métodos integrados en la clase `PyCleanAPI` expuestos al frontend webview con validación de excepciones.
- **Suite de Pruebas Automatizadas:**
  - 41 nuevas pruebas unitarias y de integración en `tests/test_deep_cleaner.py`, `tests/test_sys_optimizer.py`, `tests/test_web_gui_optimization.py` y `tests/conftest.py`. Totalizando 151 pruebas pasando al 100%.

### Cambiado
- Actualizados metadatos de versión a `2.8.0` en `installer.iss`, `version_info.txt` y `README.md`.

---

## [2.7.1] - 2026-11-20

### Añadido
- **Compatibilidad con Cámara en Redes Locales Móviles (HTTP):**
  - Botón de respaldo de un toque para captura de fotos con la app de cámara nativa del smartphone (`capture="environment"`), superando las restricciones de video WebRTC en navegadores móviles sin HTTPS.
  - Notificación informativa contextual en la vista de escaneo móvil si el navegador no expone `getUserMedia`.
- **Resiliencia en CI/CD:**
  - Desacoplada la prueba de ciclo de vida de tokens de sincronización de retrasos de red/sockets en runners de CI.
  - Flujo de publicación multiplataforma tolerante a fallos para asegurar la publicación de los instaladores de Windows.

### Cambiado
- Actualizados metadatos de versión a `2.7.1` en `installer.iss` y `version_info.txt`.

---

## [2.7.0] - 2026-11-20

### Añadido
- **Bóveda con QR individual para celular:**
  - Botón "📱 QR" en cada fila de credencial para proyectar en pantalla un código QR generado localmente en `<canvas>` (sin conexión externa ni CDNs).
  - Soporte de doble modalidad: texto directo o protegido con PIN efímero de 6 dígitos cifrado mediante AES-256-GCM.
  - Temporizador de seguridad con cuenta regresiva de 60 segundos y autodestrucción/cierre para prevenir *shoulder surfing*.
- **Sincronización Total LAN (Wi-Fi Local):**
  - Servidor local efímero y seguro multihilo (`VaultSyncServer` en `web_gui.py`) con detección automática de IP y tokens de emparejamiento con tiempo de vida limitado.
  - Asistente modal en el encabezado de la bóveda ("📱 Sincronizar Móvil") con código QR de emparejamiento y monitoreo en vivo de la conexión.
  - Algoritmo de fusión bidireccional inteligente de credenciales (*Smart Merge*) que resuelve conflictos mediante marcas de tiempo (`updated_at`) sin pérdida de datos.
- **Aplicación Móvil Compañera (PWA & Offline Bundle):**
  - Progressive Web App responsive táctil en `web/mobile/` y versión autocontenida de archivo único en `vault_mobile.html`.
  - Escáner de cámara integrado en vivo (`scanner.js`, `jsqr.min.js`) para apuntar directamente a la pantalla de la PC.
  - Motor criptográfico WebCrypto API (`crypto.js`) con compatibilidad bit a bit exacta con Python `vault.py` (PBKDF2-HMAC-SHA256 con 600.000 iteraciones y AES-256-GCM).
  - Almacén local cifrado en el dispositivo (`storage.js`) con auto-bloqueo tras 5 minutos de inactividad.

### Cambiado
- Actualizados metadatos de versión a `2.7.0` en `installer.iss`, `version_info.txt` y `web/index.html`.

---

## [2.6.0] - 2026-11-19

### Añadido
- **Rediseño integral de la interfaz gráfica (`web/`):**
  - Barra lateral agrupada en 4 secciones: *General*, *Sistema y Hardware*, *Seguridad y Privacidad* y *Gestión* (13 vistas en total).
  - Selector de 3 temas visuales (**Oscuro**, **OLED** y **Claro**) en la barra superior con persistencia en `localStorage` (`web/ui_kit.js`, `web/style.css`).
  - Sistema de notificaciones **Toast** flotantes no bloqueantes y **modales de confirmación** oscuros personalizados en sustitución de diálogos nativos.
  - Banner contextual descartable para advertir sobre navegadores o aplicaciones en ejecución que bloquean cachés.
  - Consola de registro en vivo colapsada por defecto en el pie de página con contador de eventos sin leer.

### Cambiado
- Actualizados metadatos de versión a `2.6.0` en `installer.iss`, `version_info.txt` y `web/index.html`.

---

## [2.5.1] - 2026-11-18

### Cambiado
- **Rediseño de la interfaz de la Bóveda Local de Contraseñas (`web/index.html`, `web/style.css`, `web/modules_v24.js`):**
  - Tarjeta de desbloqueo/creación con diseño glassmórfico y campos de ancho completo.
  - Medidor de entropía y fortaleza de contraseña en tiempo real.
  - Tarjetas de indicadores (KPIs), barra de búsqueda y filtros por categoría para credenciales guardadas.

---

## [2.5.0] - 2026-11-18

### Añadido
- **Soporte e instalador nativo para macOS (`build_macos.py`):**
  - Empaquetado de bundle `PyCleanPro.app` con ícono de alta resolución (`assets/pyclean_icon.icns`) e imagen de disco comprimida `PyCleanPro-macOS.dmg` con enlace simbólico a `/Applications`.
  - 9 categorías de limpieza nativas para macOS en `cleaner.py` (`~/Library/Caches`, `~/Library/Logs`, `~/.Trash`, navegadores Chrome/Edge/Brave/Firefox, VS Code y herramientas de desarrollo Pip/NPM/Cargo/Homebrew/Xcode DerivedData).
  - Lectura de estadísticas de RAM mediante `psutil` y limpieza automática del portapapeles con `pbcopy`.
- **Pipeline de CI/CD multiplataforma (`.github/workflows/build-release.yml`):**
  - Trabajo `build-macos` en `macos-latest` integrado junto a `build-windows` (`windows-latest`) y publicación unificada en GitHub Releases desde `ubuntu-latest`.
- **Pruebas unitarias (`tests/test_v24_modules.py`):** Añadida la 8.ª prueba unitaria (`test_macos_target_categories_and_system_stats`), elevando la suite completa a 21 pruebas en total (13 en `tests/test_cleaner.py` + 8 en `tests/test_v24_modules.py`).

---

## [2.4.0] - 2026-11-18

### Añadido
- **Monitor de Procesos y Red (`sys_monitor.py`):**
  - Listado de procesos por consumo de RAM/CPU con protección de 18 procesos críticos del sistema y PIDs `0`, `1`, `4` y propio.
  - Detección de interfaces de red IPv4 activas, selector rápido de presets DNS (Cloudflare, Google, AdGuard, DHCP automático) y prueba de latencia (Ping) con validación anti-inyección.
- **Salud de Hardware (`hardware_health.py`):**
  - Lectura S.M.A.R.T. de discos físicos en Windows (`Get-PhysicalDisk`).
  - Ejecución de optimización **SSD TRIM** (`Optimize-Volume -ReTrim`) con validación estricta de letra de unidad.
  - Diagnóstico de batería y cálculo de desgaste/ciclos (`psutil` + análisis XML de `powercfg /batteryreport`).
- **Gestor del Menú Contextual de Windows (`context_menu.py`):**
  - Auditoría de entradas del menú clic derecho del Explorador de Windows en 6 ámbitos del Registro (`HKCU`/`HKCR`).
  - Activación y desactivación 100% reversible mediante el valor `LegacyDisable`, protegiendo 15 verbos nativos de Windows.
- **Bóveda Local de Contraseñas Zero-Knowledge (`vault.py`):**
  - Cifrado autenticado **AES-256-GCM** con derivación **PBKDF2-HMAC-SHA256** (600,000 iteraciones, salt de 16 bytes, nonce de 12 bytes regenerado en cada guardado y AAD `pyclean-pro-vault-v1`).
  - Generador criptográfico CSPRNG (`secrets`), evaluador de entropía, auto-bloqueo tras 5 minutos de inactividad, limpieza automática del portapapeles en 30 segundos y respaldo/restauración cifrada (`.vault`).
- **Nuevas banderas CLI (`main.py`):** `--processes`, `--hardware` y `--context-menu`.
- **Nuevas pruebas unitarias (`tests/test_v24_modules.py`):** 7 pruebas cubriendo procesos críticos, validación DNS, XML de batería, validación TRIM, menú contextual, ciclo de vida de la bóveda y fortaleza de contraseñas.

---

## [2.3.3] - 2026-11-18

### Añadido
- Ícono personalizado de la aplicación en formatos Windows, macOS y PNG (`assets/pyclean_icon.ico`, `assets/pyclean_icon.icns`, `assets/pyclean_icon.png`).
- Metadatos de versión PE para Windows (`version_info.txt`).
- Generación automática de sumas de verificación `SHA256SUMS.txt` en los lanzamientos de GitHub Actions.
- Soporte opcional para firma de código Windows Authenticode (`signtool.exe`) en CI mediante secretos `CODE_SIGN_CERT_BASE64` y `CODE_SIGN_CERT_PASSWORD`.

---

## [2.3.2] - 2026-11-18

### Corregido
- Forzada la codificación `UTF-8` en `stdout` de los scripts de compilación para evitar fallos en consolas Windows.
- Limpiadas directivas vacías en el script de Inno Setup (`installer.iss`).

---

## [2.3.1] - 2026-11-18

### Corregido
- Mock de `st_ctime` en `test_is_file_safe_to_clean` (`tests/test_cleaner.py`) para garantizar la estabilidad de las pruebas en runners Windows de CI.

---

## [2.3.0] - 2026-11-18

### Añadido
- **Mapa de Almacenamiento, Particiones y Treemap (`cleaner.py`, `web/`):**
  - Análisis detallado de particiones y unidades (`get_partitions_detailed`), Treemap interactivo por carpetas con clasificación por tipo de archivo (`scan_folder_treemap`) y Cazador de Archivos Gigantes (`find_largest_files`).
- **Instalador oficial para Windows (`installer.iss`, `build_installer.py`, `build.bat`):**
  - Instalador `PyCleanPro-Setup.exe` compilado con Inno Setup 6, asistente en español e inglés y compresión LZMA2.
- **Nuevas banderas CLI (`main.py`):** `--partitions` y `--largest`.

---

> **Nota sobre historial previo a etiquetas Git:** Las etiquetas (`git tag`) oficiales del repositorio comienzan en `v2.3.0`. Las entradas `2.2.0`, `2.1.0` y `2.0.0` a continuación reconstruyen los commits históricos previos al etiquetado.

## [2.2.0] - 2026-11-18 *(commit histórico previo a tags)*

### Añadido
- **Desinstalador Limpio de Aplicaciones (`cleaner.py`):** Catálogo del Registro (`HKLM`, `HKCU`, `Wow6432Node`), ejecución del desinstalador oficial y escáner de residuos huérfanos en `%APPDATA%`, `%LOCALAPPDATA%` y `%ProgramData%`.
- **Programador de Mantenimiento Automático:** Creación/eliminación de tarea programada nativa en Windows (`PyCleanPro_AutoClean` vía `schtasks`).
- **Optimizador de Telemetría y Privacidad:** Auditoría y control reversible de servicios (`DiagTrack`, `dmwappushservice`, `WerSvc`) y política `AllowTelemetry`.
- **Auditor de Descargas Olvidadas:** Detección de instaladores y archivos comprimidos antiguos en `Descargas`.
- **Flujo inicial de CI/CD** con GitHub Actions (`.github/workflows/build-release.yml`).
- **Nuevas banderas CLI:** `--apps`, `--downloads-audit`, `--schedule` y `--privacy`.

---

## [2.1.0] - 2026-11-18 *(commit histórico previo a tags)*

### Añadido
- **Endurecimiento de seguridad:** Filtro de retención de 24 horas para temporales, protección contra enlaces simbólicos y *Directory Junctions*, lista blanca de exclusiones y detección de aplicaciones abiertas que bloquean cachés.
- **Herramientas avanzadas:** Triturador seguro de archivos (`shred_file`), buscador de archivos duplicados por hash SHA-256 (`find_duplicate_files`) y exportación de informes `.json` / `.txt`.
- **Empaquetado Windows portable:** Script `build_exe.py` con PyInstaller (`PyCleanPro.exe`).
- **Suite de pruebas unitarias inicial (`tests/test_cleaner.py`).**

---

## [2.0.0] - 2026-10-19 *(commits históricos previos a tags)*

### Añadido
- **Actualización base v2.0 (`2026-10-19`, commit `4c442a1`):**
  - Interfaz de escritorio mejorada en Tkinter (`gui.py`, `charts.py`) con gráficas personalizadas.
  - Expansión a categorías de limpieza en Windows con soporte multi-perfil para navegadores (Chrome, Edge, Brave, Firefox, Opera/GX y Vivaldi).
  - Gestor reversible de programas de inicio automático de Windows (`Run` ↔ `RunDisabled`).
  - Compactación de memoria RAM (`EmptyWorkingSet`) y vaciado de caché DNS (`ipconfig /flushdns`).
- **Integración de interfaz web moderna (`2026-10-21`, commit `cd9408a`):**
  - Incorporación de **PyWebView** y animaciones **GSAP** (`web_gui.py`, `web/`, `run.bat`, `run_admin.bat`), manteniendo la interfaz clásica en Tkinter (`gui.py`, `charts.py`) como respaldo.
