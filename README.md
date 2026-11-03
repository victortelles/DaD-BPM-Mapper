<div align="center">

**[🇪🇸 Leer en Español](README.md)** | **[🇺🇸 Read in English](README.en.md)**

  <img src="Logo.PNG" alt="Dead as Disco – BPM & BeatSync Studio v2" width="320"/>
  <h1>Dead as Disco — BPM & BeatSync Studio (v2)</h1>
  <p><b>Estudio web interactivo para sincronización rítmica de precisión (BeatWarping) y empaquetado nativo de canciones personalizadas</b></p>
</div>

---

## 🎯 Propósito y Solución (Lead with the Outcome)

**Resultado directo:** Convierte cualquier pista musical (`.mp3`, `.wav`, `.ogg`, `.flac`) en un paquete de mod nativo para **Dead as Disco** (`<SongName>/audio.ogg` a **44.1 kHz** + `<SongName>/Meta.json` de **16 campos**), listo para descomprimir en `%localappdata%\Pagoda\Saved\ImportedSongs\`.

### ¿Por qué existe esta herramienta?
Cuando importas canciones con cambios de ritmo, introducciones asimétricas o percusiones síncopas directamente en **Dead as Disco**, el detector interno del juego suele asumir un BPM estático o desfasar el primer golpe (`beatOffset`), provocando que los ataques y esquives pierdan sincronía con la música.

**Dead as Disco — BPM & BeatSync Studio v2** resuelve esta limitación mediante:
1. **Análisis DSP No Destructivo (Librosa)**: Detecta el `tempo` raíz, el `beatOffset` exacto en milisegundos y cambios dinámicos de velocidad (`customTempoSections`).
2. **Alineación Magnética a Picos Acústicos**: Permite anclar banderas de tempo directamente a los transitorios reales (golpes de bombo/caja) y recalcular BPMs automáticamente poniendo `BPM = 0`.
3. **Empaquetado Nativo sin Desfase**: Transcodifica una copia limpia a `audio.ogg` (**44,100 Hz**) eliminando el *encoder padding* del MP3 y preservando intacto el hash MD5 del archivo original (`originalAudioFileHash`).

---

## ⚡ Ruta Rápida (Quick Path)

1. **Subir Pista (Paso 1)**: Carga tu archivo de audio validado por el firewall binario de cabeceras mágicas.
2. **Sincronizar Ritmo (Paso 2)**: Verifica el golpe inicial (`beatOffset`) y las secciones de tempo en el reproductor en vivo con metrónomo y cuadrícula de beats.
3. **Exportar Mod (Paso 3)**: Descarga el archivo `<SongName>.zip` (o expórtalo directamente) a `%localappdata%\Pagoda\Saved\ImportedSongs\`.

---

## 🖼️ Guía Visual Paso a Paso

### Paso 1: Subir Audio Validado por Firewall Binario
Sube tu pista musical (`.mp3`, `.wav`, `.ogg`, `.flac`) y, opcionalmente, un archivo `Meta.json` previo. El motor verifica la firma binaria real (*magic bytes*) antes de decodificar la señal y calcula el hash MD5 original sin alterar tus archivos.

<div align="center">
  <img src="assets/guide/step1_upload.png" alt="Paso 1: Subir Audio validado por Firewall Binario" width="850"/>
</div>

### Paso 2: Verificar y Sincronizar con Picos Acústicos y Cuadrícula de Beats
Reproduce la canción a 60 FPS sobre la forma de onda interactiva con zoom de hasta `25x`, metrónomo WebAudio y rejilla visual de pulsos. Ajusta `beatOffset` (ms), `startSongOffset`/`endSongOffset` (s), navega entre secciones (`◀ Anterior` / `Siguiente ▶`) o escribe `BPM = 0` para que el motor calcule el tempo exacto entre picos.

<div align="center">
  <img src="assets/guide/step2_sync.png" alt="Paso 2: Verificar y Sincronizar con Picos Acústicos y Cuadrícula de Beats" width="850"/>
</div>

### Paso 3: Generar y Descargar `.ZIP` con `audio.ogg` + `Meta.json`
Revisa la auditoría del paquete (calidad de ajuste `fitQuality`, secciones detectadas y vista previa de `Meta.json`). Genera el paquete `.zip` con el audio transcodificado a `audio.ogg` (44.1 kHz) o expórtalo directamente a la carpeta local del juego.

<div align="center">
  <img src="assets/guide/step3_export.png" alt="Paso 3: Generar y Descargar .ZIP con audio.ogg + Meta.json" width="850"/>
</div>

### Paso 4: Descomprimir en `ImportedSongs` y Jugar
Extrae la carpeta `<SongName>/` dentro de `%localappdata%\Pagoda\Saved\ImportedSongs\`. Inicia **Dead as Disco** y selecciona tu pista perfectamente sincronizada.

<div align="center">
  <img src="assets/guide/step4_install_game.png" alt="Paso 4: Descomprimir en ImportedSongs y validar en el juego" width="850"/>
</div>

---

## 📄 Formato Oficial de Salida (`Meta.json` + `audio.ogg`)

Cada paquete exportado genera la estructura exacta requerida por Unreal Engine / Pagoda:

```text
%localappdata%\Pagoda\Saved\ImportedSongs\
└── <SongName>\
    ├── audio.ogg   # Audio Ogg Vorbis a 44,100 Hz (sin padding de compresión)
    └── Meta.json   # Contrato nativo de 16 campos indentado con tabulaciones (\t)
