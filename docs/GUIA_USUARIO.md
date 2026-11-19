# 📖 Guía de Usuario — PyClean Pro v2.6.0

Esta guía explica cómo utilizar la interfaz moderna de **PyClean Pro v2.6.0**, sus controles globales, sus **13 vistas organizadas en 4 grupos**, las categorías de limpieza en Windows y macOS, y la interfaz clásica de respaldo (`--legacy-gui`).

> **Volver al inicio:** [`README.md`](../README.md) · **Línea de comandos:** [`CLI.md`](CLI.md) · **Seguridad y Bóveda:** [`SEGURIDAD_Y_BOVEDA.md`](SEGURIDAD_Y_BOVEDA.md)

---

## 1. Inicio y Controles Globales

Al ejecutar `python main.py` (o abrir `PyCleanPro.exe` / `PyCleanPro.app`), se abre la interfaz moderna basada en PyWebView y GSAP (100% offline, sin conexión a internet requerida).

### Estructura permanente de la ventana
1. **Barra lateral izquierda (4 grupos, 13 vistas):**
   - Muestra la cabecera `v2.6 • Suite Pro`, los 4 grupos de navegación, un contador de categorías seleccionadas junto a **Limpieza** y el indicador de privilegios en la parte inferior.
   - **Elevación a Administrador (Windows):** Si la aplicación corre como usuario estándar, aparece el botón **`⚡ Elevar`**, que solicita elevación UAC para habilitar funciones administrativas (caché de Windows Update, Prefetch, SSD TRIM, DNS, telemetría y claves `HKLM`/`HKCR`).
