# 💻 Referencia CLI — PyClean Pro v2.6.0

**PyClean Pro** incluye una interfaz de línea de comandos completa en [`main.py`](../main.py) con **24 banderas** diseñadas para diagnósticos rápidos, scripts de mantenimiento y automatización con salida estructurada JSON.

> **Nota sobre la Bóveda de Contraseñas:** Las operaciones de la Bóveda (`vault.py`) son **exclusivas de la interfaz gráfica (GUI)** y no están expuestas por CLI por motivos de seguridad (evitar contraseñas maestras en el historial de terminal o en la lista de procesos).

> **Volver al inicio:** [`README.md`](../README.md) · **Guía de Usuario:** [`GUIA_USUARIO.md`](GUIA_USUARIO.md) · **Seguridad:** [`SEGURIDAD_Y_BOVEDA.md`](SEGURIDAD_Y_BOVEDA.md)

---

## 1. Reglas de Ejecución y Despacho

Al ejecutar `python main.py` (o `PyCleanPro.exe` desde terminal):
1. Si se pasa `--legacy-gui`, se abre directamente la interfaz clásica Tkinter (`gui.py`).
2. Si se pasa cualquier bandera de acción CLI (o `--cli` / `--json`), se ejecuta el modo consola (`run_cli`).
3. Sin banderas, se abre la interfaz moderna PyWebView (`web_gui.py`), con respaldo automático a Tkinter si PyWebView falla.

### Compatibilidad con `--json` y `--export`
Es fundamental distinguir entre los dos grupos de banderas de acción en `main.py`:

| Comportamiento | Banderas | Notas |
|---|---|---|
| **Acciones independientes (*early-return*)** | `--shred`, `--duplicates`, `--apps`, `--downloads-audit`, `--schedule`, `--privacy` | Se ejecutan inmediatamente y finalizan el proceso antes del bloque `--json`. **No** soportan `--json` ni `--export`. Si se combinan varias, solo se ejecuta la primera según el orden de prioridad en `main.py` (`--shred` → `--duplicates` → `--apps` → `--downloads-audit` → `--schedule` → `--privacy`). |
| **Acciones combinables (soportan `--json`)** | `--scan`, `--clean`, `--dry-run`, `--ram`, `--dns`, `--all`, `--startup`, `--partitions`, `--largest`, `--processes`, `--hardware`, `--context-menu` | Pueden combinarse libremente en un mismo comando. Con `--json`, emiten un único objeto JSON en `stdout` y, si se añade `--export`, escriben ese objeto completo en el archivo destino. |
| **`--export` sin `--json`** | `--scan`, `--dry-run`, `--clean`, `--all` | En salida legible para humanos, `--export` solo genera archivo cuando existe un reporte de escaneo o limpieza (`action_report`). Usa formato `.txt` si la ruta termina en `.txt`; en caso contrario guarda `.json`. |

---

## 2. Catálogo Completo de las 24 Banderas

### Limpieza y Optimización Principal

