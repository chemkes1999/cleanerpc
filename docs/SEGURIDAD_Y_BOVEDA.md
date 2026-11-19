# 🔐 Seguridad, Salvaguardas y Bóveda Cifrada — PyClean Pro v2.6.0

Este documento detalla la especificación criptográfica de la **Bóveda Local de Contraseñas** (`vault.py`), los mecanismos de seguridad aplicados durante la limpieza y gestión del sistema, y un modelo de amenazas honesto con las limitaciones conocidas.

> **Volver al inicio:** [`README.md`](../README.md) · **Guía de Usuario:** [`GUIA_USUARIO.md`](GUIA_USUARIO.md) · **Arquitectura:** [`ARQUITECTURA.md`](ARQUITECTURA.md)

---

## 1. Bóveda Local de Contraseñas (`vault.py`)

La Bóveda de PyClean Pro adopta un diseño **Zero-Knowledge 100% offline**: nunca envía datos por red, nunca almacena la contraseña maestra en disco y cifra el catálogo completo de credenciales (incluyendo todos los metadatos).

### 1.1 Primitivas Criptográficas

| Componente | Especificación exacta en `vault.py` | Propósito |
|---|---|---|
| **Derivación de clave (KDF)** | `PBKDF2-HMAC-SHA256` (`cryptography`) | Derivar la clave simétrica a partir de la contraseña maestra. |
| **Iteraciones KDF** | `PBKDF2_ITERATIONS = 600_000` | Endurecimiento frente a ataques de fuerza bruta offline (alineado con OWASP). |
| **Salt** | `16` bytes (`128` bits) generados con `os.urandom(16)` | Valor único generado al crear la bóveda para evitar tablas arcoíris. |
| **Longitud de clave derivada** | `32` bytes (`256` bits) | Clave de sesión en memoria para AES-256. |
| **Cifrado autenticado (AEAD)** | `AES-256-GCM` (`AESGCM`) | Confidencialidad e integridad autenticada de la carga útil. |
| **Nonce / IV** | `12` bytes (`96` bits) vía `os.urandom(12)` | **Regenerado aleatoriamente en cada guardado** (`_persist()`), evitando reutilización de nonce. |
| **Etiqueta de autenticación (Tag)** | `16` bytes (`128` bits) | Anexada automáticamente al texto cifrado y verificada en cada descifrado; detecta cualquier alteración del archivo. |
| **Datos Autenticados Adicionales (AAD)** | `VAULT_AAD = b"pyclean-pro-vault-v1"` | Vincula criptográficamente el texto cifrado a la versión del formato de bóveda. |

### 1.2 Formato del Sobre en Disco (`vault.enc`)

La bóveda se almacena como un archivo JSON UTF-8 estructurado:

```json
{
  "version": 1,
  "kdf": "pbkdf2-sha256",
  "iterations": 600000,
  "salt": "<base64(16 bytes)>",
  "nonce": "<base64(12 bytes)>",
  "ciphertext": "<base64(payload_json_cifrado + tag_gcm_16_bytes)>"
}
```

- **Ubicación predeterminada:**
  - **Windows:** `%APPDATA%\PyCleanPro\vault.enc` (respaldo: `~\PyCleanPro\vault.enc`).
  - **macOS / Linux:** `~/.pycleanpro/vault.enc`.
- **Escritura atómica:** Cada operación de guardado escribe primero en `<vault_path>.tmp` y realiza el reemplazo atómico con `os.replace()`. Esto previene corrupción de la bóveda si ocurre un corte de energía o cierre inesperado durante la escritura.
- **Cifrado completo de metadatos:** Toda la estructura `{"entries": [...]}` —incluyendo `id`, `title`, `username`, `password`, `url`, `category`, `notes`, `created_at` y `updated_at`— se serializa y cifra dentro de `ciphertext`. Ningún título, URL ni conteo de entradas es visible en disco.

### 1.3 Gestión de Sesión, Portapapeles y Generador

- **Contraseña maestra:** Mínimo obligatorio de **8 caracteres** al crear la bóveda (`create()`). Nunca se guarda en disco.
- **Auto-bloqueo por inactividad:** `AUTO_LOCK_SECONDS = 300` (**5 minutos**). Se verifica de forma perezosa en cada comprobación de `is_unlocked()`; al expirar, `lock()` elimina las referencias en memoria a la clave y a las entradas descifradas.
- **Limpieza automática del portapapeles (30 segundos):** Al copiar un secreto desde la interfaz (`vault_copy_secret()` en `web_gui.py`), se programa un temporizador `threading.Timer` (30 s por defecto) que sobrescribe el portapapeles con una cadena vacía:
  - **Windows:** utiliza `clip` (codificación UTF-16LE).
  - **macOS:** utiliza `pbcopy` (codificación UTF-8).
  - **Linux:** el copiado automático al portapapeles **no está soportado** actualmente (retorna `success: False`).
- **Generador criptográfico CSPRNG (`generate_password`):** Usa el módulo `secrets` de Python, restringe la longitud entre `8` y `128` caracteres (`10–48` en el deslizador de la UI), garantiza al menos un carácter de cada conjunto activado y baraja el resultado con Fisher-Yates usando `secrets.randbelow`.
- **Evaluador de entropía (`evaluate_password_strength`):** Calcula `longitud × log2(tamaño_alfabeto)` (alfabeto máximo 94) y clasifica en **Débil** (`<40` bits), **Media** (`<60` bits), **Fuerte** (`<85` bits) y **Muy Fuerte** (`≥85` bits).
- **Respaldos cifrados (`.vault`):** Las funciones de exportación e importación copian o reemplazan el sobre cifrado completo sin exponer texto plano.

---

## 2. Salvaguardas de Limpieza y Protección del Sistema

