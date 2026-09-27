# Dead as Disco – BPM Mapper & Song Importer

Herramienta web interactiva (desarrollada en **Python + Streamlit**) diseñada para convertir cualquier archivo musical (`.mp3`, `.wav`, `.ogg`) en un paquete de mod listo para el juego **Dead as Disco**, con detección automática de BPM dinámico (**BeatWarping**), editor de onda sonoro en vivo con zoom y playhead en tiempo real, ajuste manual de banderas de tempo y exportación automatizada (`.ogg` a 44.1 kHz + `.json`).

---

## 📌 Resumen del Proyecto

En canciones con ritmos complejos o tempos cambiantes (por ejemplo, transiciones de 70 BPM a 120 BPM), mapear cada pulso a mano resulta lento y propenso a desfases. Esta aplicación automatiza el análisis mediante procesamiento digital de señales (**Librosa**), calcula la progresión continua de tiempos y pulsos, y ofrece un entorno interactivo en vivo para refinar visualmente cada bandera antes de empaquetar el mod para el juego.

---

## ✨ Características Principales

- **Detección Automática de BeatWarping**: Escanea transitorios y fluctuaciones de tempo en el audio para proponer secciones de BPM continuas (`startTime`, `startBeat`, `bpm`).
- **Editor de Onda en Vivo (Live Waveform Player)**:
  - **Barra de reproducción (Playhead) en tiempo real**: Cursor vertical a 60 FPS con auto-desplazamiento continuo (`Follow`).
  - **Zoom de alta precisión**: Control deslizante de 1x a 25x y accesos rápidos (`Ajustar`, `5x`, `15x`) con scroll horizontal para sincronizar transitorios al milisegundo.
  - **Scrubbing interactivo**: Salto inmediato en la reproducción al hacer click o arrastrar el cursor sobre la onda.
  - **Banderas visuales integradas**: Marcadores verticales coloreados con etiquetas de BPM montados directamente sobre la onda interactiva.
  - **Controles de transporte completos**: Reproducir/Pausa (soporta barra espaciadora), Detener, saltos de $\pm 5$ segundos, selector de velocidad (0.5x a 1.5x) y botón `📋 Copiar Tiempo` al portapapeles.
- **Tabla de Edición de Banderas**:
  - Modificación de BPM y tiempos de inicio con recálculo matemático automático en cascada.
  - Protección de la bandera raíz obligatoria (`0.0s`).
  - Validación estricta de orden cronológico e invariantes de tempo.
- **Transcodificación Sample-Accurate (FFmpeg)**:
  - Conversión a formato Ogg Vorbis a **44.1 kHz**.
  - Evita el *encoder padding* o micro-silencio inicial característico del MP3 que rompe la sincronía en juegos rítmicos.
- **Doble Modo de Exportación**:
  - Descarga del paquete comprimido en `.zip`.
  - Exportación directa a la carpeta de mods del juego: `%localappdata%\Pagoda\Saved\ImportedSongs\`.

---

## 🚀 Requisitos e Instalación

### 1. Prerrequisitos
- **Python 3.10 o superior** (probado en Python 3.12).
- **FFmpeg** (requerido para la conversión de audio a OGG 44.1 kHz):
  - **Windows**: Instalar mediante WinGet:
    ```bash
    winget install Gyan.FFmpeg
    ```
    *O descargar desde [ffmpeg.org](https://ffmpeg.org/download.html) y agregar su carpeta `bin` al PATH.*

### 2. Instalación de Dependencias
Clona el repositorio e instala las librerías necesarias:
```bash
git clone https://github.com/victortelles/DaD-BPM-Mapper.git
cd DaD-BPM-Mapper
pip install -r requirements.txt
```

---

## 📖 Guía de Uso Paso a Paso

### Paso 1: Subir y Analizar la Pista
1. Ejecuta la aplicación en tu terminal:
   ```bash
   streamlit run app.py
   ```
2. Se abrirá la interfaz web en tu navegador (`http://localhost:8501`).
3. En la pestaña **`1. 📂 Subir y Analizar`**, arrastra o selecciona tu archivo de música (`.mp3`, `.wav` o `.ogg`).
4. El motor analizará automáticamente el ritmo, detectará los transitorios y generará la propuesta inicial de banderas de BPM.

