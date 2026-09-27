# Dead as Disco – BPM Mapper & Song Importer

Herramienta web (Python + Streamlit) para convertir un archivo de audio (`.mp3`) en un paquete de mod listo para **Dead as Disco**, con detección automática de BPM variable (BeatWarping), ajuste manual mediante banderas y exportación automatizada (`.ogg` + `.json`).

---

## 1. Propósito del Proyecto

Permitir a creadores de contenido y jugadores sincronizar canciones con ritmos complejos (BPM variable) dentro del juego, pasando de un audio crudo a un paquete de mod completamente estructurado en pocos clics, sin necesidad de mapear el ritmo manualmente desde cero.

---

## 2. Formatos y Compatibilidad de Archivos

| Elemento | Detalle |
|---|---|
| **Entrada** | Archivo musical subido por el usuario (comúnmente `.mp3`) |
| **Salida del juego** | El juego lee la música y su sincronización desde `%localappdata%\Pagoda\Saved\ImportedSongs\` |
| **Archivo de sincronización** | `.json` con técnica **BeatWarping**: arreglo `bpmSections` con tiempos y pulsos específicos |
| **Audio final recomendado** | `.ogg` a 44.1kHz (evita el *encoder padding*/micro-silencio inicial que introduce el MP3 y que rompe la sincronización milimétrica) |
| **Conversión** | Automática, vía `ffmpeg`, de `.mp3` a `.ogg` |

---

## 3. Arquitectura del Software

- **Frontend/UI:** Python + Streamlit — interfaz web interactiva, rápida y ligera.
- **Backend de análisis de audio:** LibROSA o Aubio (beat tracking / detección de tempo dinámico).
- **Conversión de audio:** `ffmpeg` (mp3 → ogg 44.1kHz).
- **Principio de diseño:** Componentización — separar claramente:
  - `audio_analysis/` (lógica de detección de BPM, segmentación, cálculo de beats)
  - `ui/` (componentes visuales de Streamlit)
  - `export/` (empaquetado del `.ogg` + `.json` + carpeta final)

### Estructura de carpetas sugerida

```
dead-as-disco-bpm-mapper/
├── app.py                  # Entry point de Streamlit
├── audio_analysis/
│   ├── beat_detection.py   # Detección de BPM y transitorios (LibROSA/Aubio)
│   ├── bpm_sections.py     # Cálculo de bpmSections (segundo → beat)
│   └── converter.py        # Conversión mp3 → ogg vía ffmpeg
├── ui/
│   ├── waveform_view.py    # Visualización de la onda + marcadores
│   ├── flag_editor.py      # Editor manual de banderas/flags de BPM
│   └── player.py           # Reproductor de audio integrado (preview)
├── export/
│   └── package_builder.py  # Genera carpeta final (.ogg + .json)
├── models/
│   └── song_metadata.py    # Esquema de datos del JSON (BeatWarping)
├── requirements.txt
└── README.md
```

---

## 4. Funcionalidades Clave de la Interfaz

### 4.1 Análisis Automático
- El usuario sube el `.mp3`.
- El backend (LibROSA/Aubio) escanea el audio y detecta cambios de ritmo (ej. de 70 BPM a 120 BPM) mediante beat tracking dinámico.
- Se genera un mapeo inicial de `bpmSections` (propuesta automática, no definitiva).

### 4.2 Preview y Ajuste Manual
- Reproductor de audio integrado.
- Visualización de la forma de onda (waveform) con línea de tiempo.
- Marcadores/banderas (*flags*) sobre la waveform indicando cada cambio de BPM detectado.
- Tabla editable de secciones con columnas: `tiempo (s)`, `beat inicial`, `BPM`.
- El usuario puede:
  - Mover un marcador existente.
  - Agregar una bandera nueva manualmente.
  - Eliminar una bandera mal detectada.
  - Escuchar en preview el resultado antes de exportar.

### 4.3 Exportación Automatizada
- Conversión automática `.mp3` → `.ogg` (44.1kHz) vía `ffmpeg`.
- Generación del `.json` con el arreglo `bpmSections` estructurado según el formato BeatWarping del juego.
- Empaquetado de ambos archivos en una carpeta lista para copiar/arrastrar a `ImportedSongs\`.
- Botón de descarga (`.zip` o carpeta) al finalizar el flujo.

---

## 5. Lógica de Cálculo de Marcadores (BeatWarping)

1. **Detección de transitorios:** LibROSA/Aubio devuelve una lista de tiempos (segundos o ms) donde ocurren los golpes (*beat tracking*).
2. **Segmentación por cambio de tempo:** se identifica el segundo exacto donde el tempo local cambia de forma drástica (ej. 70 → 120 BPM).
3. **Conversión tiempo → beat:** para cada sección, se calcula a qué número de pulso (beat) equivale ese segundo, contando desde el inicio de la canción y respetando el BPM de la sección anterior.
4. **Escritura del nodo:** cada sección se agrega al arreglo `bpmSections` del `.json`, con al menos:
   - tiempo de inicio de la sección (segundos)
   - beat inicial correspondiente
   - valor de BPM de esa sección

### Ejemplo conceptual de estructura JSON (a validar contra el formato real del juego)

```json
{
  "songName": "nombre_de_la_cancion",
  "audioFile": "nombre_de_la_cancion.ogg",
  "bpmSections": [
    { "startTime": 0.0,  "startBeat": 0,   "bpm": 70 },
    { "startTime": 42.5, "startBeat": 165, "bpm": 120 }
  ]
}
```

> ⚠️ Este esquema debe validarse/ajustarse contra archivos `.json` reales exportados por el juego para garantizar compatibilidad exacta de nombres de campos.

---

## 6. Librerías y Herramientas Sugeridas

| Función | Librería/Herramienta |
|---|---|
| Interfaz web | `streamlit` |
| Beat tracking / análisis de tempo | `librosa` (o `aubio` como alternativa) |
| Manipulación numérica | `numpy` |
| Conversión y manejo de audio | `ffmpeg` (vía `subprocess` o `ffmpeg-python`) |
| Visualización de waveform | `librosa.display` + `matplotlib`, o componente custom en Streamlit |
| Reproductor de audio embebido | `st.audio` (nativo de Streamlit) |
| Empaquetado de salida | `zipfile` / `shutil` (librerías estándar de Python) |

---

## 7. Flujo de Usuario (User Flow)

1. Usuario abre la app y sube su archivo `.mp3`.
2. La app lo procesa y muestra la waveform con el BPM sugerido y las banderas detectadas.
3. Usuario reproduce el preview y revisa si los cambios de ritmo coinciden con la música.
4. Usuario ajusta manualmente cualquier bandera incorrecta (mover, borrar, agregar).
5. Usuario confirma y presiona "Exportar".
6. La app convierte el audio a `.ogg`, genera el `.json` y empaqueta ambos en una carpeta/zip descargable.
7. Usuario descarga y arrastra el contenido a `%localappdata%\Pagoda\Saved\ImportedSongs\`.

---

## 8. Consideraciones Técnicas / Riesgos

- **Precisión del beat tracking:** los algoritmos de detección automática pueden fallar en canciones con ritmos ambiguos o cambios muy sutiles de BPM — de ahí la importancia crítica del editor manual.
- **Offset de audio:** validar que la conversión a `.ogg` no introduza su propio padding; comparar waveform antes/después de la conversión.
- **Validación del formato JSON real del juego:** antes de finalizar el `package_builder.py`, confirmar la estructura exacta esperada por Dead as Disco (nombres de campos, unidades de tiempo, orden del arreglo).
- **Rendimiento:** archivos largos (>5 min) pueden tardar en analizarse; considerar mostrar un spinner/progreso en Streamlit.

---

## 9. Próximos Pasos

- [ ] Confirmar estructura exacta del `.json` de BeatWarping (ingeniería inversa sobre un archivo válido del juego).
- [ ] Prototipo de detección de BPM con LibROSA sobre canciones de prueba.
- [ ] Diseño del componente de waveform + editor de flags en Streamlit.
- [ ] Implementar conversión `ffmpeg` mp3 → ogg.
- [ ] Implementar exportación y empaquetado final.
- [ ] Pruebas end-to-end importando el resultado directamente en el juego.