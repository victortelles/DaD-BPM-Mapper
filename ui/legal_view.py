"""Legal policies, terms of use, and security disclosures for Dead as Disco BPM Mapper."""

from typing import List, Tuple

import streamlit as st

from ui.theme import render_micro_card

LEGAL_POLICIES: List[Tuple[str, str, str, List[str]]] = [
    (
        "1. Propiedad Intelectual y Derechos de Autor (DMCA)",
        "Cumplimiento de Derechos de Autor",
        "El usuario declara poseer los derechos o licencias de uso personal sobre cualquier pista subida. Se prohíbe la distribución no autorizada de material protegido.",
        [
            "Esta herramienta está diseñada exclusivamente para uso personal de modding local y pistas con licencia libre o propia.",
            "La aplicación no aloja, indexa ni redistribuye bibliotecas musicales con derechos de autor de terceros.",
            "Cualquier paquete `.zip` generado es responsabilidad exclusiva del usuario que realiza la conversión.",
        ],
    ),
    (
        "2. Seguridad y Mitigación de Archivos Maliciosos",
        "Firewall Binario Activo",
        "Todo archivo pasa por inspección estricta de firmas mágicas binarias (`ID3/MPEG`, `RIFF/WAVE`, `OggS`, `fLaC`). Cualquier ejecutable, script o payload camuflado es bloqueado de inmediato.",
        [
            "Verificación de cabeceras binarias antes de invocar cualquier decodificador de señal (`librosa` / `soundfile`).",
            "Rechazo inmediato de extensiones no autorizadas, archivos vacíos o cargas que superen el límite de seguridad.",
            "Cálculo de huella criptográfica MD5 (`originalAudioFileHash`) sobre los bytes originales sin mutar el archivo fuente.",
        ],
    ),
    (
        "3. Política de Privacidad de Datos (Cero Recopilación)",
        "Sin Almacenamiento en Bases de Datos",
        "La aplicación no recopila ni toma datos de los usuarios. Lo único que utiliza es el audio que proporciona para sincronizar los BPMs en memoria RAM, el cual no se almacena en ninguna base de datos ni servidor externo.",
        [
            "La aplicación no solicita ni registra nombres, correos, cuentas ni datos personales de los usuarios.",
            "Lo único que se procesa es el archivo de audio que proporcionas, exclusivamente en la memoria volátil (RAM) de la sesión para el cálculo de ritmos y BPMs.",
            "El audio no se almacena en ninguna base de datos, servicio en la nube ni disco externo permanente.",
            "Al cerrar la pestaña o reiniciar la sesión, todos los buffers de audio y metadatos se eliminan por completo.",
        ],
    ),
    (
        "4. Exención de Responsabilidad (Fan Modding Tool)",
        "Herramienta Comunitaria Independiente",
        "Proyecto independiente comunitario no afiliado oficialmente con los desarrolladores de *Dead as Disco* / Pagoda. El uso de mods es bajo responsabilidad del usuario.",
        [
            "*Dead as Disco* y *Pagoda* son marcas y propiedades de sus respectivos creadores y titulares de derechos.",
            "El software se proporciona «tal cual» (AS IS), sin garantías expresas o implícitas sobre cambios futuros en el motor del juego.",
            "Se recomienda respaldar tu carpeta `ImportedSongs` antes de sobrescribir configuraciones personalizadas.",
        ],
    ),
]


def render_legal_view() -> None:
    """Render the structured Legal Policies, Security Rules, and Disclaimer view."""
    render_micro_card(
        "Políticas, Reglas de Uso y Aviso Legal",
        "Normativa de derechos de autor (DMCA), seguridad de archivos, privacidad en memoria y aviso de modding comunitario.",
        "Marco Legal y Seguridad",
    )

    col_left, col_right = st.columns(2, gap="medium")
    for idx, (title, badge, summary, details) in enumerate(LEGAL_POLICIES):
        target_col = col_left if idx % 2 == 0 else col_right
        with target_col:
            with st.container(border=True):
                st.markdown(f'<span class="dad-badge">{badge}</span>', unsafe_allow_html=True)
                st.markdown(f"#### {title}")
                st.markdown(summary)
                with st.expander("Ver detalles y reglas aplicables", expanded=False):
                    for bullet in details:
                        st.markdown(f"- {bullet}")

    st.info(
        "**Nota de Conformidad:** Al subir un archivo y utilizar el asistente de sincronización, "
        "confirmas que cumples con estas reglas de uso personal y seguridad.",
    )