2. **Barra superior (acciones rápidas):**
   - **Selector de unidad:** Cambia el disco monitoreado en el Dashboard (`C:\`, `D:\`, etc., o `/` en macOS/Linux).
   - **`Liberar RAM`:** Compacta el *Working Set* de procesos accesibles en Windows (`EmptyWorkingSet`).
   - **`Vaciar DNS`:** Limpia la caché local de resolución DNS en Windows (`ipconfig /flushdns`).
   - **`Exportar`:** Guarda un reporte `.json` del último escaneo o limpieza en el Escritorio (o `Descargas` si no existe).
   - **Selector de tema:** Alterna entre **Oscuro** (predeterminado), **OLED** (negro puro `#000000`) y **Claro** (`#F3F5F9`). La preferencia se guarda automáticamente en `localStorage`.
3. **Banner contextual de aplicaciones abiertas:**
   - Visible únicamente en **Dashboard** y **Limpieza** cuando se detectan navegadores o aplicaciones en ejecución que bloquean cachés (Chrome, Edge, Brave, Firefox, Opera/GX, Vivaldi, Discord, Spotify, VS Code). Puede descartarse durante la sesión actual.
4. **Pie de página global y Consola en Vivo:**
   - Barra de progreso global y botones **`Analizar Sistema`** (solo lectura) y **`Limpiar Ahora`** (habilitado tras encontrar espacio recuperable).
   - **Consola en Vivo colapsable:** Permanece cerrada por defecto para mantener la vista limpia, mostrando un indicador de eventos nuevos sin leer y un botón para limpiar el registro.
5. **Notificaciones Toast y Modales de confirmación:**
   - Las acciones muestran avisos flotantes no bloqueantes (se ocultan a los 3.4 s).
   - Las operaciones destructivas (triturado, desinstalación, borrado de credenciales o residuos) abren un modal de confirmación oscuro con soporte de teclado (`Enter` confirma, `Escape` cancela).

---

## 2. Recorrido por las 13 Vistas (4 Grupos)

### Grupo 1: General

#### 1. Dashboard
- Muestra **dos medidores SVG circulares animados** (uso de Disco y Memoria RAM) para la unidad seleccionada en la barra superior.
- Presenta el contador animado de **espacio recuperable** (bytes y cantidad de archivos) y el **desglose horizontal por categoría** tras ejecutar **Analizar Sistema**.

#### 2. Limpieza
- Lista todas las categorías disponibles en el sistema operativo actual con casillas de selección (`Seleccionar Todos` / `Deseleccionar`), insignia **`Admin`** en las categorías que requieren privilegios elevados, tamaño detectado y cantidad de archivos.
- Todas las categorías vienen seleccionadas por defecto. Al pulsar **Analizar Sistema** o **Limpiar Ahora** en el pie de página, solo se procesan las categorías marcadas.

##### Categorías de limpieza en Windows (20 categorías)
- **Nivel de usuario (15 categorías):**
  1. `user_temp` — Temporales de usuario (`%TEMP%`, con filtro de antigüedad de 24 h).
  2. `recycle_bin` — Papelera de Reciclaje (vaciado silencioso vía Win32 `SHEmptyRecycleBinW`).
  3. `browser_chrome` — Caché de Google Chrome (soporte multi-perfil).
  4. `browser_edge` — Caché de Microsoft Edge (soporte multi-perfil).
  5. `browser_brave` — Caché de Brave Browser (soporte multi-perfil).
  6. `browser_firefox` — Caché `cache2` de Mozilla Firefox (soporte multi-perfil).
  7. `browser_opera` — Caché de Opera Stable y Opera GX.
  8. `browser_vivaldi` — Caché de Vivaldi (soporte multi-perfil).
  9. `dev_tools` — Cachés de desarrollo: `pip`, `npm`, `pnpm`, `yarn` y `cargo` (con filtro de antigüedad).
  10. `app_discord` — Caché multimedia de Discord.
  11. `app_spotify` — Almacenamiento temporal de Spotify.
  12. `app_vscode` — Caché de Visual Studio Code (`Cache`, `CachedData`, temporales VSIX).
  13. `windows_inet_cache` — Caché web del sistema (`INetCache`, con filtro de antigüedad).
  14. `crash_dumps` — Volcados de error (`CrashDumps`, `WER\ReportArchive`, `WER\ReportQueue`).
  15. `thumbnail_cache` — Caché de miniaturas e íconos del Explorador (`thumbcache_*.db`, `iconcache_*.db`).
- **Requieren Administrador (5 categorías):**
  16. `system_temp` — Temporales del sistema (`C:\Windows\Temp`, con filtro de antigüedad).
  17. `windows_update_cache` — Descargas de Windows Update (`SoftwareDistribution\Download`).
  18. `windows_delivery_opt` — Optimización de Distribución (`DeliveryOptimization`).
  19. `windows_logs` — Registros antiguos de Windows (`C:\Windows\Logs` y `Panther`, con filtro de antigüedad).
  20. `prefetch` — Archivos de precarga (`C:\Windows\Prefetch`).

##### Categorías de limpieza nativas en macOS (9 categorías, todas de nivel usuario)
1. `macos_user_caches` — Cachés de usuario (`~/Library/Caches`, con filtro de antigüedad).
2. `macos_user_logs` — Registros de usuario (`~/Library/Logs`, con filtro de antigüedad).
3. `macos_trash` — Papelera del usuario (`~/.Trash`).
4. `browser_chrome` — Caché de Google Chrome.
5. `browser_edge` — Caché de Microsoft Edge.
6. `browser_brave` — Caché de Brave.
7. `browser_firefox` — Caché de Mozilla Firefox.
8. `vscode_cache` — Caché de Visual Studio Code.
9. `dev_tools` — Cachés de `pip`, `.npm`, `.cargo`, `Homebrew` y `Xcode/DerivedData`.

> **Nota:** La limpieza de navegadores **nunca** elimina contraseñas, marcadores, historial ni sesiones abiertas; únicamente limpia directorios de caché.

#### 3. Archivos Top
- Tras ejecutar un escaneo, muestra los **100 archivos basura más pesados** detectados (nombre, tamaño y ruta en disco).
- Cada fila incluye el botón **`📁 Explorar`** para revelar el archivo directamente en el explorador del sistema operativo.

---

### Grupo 2: Sistema y Hardware

#### 4. Mapa de Disco
Combina tres herramientas visuales de análisis de almacenamiento:
1. **Particiones y Unidades:** Tarjetas con letra/punto de montaje, etiqueta de volumen, sistema de archivos (`NTFS`, `FAT32`, etc.), espacio libre/total y barra de uso con alertas visuales (>75% advertencia, >88% crítico). Hacer clic en una partición escanea su raíz en el Treemap.
2. **Treemap Interactivo:** Bloques proporcionales por peso de carpeta/archivo, etiquetas de clasificación por tipo (**Videos**, **Imágenes**, **Comprimidos e ISOs**, **Ejecutables e Instaladores**, **Documentos**, **Desarrollo y Código**, **Otros**), navegación hacia adentro (`Entrar ➔`) y botón **`⬆ Subir Nivel`**.
3. **Cazador de Archivos Gigantes:** Busca los 50 archivos más grandes en la ruta actual por encima de un umbral configurable (`100 MB`, `500 MB`, `1 GB` o `2 GB`), con acciones directas **`📁 Abrir`** o **`⚡ Triturar`** (sobrescritura de 3 pasadas tras confirmación).

#### 5. Monitor y Red
1. **Top 35 Procesos:** Tabla ordenable por **RAM** o **CPU**. Los **18 procesos críticos del sistema** (como `lsass.exe`, `csrss.exe`, `winlogon.exe`, `svchost.exe`, `explorer.exe`, `systemd`, además de los PIDs `0`, `1`, `4` y el propio proceso de PyClean Pro) muestran la insignia **`SO`** y están bloqueados contra finalización accidental.
2. **Selector Rápido de DNS (Windows, requiere Admin):** Lista las interfaces de red IPv4 activas y permite aplicar en un clic los presets **Cloudflare (`1.1.1.1`)**, **Google (`8.8.8.8`)**, **AdGuard (`94.140.14.14`)** o **DHCP Automático**, vaciando la caché DNS al finalizar.
3. **Prueba de Latencia (Ping):** Mide disponibilidad y latencia hacia `1.1.1.1`, `8.8.8.8` y `github.com` con indicadores de color (verde ≤120 ms, amarillo >120 ms, rojo inalcanzable).

> **Alcance del módulo:** `sys_monitor.py` monitorea procesos (CPU/RAM), interfaces IPv4, presets DNS y ping. **No** recopila métricas de GPU.

#### 6. Salud Hardware
1. **Discos Físicos (S.M.A.R.T.) y SSD TRIM (Windows):** Muestra el estado de salud, tipo de medio (SSD/HDD/NVMe), bus y capacidad mediante `Get-PhysicalDisk`. Incluye selector de letra de unidad y botón **`⚡ Ejecutar TRIM`** (`Optimize-Volume -ReTrim`, requiere Administrador).
2. **Salud de Batería:** Muestra porcentaje actual y estado de corriente en cualquier plataforma (`psutil`), y en portátiles Windows añade capacidad de diseño vs. carga completa (mWh), porcentaje real de salud, desgaste y conteo de ciclos mediante `powercfg /batteryreport /xml`. En equipos de escritorio muestra el aviso correspondiente.

> **Alcance del módulo:** `hardware_health.py` cubre S.M.A.R.T., SSD TRIM y desgaste de batería. **No** incluye sensores de temperatura ni velocidad de ventiladores.

#### 7. Inicio Rápido (Windows)
- Enumera los programas configurados en el Registro (`HKCU` y `HKLM` bajo `Software\Microsoft\Windows\CurrentVersion\Run` y `RunDisabled`).
- Cada entrada dispone de un interruptor reversible que mueve la clave entre `Run` y `RunDisabled` sin borrar la configuración original. Modificar entradas de ámbito `HKLM` requiere privilegios de Administrador.

---

### Grupo 3: Seguridad y Privacidad

#### 8. Bóveda
Gestor local de contraseñas *Zero-Knowledge* 100% offline cifrado con **AES-256-GCM** y **PBKDF2-HMAC-SHA256** (600,000 iteraciones):
- **Primer uso:** Crea la bóveda con una contraseña maestra (mínimo 8 caracteres) y medidor de fortaleza en vivo. También puedes importar un respaldo cifrado previo (`.vault`).
- **Panel desbloqueado:**
  - 3 tarjetas KPI (total de credenciales, categorías y estado de cifrado).
  - Formulario para crear o editar credenciales (título, categoría, usuario, URL, contraseña con botón **`🎲 Generar`** y notas).
  - Generador criptográfico CSPRNG con control deslizante de longitud (10–48 caracteres en UI) y selección de mayúsculas, números y símbolos.
  - Búsqueda en tiempo real, filtros por categoría y botones por credencial: **`📋 Copiar Clave`** (limpia automáticamente el portapapeles a los 30 segundos en Windows y macOS), **`✏️ Editar`** y **`🗑️ Eliminar`**.
  - Acciones globales: **`💾 Exportar Respaldo`** (`.vault`) y **`🔒 Bloquear Bóveda`** (también se bloquea automáticamente tras 5 minutos de inactividad).

> Consulta los detalles criptográficos y el modelo de amenazas completo en [`SEGURIDAD_Y_BOVEDA.md`](SEGURIDAD_Y_BOVEDA.md).

#### 9. Privacidad (Windows, requiere Admin)
- Audita el estado de los servicios de diagnóstico (`DiagTrack`, `dmwappushservice`, `WerSvc`) y la directiva del Registro `HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection\AllowTelemetry`.
- Permite aplicar **`Mitigar Telemetría`** (desactiva servicios y fija `AllowTelemetry = 0`) o **`Restablecer Valores`** (restaura servicios a inicio automático y `AllowTelemetry = 1`).

#### 10. Herramientas
Reúne tres utilidades independientes:
1. **Triturador Seguro:** Sobrescribe un archivo seleccionado con datos aleatorios (`1` o `3` pasadas tipo DoD 5220.22-M + pasada final de ceros), renombra temporalmente el archivo y lo elimina de forma irreversible (previa confirmación).
2. **Buscador de Duplicados:** Analiza una carpeta en dos fases (tamaño exacto + hash **SHA-256** completo) y lista hasta 100 grupos de duplicados ordenados por espacio desperdiciado.
3. **Auditor de Descargas Olvidadas:** Escanea `~/Downloads` (o `~/Descargas`) en busca de instaladores y comprimidos antiguos (`.exe`, `.msi`, `.iso`, `.zip`, `.rar`, `.7z`, `.tar.gz`, `.dmg`, `.pkg`) con más de `30`, `60` o `90` días, permitiendo eliminar elementos seleccionados de forma individual.

---

### Grupo 4: Gestión

#### 11. Desinstalador (Windows)
- Muestra las aplicaciones instaladas registradas en `HKLM`, `HKCU` y `Wow6432Node` (filtrando componentes internos del sistema) con búsqueda instantánea.
- Al pulsar **`Desinstalar`**, solicita confirmación, lanza el desinstalador nativo de la aplicación y, tras 3 segundos, busca automáticamente carpetas residuales huérfanas en `%LOCALAPPDATA%`, `%APPDATA%` y `%ProgramData%` para ofrecer su eliminación segura (omitiendo carpetas protegidas del sistema).

#### 12. Menú Contextual (Windows)
- **Función exacta:** Audita y permite desactivar o reactivar entradas de terceros en el menú contextual ("clic derecho") del Explorador de Windows sobre archivos, carpetas y fondo de directorio (`HKCU` y `HKCR`). **No** instala accesos de PyClean Pro en el menú contextual.
- Utiliza el mecanismo estándar y 100% reversible **`LegacyDisable`** (no elimina claves del Registro).
- Protege **15 verbos nativos de Windows** (como `open`, `explore`, `edit`, `print`, `runas`, `cmd`, `powershell`, `properties`), mostrados con la etiqueta `Nativo Windows`. Modificar entradas de `HKCR` requiere Administrador.

#### 13. Ajustes
1. **Antigüedad mínima de archivos:** Configura el filtro de retención (`0` a `720` horas; presets rápidos `0h`, `12h`, `24h`, `48h`; valor por defecto: `24h`).
2. **Lista blanca de exclusiones:** Añade o quita carpetas que nunca serán analizadas ni eliminadas por la limpieza.
3. **Programador de Tareas (Windows, requiere Admin):** Activa o desactiva la tarea programada `PyCleanPro_AutoClean` (`schtasks`) con frecuencia **semanal** (domingos 03:00) o **diaria** (03:00), ejecutando limpieza automática `--clean --all`.

---

## 3. Interfaz Clásica de Respaldo (`--legacy-gui`)

PyClean Pro conserva una interfaz de escritorio clásica construida en **Tkinter** (`gui.py` + `charts.py`) que cumple dos funciones:
1. **Respaldo automático:** Si PyWebView o el motor WebView2/WebKit no está disponible al ejecutar `python main.py`, la aplicación inicia automáticamente la interfaz Tkinter.
2. **Lanzamiento manual:** Puedes abrirla directamente ejecutando:
   ```bash
   python main.py --legacy-gui
   ```

### Alcance de la interfaz clásica
La interfaz clásica implementa el **subconjunto de funciones v2.0** organizado en **4 pestañas**:
1. **Dashboard / Gráficos:** Gráficos Canvas (`DonutChart` y `HorizontalBarBreakdown`), selector de unidad, compactación de RAM y vaciado DNS.
2. **Opciones de Limpieza:** Selección de categorías y ventana emergente para inspeccionar archivos pesados.
3. **Inicio de Windows:** Listado y activación/desactivación de programas de inicio.
4. **Ajustes y Exclusiones:** Antigüedad mínima de archivos y lista blanca de carpetas.

> Para utilizar los módulos introducidos a partir de v2.2–v2.6 (Mapa de Disco, Desinstalador, Privacidad, Triturador, Duplicados, Auditor de Descargas, Monitor y Red, Salud Hardware, Menú Contextual, Bóveda de Contraseñas y temas Oscuro/OLED/Claro), utiliza la **interfaz moderna predeterminada**.