PyClean Pro aplica múltiples capas defensivas para evitar pérdida de datos o inestabilidad del sistema operativo:

| Mecanismo | Módulo | Comportamiento exacto |
|---|---|---|
| **Filtro de retención de 24 horas** | `cleaner.py` (`is_file_safe_to_clean`) | Conserva por defecto archivos temporales y logs modificados recientemente (`min_age_hours = 24`, configurable en Ajustes). En Windows evalúa `max(st_mtime, st_ctime)`; en Unix usa `st_mtime`. Falla de forma segura (*fail-closed*: retorna `False` ante errores). |
| **Guardia contra Symlinks y *Directory Junctions*** | `cleaner.py` (`is_safe_link_or_junction`) | Verifica `os.path.islink()` y `os.path.isjunction()` antes de recorrer, limpiar, triturar o buscar residuos. Nunca sigue enlaces hacia carpetas personales o discos externos. Falla de forma segura (*fail-closed*). |
| **Lista blanca de exclusiones** | `cleaner.py` (`is_path_excluded`) | Compara rutas absolutas normalizadas; cualquier carpeta excluida en `cleaner_config.json` se omite en escaneos y limpiezas. |
| **Detección de aplicaciones bloqueantes** | `cleaner.py` (`LOCKED_APPS_MAP`, `get_running_locked_apps`) | Detecta 9 aplicaciones en ejecución en Windows (Chrome, Edge, Brave, Firefox, Opera/GX, Vivaldi, Discord, Spotify, VS Code) para avisar al usuario y evitar bloqueos de caché. |
| **Protección de procesos críticos** | `sys_monitor.py` (`CRITICAL_PROCESSES`, `is_critical_process`) | Impide finalizar 18 procesos críticos del SO (`system`, `system idle process`, `registry`, `smss.exe`, `csrss.exe`, `wininit.exe`, `services.exe`, `lsass.exe`, `lsaiso.exe`, `winlogon.exe`, `svchost.exe`, `dwm.exe`, `explorer.exe`, `fontdrvhost.exe`, `memory compression`, `ntoskrnl.exe`, `init`, `systemd`), los PIDs `0`, `1`, `4` y el propio PID de PyClean Pro. |
| **Ediciones 100% reversibles del Registro** | `cleaner.py`, `context_menu.py` | El gestor de inicio mueve claves entre `Run` y `RunDisabled`; el gestor de menú contextual escribe o elimina el valor `LegacyDisable` sin borrar claves y protege **15 verbos nativos de Windows**. |
| **Protección en escáner de residuos** | `cleaner.py` (`find_app_leftovers`) | Exige coincidencia de longitud ≥ 3 y omite nombres protegidos (`microsoft`, `windows`, `temp`, `programs`, `packages`, `system`, `common`) y enlaces simbólicos. |
| **Validación anti-inyección (Regex)** | `hardware_health.py`, `sys_monitor.py` | `run_ssd_trim()` valida estrictamente `^[A-Z]$` antes de invocar PowerShell; `run_ping_test()` valida `^[a-zA-Z0-9.\-]+$` antes de invocar `ping`. |

---

## 3. Modelo de Amenazas y Limitaciones Conocidas

Para una evaluación realista de seguridad, ten en cuenta las siguientes limitaciones inherentes al diseño actual:

1. **Permanencia temporal en memoria RAM (Python):**
   - Los objetos `bytes` y `str` en Python son inmutables y gestionados por el recolector de basura. Aunque `PasswordVault.lock()` elimina todas las referencias a la clave derivada y a las credenciales en memoria, Python no garantiza la puesta a cero inmediata (*zeroization*) de las páginas físicas de RAM frente a un atacante con acceso privilegiado a volcados de memoria del proceso.
2. **Triturador seguro en unidades SSD / NVMe y sistemas Copy-on-Write:**
   - `shred_file()` sobrescribe el archivo en bloques de 64 KB (`passes` pasadas de `os.urandom` + 1 pasada de `\x00` + `fsync`), lo renombra y lo elimina. Esto es efectivo en discos magnéticos (HDD), pero en unidades **SSD/NVMe con *wear-leveling*** o sistemas de archivos *Copy-on-Write* (como APFS o ZFS), los bloques flash anteriores pueden persistir físicamente hasta que el controlador ejecute TRIM o recolección de basura. Para confidencialidad garantizada en SSD, utiliza cifrado de disco completo (BitLocker / FileVault).
3. **Permisos de archivo por defecto en `vault.enc`:**
   - El archivo `vault.enc` hereda los permisos predeterminados del sistema operativo (en macOS/Linux no aplica explícitamente `chmod 0600`). En equipos multiusuario Unix, se recomienda restringir manualmente los permisos con `chmod 600 ~/.pycleanpro/vault.enc`.
4. **Sin API dedicada de rotación de contraseña maestra:**
   - Actualmente no existe un botón o método automatizado para rotar la contraseña maestra o regenerar el `salt` sobre una bóveda existente; para cambiar la contraseña maestra, se debe recrear la bóveda manualmente.
5. **Sin limitación de intentos por software (*rate-limiting*):**
   - La resistencia contra ataques de fuerza bruta offline depende exclusivamente del costo computacional de **PBKDF2-HMAC-SHA256 (600,000 iteraciones)** y de la entropía de tu contraseña maestra. Utiliza una frase de contraseña larga y única.
6. **Ubicación de `cleaner_config.json` en instalaciones protegidas:**
   - El archivo `cleaner_config.json` se guarda junto al módulo `cleaner.py`. Si la aplicación se instala en una ruta de solo lectura para usuarios estándar (como `C:\Program Files`), guardar cambios de configuración requerirá ejecutar la aplicación como Administrador o usar una instalación por usuario (opción predeterminada del instalador).