```

### Contrato de 16 Campos de `Meta.json`

| # | Campo | Tipo | Descripción |
| :- | :--- | :--- | :--- |
| 1 | `version` | `int` | Versión del esquema de metadatos de Pagoda (`1`). |
| 2 | `uniqueId` | `int` | Identificador numérico único de 32 bits sin signo. |
| 3 | `songName` | `str` | Título visible de la canción dentro del juego. |
| 4 | `performedBy` | `list[str]` | Lista de intérpretes o artistas. |
| 5 | `writtenBy` | `list[str]` | Lista de compositores o autores. |
| 6 | `seed` | `int` | Semilla determinista de 32 bits para generación procedural. |
| 7 | `tempo` | `float \| int` | BPM base de la canción (sección inicial desde `0.0s`). |
| 8 | `customTempoSections` | `list[dict]` | Cambios dinámicos de tempo (`{"tempo", "startAbsoluteTime"}`). |
| 9 | `beatOffset` | `int` | Desfase del primer pulso rítmico en **milisegundos** (`ms`). |
| 10 | `startSongOffset` | `float` | Tiempo de inicio de reproducción efectiva en **segundos** (`s`). |
| 11 | `endSongOffset` | `float` | Tiempo de corte final en **segundos** (`s`). |
| 12 | `uEAssetName` | `str` | Nombre del recurso interno para Unreal Engine. |
| 13 | `originalAudioFileHash` | `str` | Hash **MD5** hexadecimal (32 caracteres) de los bytes originales. |
| 14 | `originalAudioFilePath` | `str` | Ruta de referencia del archivo de audio de origen. |
| 15 | `analyseResult` | `dict` | Diagnóstico (`bAnalyseSuccessful`, `bFoundTempo`, `bFoundOffset`, `tempo`, `beatOffset`, `fitQuality`, `errorCode`). |
| 16 | `beatTracks` | `list` | Pistas de eventos coreográficos (reservado como `[]`). |

### Ejemplo Real de `Meta.json`

```json
{
	"version": 1,
	"uniqueId": 27605225,
	"songName": "Neon Rave Act I",
	"performedBy": [],
	"writtenBy": [],
	"seed": 2196372576,
	"tempo": 95,
	"customTempoSections": [
		{
			"tempo": 190,
			"startAbsoluteTime": 20.248838
		}
	],
	"beatOffset": 38,
	"startSongOffset": 0.85,
	"endSongOffset": 210.0,
	"uEAssetName": "Neon Rave Act I",
	"originalAudioFileHash": "84e43bfb431159bcf29ab6ab906a4147",
	"originalAudioFilePath": "D:/Music/Neon Rave Act I.mp3",
	"analyseResult": {
		"bAnalyseSuccessful": true,
		"bFoundTempo": true,
		"bFoundOffset": true,
		"tempo": 95,
		"beatOffset": 38,
		"fitQuality": 0.920423,
		"errorCode": {
			"code": 0,
			"messageKey": "None",
			"message": ""
		}
	},
	"beatTracks": []
}
```

---

## 🧱 Arquitectura Modular S.O.L.I.D (`< 400` Líneas por Archivo)

El repositorio aplica separación estricta de responsabilidades (**S.O.L.I.D**) y un límite arquitectónico automatizado donde **ningún archivo supera las 400 líneas de código** (`tests/test_architecture_limits.py`). Las capas de dominio (`models/`, `audio_analysis/`, `export/`) son 100% independientes de Streamlit.

```text
├── app.py                          # Orquestador ligero de navegación y estado (< 200 LOC)
├── models/
│   └── song_metadata.py            # Entidades de 16 campos Meta.json y puente legacy BPMSection
├── audio_analysis/
│   ├── security.py                 # Firewall binario de cabeceras mágicas + hash MD5
│   ├── dsp_peaks.py                # Carga DSP, envolvente, snapping a transitorios y cálculo Zero-BPM
│   ├── beat_detection.py           # Detección de tempo, beatOffset (ms) y fitQuality
│   ├── bpm_sections.py             # CRUD de secciones y fórmulas continuas de BeatWarping
│   ├── converter.py                # Transcodificador no destructivo a OGG 44.1 kHz (FFmpeg/SoundFile)
│   └── exceptions.py               # Jerarquía de excepciones de dominio y seguridad
├── export/
│   ├── package_builder.py          # Empaquetador ZIP (<SongName>/Meta.json + audio.ogg) y exportador local
│   └── exceptions.py               # Errores de E/S de exportación
├── ui/
│   ├── theme.py                    # Sistema de diseño Sky/Slate (:root CSS, Inter + JetBrains Mono)
│   ├── step_upload.py              # Paso 1 del Wizard: carga segura e importación de Meta.json
│   ├── step_sync.py                # Paso 2 del Wizard: sincronización en vivo y auto-calibración
│   ├── step_export.py              # Paso 3 del Wizard: vista previa de Meta.json y descarga ZIP
│   ├── live_waveform_player.py     # Puente del reproductor interactivo en vivo
│   ├── player_assets.py            # Plantilla HTML5 Canvas + WebAudio Metronome + Beat Grid
│   ├── flag_editor.py              # Editor interactivo de offsets y customTempoSections
│   ├── waveform_view.py            # Gráfica estática de respaldo en Matplotlib
│   ├── guide_view.py               # Vista integrada "Cómo Usarlo" con capturas anotadas
│   └── legal_view.py               # Vista de Políticas, Privacidad y Aviso Legal (DMCA)
└── tests/                          # Suite de pruebas unitarias, límite <400 LOC y flujo E2E
```

| Capa | Paquete | Responsabilidad Clave | Dependencia UI |
| :--- | :--- | :--- | :---: |
| **Dominio** | `models/` | Contratos tipados `SongMetadata`, `CustomTempoSection`, `AnalyseResult` y migración legacy. | Ninguna |
| **Seguridad y DSP** | `audio_analysis/` | Validación de magic bytes, MD5 intacto, detección de picos/BPM y conversión OGG 44.1 kHz. | Ninguna |
| **Empaquetado** | `export/` | Serialización `Meta.json` (16 campos) y construcción de paquetes `.zip` para Pagoda. | Ninguna |
| **Presentación** | `ui/` + `app.py` | Wizard minimalista de 3 pasos, tema Sky/Slate, Canvas 60 FPS y vistas de ayuda/legal. | Streamlit |

---

## 🛠️ Instalación, Ejecución Local y Pruebas

### 1. Prerrequisitos
- **Python 3.10+** (recomendado Python 3.12).
- **FFmpeg** instalado en el sistema (con respaldo automático vía `soundfile` / `libsndfile`):
  ```bash
  winget install Gyan.FFmpeg
  ```

### 2. Instalación y Ejecución
```bash
git clone https://github.com/victortelles/DaD-BPM-Mapper.git
cd DaD-BPM-Mapper
pip install -r requirements.txt
streamlit run app.py
```

### 3. Suite de Pruebas (Pytest + Auditoría Arquitectónica + E2E)
```bash
# Ejecutar toda la suite unitaria, de seguridad, arquitectura (<400 LOC) y E2E
pytest -q