| Bandera | Parámetro / Defecto | Plataforma / Privilegios | Descripción |
|---|---|---|---|
| `--scan` | *(flag)* | Multiplataforma / Usuario (Admin para 5 cat. Windows) | Escanea las categorías de limpieza en modo solo lectura y muestra el espacio recuperable respetando `min_age_hours` y exclusiones de `cleaner_config.json`. |
| `--clean` | *(flag)* | Multiplataforma / Usuario (Admin para 5 cat. Windows) | Elimina los archivos basura de las categorías aplicables y reporta espacio liberado, archivos eliminados y omitidos. |
| `--dry-run` | *(flag)* | Multiplataforma / Usuario | Simula una limpieza ejecutando el mismo análisis de solo lectura que `--scan` sin borrar ningún archivo. |
| `--ram` | *(flag)* | Windows / Usuario (más efectivo con Admin) | Compacta la memoria RAM de procesos accesibles (`EmptyWorkingSet`). |
| `--dns` | *(flag)* | Windows / Usuario | Vacía la caché local de resolución DNS (`ipconfig /flushdns`). |
| `--all` | *(flag)* | Windows / macOS | Ejecuta en secuencia: optimización de RAM (`--ram`), vaciado DNS (`--dns`) y limpieza completa (`--clean`). |
| `--drive` | `DRIVE` (defecto en `argparse`: `C:\`, con respaldo automático en tiempo de ejecución a `/` en Unix/macOS cuando `C:\` no existe) | Multiplataforma | Especifica la unidad o punto de montaje cuyas estadísticas de disco se muestran en el resumen inicial y en `--json`. |

### Seguridad, Archivos y Descargas

| Bandera | Parámetro / Defecto | Plataforma / Privilegios | Descripción |
|---|---|---|---|
| `--shred` | `FILE` | Multiplataforma / Usuario | **Acción independiente.** Sobrescribe un archivo con bytes aleatorios + ceros, lo renombra temporalmente y lo elimina de forma irrecuperable. Rechaza enlaces simbólicos y *junctions*. |
| `--shred-passes` | `N` (entero, defecto: `1`) | Multiplataforma / Usuario | Número de pasadas aleatorias para `--shred` (ej. `3` para estilo DoD 5220.22-M). Siempre se añade una pasada final de ceros. |
| `--duplicates` | `DIR` | Multiplataforma / Usuario | **Acción independiente.** Busca archivos duplicados (≥ 1 KB) en `DIR` por tamaño + hash SHA-256 y muestra hasta 20 grupos en consola (hasta 100 grupos calculados). |
| `--downloads-audit` | `[DAYS]` (opcional, defecto: `30`) | Multiplataforma / Usuario | **Acción independiente.** Audita `~/Downloads` (o `~/Descargas`) buscando instaladores y comprimidos antiguos con más de `DAYS` días. |

### Análisis de Almacenamiento

| Bandera | Parámetro / Defecto | Plataforma / Privilegios | Descripción |
|---|---|---|---|
| `--partitions` | *(flag)* | Multiplataforma / Usuario | Lista particiones y discos detectados con etiqueta, sistema de archivos, tipo, espacio libre y porcentaje de uso. |
| `--largest` | `[DIR]` (opcional, defecto: `C:\` / `/`) | Multiplataforma / Usuario | Busca archivos de ≥ 100 MB en `DIR`. Muestra los **20** más grandes en modo consola y hasta **50** en modo `--json`. |

### Gestión de Windows

| Bandera | Parámetro / Defecto | Plataforma / Privilegios | Descripción |
|---|---|---|---|
| `--startup` | *(flag)* | Windows / Usuario | Lista las entradas de inicio automático en `HKCU` y `HKLM` (`Run` y `RunDisabled`) indicando si están habilitadas o deshabilitadas. |
| `--apps` | *(flag)* | Windows / Usuario | **Acción independiente.** Enumera las aplicaciones instaladas desde el Registro (`HKLM`, `HKCU`, `Wow6432Node`) con versión y tamaño estimado. |
| `--schedule` | `{on,off}` | Windows / **Admin** | **Acción independiente.** Activa (`on`) o desactiva (`off`) la tarea semanal `PyCleanPro_AutoClean` en el Programador de Tareas de Windows (domingos 03:00, `--clean --all`). |
| `--privacy` | `{on,off}` | Windows / **Admin** | **Acción independiente.** Con `on` mitiga la telemetría de Windows (`DiagTrack`, `dmwappushservice`, `WerSvc` y `AllowTelemetry = 0`); con `off` restaura los valores predeterminados. |

### Monitor, Hardware y Menú Contextual

| Bandera | Parámetro / Defecto | Plataforma / Privilegios | Descripción |
|---|---|---|---|
| `--processes` | *(flag)* | Multiplataforma / Usuario | Lista los procesos ordenados por consumo de RAM, marcando con `[SO]` los procesos críticos protegidos. Muestra **20** en consola y **25** en modo `--json`. |
| `--hardware` | *(flag)* | Windows (completo) / macOS-Linux (batería básica) | Muestra la salud S.M.A.R.T. de discos físicos y el estado/desgaste/ciclos de la batería. |
| `--context-menu` | *(flag)* | Windows / Usuario | Lista entradas del menú contextual (clic derecho) del Explorador de Windows indicando si están activas u ocultas (`LegacyDisable`). Muestra hasta **30** en consola y todas en modo `--json`. |

### Salida y Modo de Ejecución

| Bandera | Parámetro / Defecto | Plataforma / Privilegios | Descripción |
|---|---|---|---|
| `--export` | `PATH` | Multiplataforma / Usuario | Exporta resultados a un archivo `.json` o `.txt`. En modo `--json` exporta todo el payload JSON; en modo texto exporta el reporte de `--scan`/`--dry-run`/`--clean`/`--all`. |
| `--json` | *(flag)* | Multiplataforma / Usuario | Emite la salida completa en formato JSON estructurado (UTF-8) en `stdout`, ideal para integración con scripts o monitoreo. |
| `--cli` | *(flag)* | Multiplataforma / Usuario | Fuerza la ejecución en modo consola mostrando el resumen del sistema (privilegios, apps bloqueadas, disco y RAM) incluso sin otras banderas de acción. |
| `--legacy-gui` | *(flag)* | Multiplataforma / Usuario | Abre la interfaz gráfica clásica en Tkinter (`gui.py`, subconjunto v2.0) en lugar de la interfaz moderna PyWebView. |

---

## 3. Ejemplos Prácticos

### Diagnóstico sin modificaciones
```bash
# Escaneo rápido en consola
python main.py --scan

# Simulación de limpieza analizando la unidad D:\
python main.py --dry-run --drive D:\

# Resumen rápido del sistema, procesos, hardware y particiones en JSON
python main.py --partitions --processes --hardware --json
```

### Limpieza y exportación de informes
```bash
# Limpieza completa + RAM + DNS y exportación de reporte en texto plano
python main.py --all --export informe_limpieza.txt

# Escaneo completo en JSON guardado en archivo para auditoría
python main.py --scan --startup --context-menu --json --export auditoria.json
```

### Herramientas de archivos y mantenimiento
```bash
# Triturar un documento confidencial con 3 pasadas aleatorias + ceros
python main.py --shred "C:\Users\Usuario\confidencial.pdf" --shred-passes 3

# Buscar duplicados por SHA-256 en una carpeta de respaldos
python main.py --duplicates "D:\Respaldos"

# Auditar instaladores en Descargas con más de 60 días
python main.py --downloads-audit 60

# Buscar archivos mayores a 100 MB en el disco D:\
python main.py --largest D:\
```

### Administración en Windows (ejecutar terminal como Administrador)
```powershell
# Activar mantenimiento semanal automático (domingos 03:00 AM)
python main.py --schedule on

# Desactivar tarea programada
python main.py --schedule off

# Mitigar telemetría de Windows
python main.py --privacy on

# Restaurar configuración de telemetría
python main.py --privacy off
```

---

## 4. Recetas de Automatización

### Windows: Tarea Programada Nativa
La forma más sencilla en Windows es usar la bandera integrada (como Administrador):
```powershell
python main.py --schedule on
```
Esto crea la tarea `PyCleanPro_AutoClean` en `schtasks` con privilegios elevados (`/rl HIGHEST`) todos los domingos a las `03:00` ejecutando `--clean --all`.

### macOS / Linux: Limpieza periódica con `cron`
Para ejecutar una limpieza semanal en segundo plano los domingos a las 03:00 y guardar un reporte JSON:
```cron
0 3 * * 0 /usr/bin/python3 /ruta/a/cleanerpc/main.py --clean --json --export "$HOME/pyclean_last.json" >/dev/null 2>&1
```
*(Reemplaza `/ruta/a/cleanerpc` por la ubicación real del repositorio en tu equipo).*