### Paso 2: Revisión y Ajuste en Vivo
1. Pasa a la pestaña **`2. 🚩 Editor de Banderas y Vista Previa`**.
2. **Escucha y navega**: Presiona **▶ Reproducir** (o la barra espaciadora). Observa la barra blanca desplazándose en tiempo real sobre la forma de onda.
3. **Usa el Zoom**: Amplía la vista con el deslizador de zoom (por ejemplo a `5x` o `15x`) para observar con claridad el pico exacto del bombo (*kick*) o caja (*snare*).
4. **Captura el tiempo**: Haz pausa en el momento exacto y haz click en `📋 Copiar Tiempo`.
5. **Ajusta o añade banderas**:
   - Para **añadir**: Despliega `➕ Agregar Nueva Bandera de Tempo`, pega el segundo y define el nuevo BPM.
   - Para **editar**: Modifica directamente los valores en la tabla interactiva inferior. Los beats subsiguientes se recalcularán automáticamente.
   - Para **eliminar**: Despliega `🗑️ Eliminar Bandera de Tempo` y selecciona la bandera que desees descartar.

### Paso 3: Exportar el Mod
1. Pasa a la pestaña **`3. 📦 Exportar Mod`**.
2. Ingresa o ajusta el nombre del mod (el sistema sanitiza caracteres no válidos para el sistema de archivos).
3. Selecciona tu método preferido de guardado:
   - **Descargar ZIP**: Haz click en `Generar ZIP del Mod` y luego en `⬇️ Descargar`. Puedes extraerlo manualmente en cualquier momento.
   - **Exportación Directa**: Haz click en `Exportar Directamente a ImportedSongs`. El sistema convertirá el audio, generará el JSON y copiará la carpeta directamente en `%localappdata%\Pagoda\Saved\ImportedSongs\` de tu equipo.
4. ¡Abre **Dead as Disco** y tu canción estará lista para jugarse!

---

## 🧮 Fórmula BeatWarping

El juego calcula el índice de pulso acumulado $B_i$ en el segundo $T_i$ utilizando el tempo de la sección inmediatamente anterior $BPM_{i-1}$:

$$B_0 = 0.0$$
$$B_i = B_{i-1} + (T_i - T_{i-1}) \cdot \frac{BPM_{i-1}}{60.0}$$

---

## 📂 Estructura del Código

```text
├── app.py                      # Punto de entrada de la interfaz Streamlit
├── audio_analysis/             # Motor de análisis acústico y transcodificación
│   ├── beat_detection.py       # Detección de tempo y envolvente de onda
│   ├── bpm_sections.py         # Algoritmos y fórmulas de BeatWarping
│   ├── converter.py            # Transcodificador FFmpeg (44.1 kHz OGG)
│   └── exceptions.py           # Jerarquía de excepciones de dominio
├── ui/                         # Componentes visuales desacoplados
│   ├── live_waveform_player.py # Editor interactivo en vivo con Canvas y Audio
│   ├── flag_editor.py          # Tabla y formularios de edición de banderas
│   ├── player.py               # Reproductor de audio embebido
│   └── waveform_view.py        # Gráfica estática de exportación (Matplotlib)
├── export/                     # Empaquetado y metadatos
│   ├── package_builder.py      # Generador de JSON y archivador ZIP
│   └── exceptions.py           # Manejo de errores de exportación / E/S
├── models/                     # Contratos de datos
│   └── song_metadata.py        # Clases BPMSection, SongMetadata y ExportResult
├── tests/                      # Suite de pruebas automatizadas con Pytest
└── requirements.txt            # Dependencias del proyecto
```

---

## 🧪 Pruebas Automatizadas

Para ejecutar los 22 tests unitarios e integrales:
```bash
pytest -v
```