# Ejecutar específicamente el gate arquitectónico y el flujo E2E v2
pytest tests/test_architecture_limits.py tests/test_e2e_workflow.py -v
```

### Lista de Verificación Rápida (Checklist)
- [x] Todos los archivos del repositorio cumplen estrictamente `< 400` líneas.
- [x] El firewall rechaza ejecutables (`MZ`) o scripts (`<script>`) renombrados como audio.
- [x] El archivo `.zip` exportado contiene `<SongName>/audio.ogg` (44.1 kHz) y `<SongName>/Meta.json` (16 campos).

---

## 🔒 Políticas de Seguridad, Privacidad y Aviso Legal (DMCA)

- **Firewall Binario de Subida**: Solo se aceptan extensiones `.mp3`, `.wav`, `.ogg` y `.flac` (entre `64 B` y `100 MB`) cuyas cabeceras binarias coincidan con firmas reales (`ID3`/MPEG sync, `RIFF`/`WAVE`, `OggS`, `fLaC`). Cualquier binario ejecutable o script camuflado es bloqueado antes de tocar el decodificador.
- **Procesamiento 100% Efímero y No Destructivo**: Los archivos de audio se procesan en memoria RAM o directorios temporales aislados. El archivo original jamás es modificado y su hash MD5 (`originalAudioFileHash`) se preserva íntegro.
- **Propiedad Intelectual y DMCA**: Este proyecto es una utilidad comunitaria de *modding* sin fines comerciales ni afiliación oficial con los creadores de **Dead as Disco** (*Pagoda*). El usuario es el único responsable de poseer los derechos o licencias de las pistas musicales que procese localmente para uso personal.
