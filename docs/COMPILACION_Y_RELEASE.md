# 📦 Compilación, Empaquetado y Releases — PyClean Pro v2.6.0

Esta guía documenta cómo compilar los ejecutables e instaladores de **PyClean Pro v2.6.0** en Windows y macOS, cómo funciona el flujo de CI/CD multiplataforma en GitHub Actions, cómo configurar la firma de código Authenticode opcional y cómo verificar la integridad de los artefactos publicados.

> **Volver al inicio:** [`README.md`](../README.md) · **Arquitectura:** [`ARQUITECTURA.md`](ARQUITECTURA.md) · **Historial de Cambios:** [`CHANGELOG.md`](../CHANGELOG.md)

---

## 1. Requisitos Previos para Compilación Local

- **Python 3.10+** (**Python 3.11** es la versión utilizada en CI).
- Dependencias de ejecución y compilación instaladas:
  ```bash
  pip install -r requirements-dev.txt
  ```
  Esto instala `pywebview>=4.0.0`, `psutil>=5.9.0`, `cryptography>=42.0.0`, `pytest>=7.0.0` y `pyinstaller>=6.0.0`.
- **Adicional en Windows (solo para `PyCleanPro-Setup.exe`):** [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe` instalado en `PATH`, `Program Files`, Chocolatey o `%LOCALAPPDATA%`).
- **Adicional en macOS:** Herramienta nativa `hdiutil` (incluida en macOS).

Antes de empaquetar, se recomienda ejecutar la suite de 21 pruebas unitarias:
```bash
pytest tests/ -v
```

---

## 2. Compilación en Windows

### 2.1 Ejecutable Portable (`dist/PyCleanPro.exe`)
El script [`build_exe.py`](../build_exe.py) invoca PyInstaller en modo `--onefile --windowed`, empaquetando la carpeta `web/`, el ícono [`assets/pyclean_icon.ico`](../assets/pyclean_icon.ico) y los metadatos PE de [`version_info.txt`](../version_info.txt):

```powershell
python build_exe.py
```

Parámetros principales aplicados por `build_exe.py`:
- `--name=PyCleanPro --onefile --windowed --clean`
- `--add-data=web;web`
- `--icon=assets/pyclean_icon.ico`
- `--version-file=version_info.txt`

### 2.2 Instalador Oficial (`dist/PyCleanPro-Setup.exe`)
El script [`build_installer.py`](../build_installer.py) compila [`installer.iss`](../installer.iss) usando Inno Setup 6 (`ISCC.exe`). Si `dist/PyCleanPro.exe` aún no existe, ejecuta `build_exe.py` automáticamente antes de crear el instalador:

```powershell
python build_installer.py
```

Características del instalador (`installer.iss`):
- Versión declarada: `MyAppVersion "2.6.0"`.
- Compresión `LZMA2` (`ultra64`), interfaz de asistente en **español e inglés**.
- Instalación por usuario por defecto (`PrivilegesRequired=lowest`) con opción interactiva de elevación para todos los usuarios.
- Incluye `PyCleanPro.exe` y `README.md`, crea accesos directos en Menú Inicio / Escritorio y registra la desinstalación en Windows.

### 2.3 Menú Interactivo Windows (`build.bat`)
Como alternativa práctica en Windows, puedes ejecutar [`build.bat`](../build.bat) para elegir desde un menú interactivo entre compilar el ejecutable portable, el instalador o ambos.

### 2.4 Metadatos de Versión PE (`version_info.txt`)
[`version_info.txt`](../version_info.txt) incrusta la información de versión de archivo y producto (`2.6.0.0`, `CompanyName: chemkes1999`) en las propiedades del binario `PyCleanPro.exe`. Al preparar un nuevo release, actualiza la versión tanto en `version_info.txt` como en `installer.iss`.

---

## 3. Compilación en macOS (`.app` y `.dmg`)

El script [`build_macos.py`](../build_macos.py) debe ejecutarse en **macOS** y genera tanto el bundle de aplicación como el instalador `.dmg`:

```bash
python3 build_macos.py
```

El proceso realiza dos pasos:
1. **Empaquetado `.app` con PyInstaller:**
   - `--name=PyCleanPro --onedir --windowed --noconfirm --clean`
   - `--add-data=web:web`
   - `--osx-bundle-identifier=com.chemkes1999.pycleanpro`
   - `--icon=assets/pyclean_icon.icns`
   - Genera `dist/PyCleanPro.app`.
2. **Creación de imagen `.dmg` con `hdiutil`:**
   - Prepara una carpeta temporal con `PyCleanPro.app` y un enlace simbólico a `/Applications`.
   - Ejecuta `hdiutil create` en formato comprimido `UDZO`, produciendo `dist/PyCleanPro-macOS.dmg`.

---

## 4. Pipeline CI/CD Multi-OS (GitHub Actions)

El flujo [`.github/workflows/build-release.yml`](../.github/workflows/build-release.yml) automatiza pruebas, compilación y publicación en GitHub Releases.

### Disparadores
- **Push de etiqueta `v*`** (por ejemplo `git tag v2.6.0 && git push origin v2.6.0`): compila todos los artefactos y publica automáticamente el GitHub Release.
- **Manual (`workflow_dispatch`)**: ejecuta las pruebas y genera los artefactos descargables desde la pestaña *Actions* sin publicar release.

### Trabajos (*Jobs*) del Pipeline

| Job | Runner | Pasos Principales | Artefactos |
|---|---|---|---|
| `build-windows` | `windows-latest` (Python 3.11) | Instala `requirements-dev.txt` → ejecuta `pytest tests/ -v` → instala Inno Setup (`choco install innosetup`) → ejecuta `python build_exe.py` → firma opcional con `signtool.exe` → ejecuta `python build_installer.py` → firma opcional del Setup. | `PyCleanPro.exe`, `PyCleanPro-Setup.exe` |
| `build-macos` | `macos-latest` (Python 3.11) | Instala `requirements-dev.txt` → ejecuta `pytest tests/ -v` → ejecuta `python build_macos.py`. | `PyCleanPro-macOS.dmg` |
| `release` | `ubuntu-latest` (solo en tag `v*`) | Descarga los artefactos de Windows y macOS → genera `SHA256SUMS.txt` con los 3 binarios → publica el Release con `softprops/action-gh-release@v2`. | `PyCleanPro.exe`, `PyCleanPro-Setup.exe`, `PyCleanPro-macOS.dmg`, `SHA256SUMS.txt` |

---

## 5. Firma de Código Authenticode Opcional (Windows)

El job `build-windows` soporta firma digital **Authenticode** automática usando `signtool.exe` (SHA-256 con sellado de tiempo de DigiCert) si se configuran ambos secretos en el repositorio de GitHub (*Settings → Secrets and variables → Actions*):

| Secreto de GitHub | Descripción |
|---|---|
| `CODE_SIGN_CERT_BASE64` | Certificado de firma de código `.pfx` codificado en Base64. |
| `CODE_SIGN_CERT_PASSWORD` | Contraseña del archivo `.pfx`. |

Si estos secretos no están definidos, la compilación continúa normalmente y produce binarios sin firmar.

---

## 6. Verificación de Integridad (`SHA256SUMS.txt`) y Avisos del SO

### Verificar hashes SHA-256
Cada release oficial incluye `SHA256SUMS.txt`. Verifica siempre tus descargas antes de ejecutarlas:

**Windows (PowerShell):**
```powershell
Get-FileHash .\PyCleanPro.exe -Algorithm SHA256
Get-FileHash .\PyCleanPro-Setup.exe -Algorithm SHA256
```

**macOS / Linux:**
```bash
shasum -a 256 PyCleanPro-macOS.dmg
```

Compara el resultado en hexadecimal con la línea correspondiente en `SHA256SUMS.txt`.

### Avisos de Windows SmartScreen y macOS Gatekeeper
- **Windows SmartScreen:** Cuando un release se compila sin certificado Authenticode comercial (o con un certificado recién emitido), Windows puede mostrar *"Windows protegió su PC"*. Tras verificar el `SHA256SUMS.txt`, pulsa **Más información → Ejecutar de todas formas**.
- **macOS Gatekeeper:** El pipeline actual de macOS no incluye firma de desarrollador ni notarización de Apple. Al abrir `PyCleanPro.app` por primera vez, haz **clic derecho sobre la aplicación → Abrir** y confirma **Abrir** en el cuadro de diálogo.
