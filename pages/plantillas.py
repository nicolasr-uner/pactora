import io
import difflib
import streamlit as st

from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Biblioteca de Plantillas")
st.caption("Accede, previsualiza y compara las plantillas contractuales estándar de Pactora.")

# ─── Paleta Unergy ─────────────────────────────────────────────────────────────
TIPO_COLOR = {
    "PPA":   "#4CAF50",
    "EPC":   "#2196F3",
    "O&M":   "#FF9800",
    "Legal": "#9C27B0",
    "SHA":   "#E91E63",
    "NDA":   "#9C27B0",
    "Otro":  "#607D8B",
}

# ─── Plantillas estáticas (catálogo base) ──────────────────────────────────────
PLANTILLAS_ESTATICAS = [
    {
        "nombre": "PPA_Standard_V2.docx",
        "tipo": "PPA",
        "version": "v2.1",
        "descripcion": "Contrato estándar de Compra de Energía (Power Purchase Agreement). "
                       "Incluye cláusulas de capacidad, precio, despacho y penalidades.",
        "campos": {
            "EMPRESA_GENERADORA": "Vendedor",
            "EMPRESA_COMPRADORA": "Comprador",
            "AÑOS_PLAZO": "Plazo (años)",
            "PRECIO_KWH": "Precio COP/kWh",
            "CAPACIDAD_MW": "Capacidad (MW)",
            "PCT_PENALIDAD": "% Penalidad",
            "DIAS_PREAVISO": "Días preaviso terminación",
        },
        "texto": """CONTRATO DE COMPRA DE ENERGÍA (PPA)

PARTES:
- Vendedor: [EMPRESA_GENERADORA]
- Comprador: [EMPRESA_COMPRADORA]

OBJETO: El Vendedor se obliga a generar y entregar energía eléctrica al Comprador bajo las condiciones establecidas.

PLAZO: El presente contrato tendrá una duración de [AÑOS_PLAZO] años contados desde la Fecha de Inicio.

PRECIO DE ENERGÍA: El precio aplicable será de [PRECIO_KWH] COP/kWh, indexado anualmente según el IPC.

CAPACIDAD CONTRATADA: [CAPACIDAD_MW] MW en condiciones estándar de despacho.

PENALIDADES: En caso de incumplimiento en la entrega, se aplicará una penalidad del [PCT_PENALIDAD]% sobre el valor mensual incumplido.

FUERZA MAYOR: Ninguna de las partes será responsable por el incumplimiento de sus obligaciones causado por eventos de fuerza mayor o caso fortuito.

TERMINACIÓN: Cualquiera de las partes podrá terminar el contrato con [DIAS_PREAVISO] días de preaviso en caso de incumplimiento material no subsanado.

CONFIDENCIALIDAD: Las partes se obligan a mantener la confidencialidad de los términos del presente contrato.
""",
    },
    {
        "nombre": "EPC_Contrato_Base.docx",
        "tipo": "EPC",
        "version": "v1.3",
        "descripcion": "Contrato de Ingeniería, Procura y Construcción. "
                       "Cubre diseño, adquisición de equipos, construcción y puesta en marcha.",
        "campos": {
            "EMPRESA_DUEÑA": "Contratante",
            "EMPRESA_CONSTRUCTORA": "Contratista EPC",
            "CAPACIDAD_MW": "Capacidad (MW)",
            "PRECIO_TOTAL_USD": "Precio total (USD)",
            "MESES_EJECUCION": "Plazo ejecución (meses)",
            "AÑOS_GARANTIA": "Años de garantía",
            "PCT_PENALIDAD_DIARIA": "% Penalidad diaria por mora",
            "PCT_TOPE_PENALIDAD": "% Tope penalidad",
            "PCT_RETENCION": "% Retención por factura",
        },
        "texto": """CONTRATO EPC — INGENIERÍA, PROCURA Y CONSTRUCCIÓN

PARTES:
- Contratante: [EMPRESA_DUEÑA]
- Contratista EPC: [EMPRESA_CONSTRUCTORA]

OBJETO: El Contratista se obliga a ejecutar, por su cuenta y riesgo, el proyecto de construcción del parque solar fotovoltaico de [CAPACIDAD_MW] MW.

ALCANCE DEL TRABAJO: Diseño, ingeniería de detalle, suministro de equipos, construcción civil, instalación electromecánica y puesta en marcha.

PRECIO TOTAL: USD [PRECIO_TOTAL_USD] precio fijo llave en mano.

PLAZO DE EJECUCIÓN: [MESES_EJECUCION] meses contados desde la firma del contrato.

GARANTÍAS: El Contratista otorgará garantía de buen funcionamiento por [AÑOS_GARANTIA] años.

PENALIDADES POR MORA: Por cada día de retraso en la entrega, se aplicará una penalidad del [PCT_PENALIDAD_DIARIA]% del valor total del contrato, con un tope del [PCT_TOPE_PENALIDAD]%.

RETENCIONES: Se retendrá el [PCT_RETENCION]% de cada factura hasta la recepción definitiva de las obras.

SEGUROS: El Contratista deberá mantener vigentes seguros de responsabilidad civil, todo riesgo construcción y de accidentes de trabajo.
""",
    },
    {
        "nombre": "OyM_Marco_General.docx",
        "tipo": "O&M",
        "version": "v1.0",
        "descripcion": "Contrato de Operación y Mantenimiento para plantas de generación. "
                       "Define niveles de servicio, disponibilidad y reportes.",
        "campos": {
            "EMPRESA_PROPIETARIA": "Propietario",
            "EMPRESA_OPERADORA": "Operador",
            "CAPACIDAD_MW": "Capacidad (MW)",
            "PCT_DISPONIBILIDAD": "% Disponibilidad garantizada",
            "TARIFA_MENSUAL_USD": "Tarifa mensual (USD)",
            "PCT_PENALIDAD_OM": "% Penalidad por punto de disponibilidad",
            "DIA_REPORTE": "Día de entrega de informes",
            "AÑOS_DURACION": "Duración (años)",
            "DIAS_PREAVISO": "Días preaviso renovación",
        },
        "texto": """CONTRATO DE OPERACIÓN Y MANTENIMIENTO (O&M)

PARTES:
- Propietario: [EMPRESA_PROPIETARIA]
- Operador: [EMPRESA_OPERADORA]

OBJETO: El Operador prestará los servicios de operación y mantenimiento de la planta de generación solar de [CAPACIDAD_MW] MW.

DISPONIBILIDAD GARANTIZADA: El Operador garantiza una disponibilidad mínima del [PCT_DISPONIBILIDAD]% anual de la planta.

SERVICIOS INCLUIDOS:
- Operación diaria de la planta
- Mantenimiento preventivo y correctivo
- Reporte mensual de generación
- Gestión de garantías de equipos

REMUNERACIÓN: Tarifa fija mensual de USD [TARIFA_MENSUAL_USD] más variable según generación real.

PENALIDADES: Por cada punto porcentual de disponibilidad por debajo del [PCT_DISPONIBILIDAD]%, se aplicará una penalidad del [PCT_PENALIDAD_OM]% de la tarifa mensual.

INFORMES: El Operador entregará informes mensuales de generación, disponibilidad e incidencias antes del día [DIA_REPORTE] de cada mes.

DURACIÓN: [AÑOS_DURACION] años renovables automáticamente por períodos iguales salvo aviso contrario con [DIAS_PREAVISO] días de anticipación.
""",
    },
    {
        "nombre": "NDA_Confidencialidad.docx",
        "tipo": "Legal",
        "version": "v2.0",
        "descripcion": "Acuerdo de Confidencialidad y No Divulgación (NDA) para proyectos de energía renovable.",
        "campos": {
            "EMPRESA_A": "Parte Reveladora",
            "EMPRESA_B": "Parte Receptora",
            "NOMBRE_PROYECTO": "Nombre del proyecto",
            "AÑOS_VIGENCIA": "Vigencia (años)",
        },
        "texto": """ACUERDO DE CONFIDENCIALIDAD Y NO DIVULGACIÓN

PARTES:
- Parte Reveladora: [EMPRESA_A]
- Parte Receptora: [EMPRESA_B]

OBJETO: Las partes desean compartir información confidencial relacionada con el proyecto [NOMBRE_PROYECTO] con el propósito de evaluar una posible relación comercial.

INFORMACIÓN CONFIDENCIAL: Se considera confidencial toda información técnica, financiera, comercial o de cualquier otra naturaleza relacionada con el proyecto.

OBLIGACIONES: La Parte Receptora se obliga a: (i) mantener la confidencialidad; (ii) no divulgar a terceros; (iii) usar la información solo para los fines del acuerdo.

EXCEPCIONES: No aplica para información de dominio público, conocida previamente o revelada por orden judicial.

VIGENCIA: [AÑOS_VIGENCIA] años desde la fecha de firma.

INDEMNIZACIÓN: El incumplimiento dará lugar a la indemnización de todos los daños y perjuicios causados.
""",
    },
    {
        "nombre": "Cesion_Derechos.docx",
        "tipo": "Legal",
        "version": "v1.2",
        "descripcion": "Contrato de Cesión de Derechos sobre activos de proyectos de energía.",
        "campos": {
            "EMPRESA_CEDENTE": "Cedente",
            "EMPRESA_CESIONARIA": "Cesionario",
            "DESCRIPCION_ACTIVO": "Descripción del activo/proyecto",
            "PRECIO_USD": "Precio de cesión (USD)",
            "FORMA_PAGO": "Forma de pago",
        },
        "texto": """CONTRATO DE CESIÓN DE DERECHOS

PARTES:
- Cedente: [EMPRESA_CEDENTE]
- Cesionario: [EMPRESA_CESIONARIA]

OBJETO: El Cedente transfiere al Cesionario todos los derechos, títulos e intereses sobre [DESCRIPCION_ACTIVO].

PRECIO: El precio de la cesión es de USD [PRECIO_USD], pagadero de la siguiente forma: [FORMA_PAGO].

DECLARACIONES Y GARANTÍAS: El Cedente declara que: (i) es el legítimo titular de los derechos cedidos; (ii) los derechos están libres de gravámenes; (iii) cuenta con todas las autorizaciones necesarias.

CONDICIONES PRECEDENTES: La cesión estará sujeta a: obtención de aprobaciones regulatorias, ausencia de litigios y cumplimiento de condiciones financieras.

PERFECCIONAMIENTO: La cesión se perfeccionará con el pago del precio y el otorgamiento de la escritura pública correspondiente.

COSTOS: Los costos notariales y de registro serán asumidos por el Cesionario.
""",
    },
]


# ─── Drive: intentar cargar plantillas reales ──────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _load_drive_templates(drive_root_id: str) -> list:
    """
    Busca una subcarpeta 'Plantillas' dentro del Drive root y lista sus archivos.
    Retorna lista de dicts con keys: nombre, drive_id, tipo, version, descripcion.
    Cachea 5 minutos para no abusar de la API.
    """
    try:
        from utils.drive_manager import get_folder_contents
        all_items = get_folder_contents(drive_root_id)

        # Encontrar subcarpeta llamada "Plantillas" (case-insensitive)
        plantillas_folder = next(
            (f for f in all_items
             if f.get("mimeType") == "application/vnd.google-apps.folder"
             and "plantilla" in f.get("name", "").lower()),
            None
        )
        if not plantillas_folder:
            return []

        archivos = get_folder_contents(plantillas_folder["id"])
        drive_templates = []
        for f in archivos:
            name = f.get("name", "")
            mime = f.get("mimeType", "")
            if not ("pdf" in mime or "word" in mime or name.endswith(".docx") or name.endswith(".pdf")):
                continue
            # Inferir tipo por nombre
            name_up = name.upper()
            tipo = "Otro"
            for t in ["PPA", "EPC", "O&M", "SHA", "NDA"]:
                if t.replace("&", "") in name_up.replace("&", ""):
                    tipo = t
                    break
            drive_templates.append({
                "nombre": name,
                "drive_id": f["id"],
                "tipo": tipo,
                "version": "Drive",
                "descripcion": f"Plantilla desde Google Drive — carpeta Plantillas/",
                "campos": {},
                "texto": None,  # se carga on-demand
            })
        return drive_templates
    except Exception:
        return []


def _get_drive_file_bytes(file_id: str) -> bytes | None:
    """Descarga un archivo de Drive y retorna sus bytes."""
    try:
        from utils.drive_manager import download_file_to_io
        api_key = st.session_state.get("drive_api_key", "")
        bio = download_file_to_io(file_id, api_key=api_key)
        if bio:
            return bio.read()
    except Exception:
        pass
    return None


# Determinar si Drive está configurado
drive_root_id = st.session_state.get("drive_root_id", "")
drive_ok = bool(drive_root_id and drive_root_id not in ("", "DEMO_KEY"))

# Cargar plantillas desde Drive si está disponible
drive_templates = []
if drive_ok:
    with st.spinner("Buscando plantillas en Google Drive..."):
        drive_templates = _load_drive_templates(drive_root_id)

# Unir: plantillas de Drive primero, luego las estáticas que no estén en Drive
drive_names_lower = {d["nombre"].lower() for d in drive_templates}
plantillas_estaticas_filtradas = [
    p for p in PLANTILLAS_ESTATICAS
    if p["nombre"].lower() not in drive_names_lower
]
PLANTILLAS = drive_templates + plantillas_estaticas_filtradas

# Banner de origen
if drive_ok and drive_templates:
    st.success(
        f"**{len(drive_templates)}** plantilla(s) cargadas desde Google Drive · "
        f"**{len(plantillas_estaticas_filtradas)}** del catálogo estático.",
        icon="☁️"
    )
elif drive_ok and not drive_templates:
    st.info(
        "Drive conectado, pero no se encontró la carpeta **Plantillas/** en la raíz. "
        "Mostrando catálogo estático. Crea una carpeta llamada 'Plantillas' en Drive "
        "y sube tus plantillas para verlas aquí.",
        icon="📁"
    )
else:
    st.info(
        "Mostrando catálogo estático. "
        "**Conecta Drive en Ajustes** para cargar tus plantillas reales.",
        icon="📋"
    )


# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_biblioteca, tab_comparar, tab_generar, tab_nueva = st.tabs([
    "📚 Biblioteca",
    "🔀 Comparar plantillas",
    "✍️ Generar desde plantilla",
    "📝 Nueva plantilla",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BIBLIOTECA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_biblioteca:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Plantillas disponibles")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Biblioteca de plantillas contractuales de Pactora. "
            "**Ver** muestra el contenido. "
            "**Descargar** exporta la plantilla. "
            "**Cmp** la preselecciona para comparar."
        )

    tipo_filter = st.multiselect(
        "Filtrar por tipo",
        sorted({p["tipo"] for p in PLANTILLAS}),
        default=[],
        placeholder="Todos los tipos",
        key="plt_filter"
    )
    filtered_plt = [
        p for p in PLANTILLAS
        if not tipo_filter or p["tipo"] in tipo_filter
    ]
    st.caption(f"{len(filtered_plt)} plantilla(s) · {'☁️ Drive + catálogo' if drive_templates else '📋 Catálogo estático'}")

    if not filtered_plt:
        st.markdown(
            '<div style="text-align:center;padding:40px;color:#999;">'
            '<div style="font-size:40px;">📄</div>'
            '<div style="font-size:16px;margin-top:8px;">No hay plantillas para los filtros seleccionados</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        for p in filtered_plt:
            color = TIPO_COLOR.get(p["tipo"], "#915BD8")
            is_drive = p.get("drive_id") is not None
            badge_src = "☁️ Drive" if is_drive else "📋 Estática"
            cols = st.columns([5, 1, 1, 1])

            cols[0].markdown(
                f'<div style="padding:4px 0;">'
                f'<span style="font-weight:700;">📝 {p["nombre"]}</span>&nbsp;&nbsp;'
                f'<span style="background:{color};color:white;border-radius:4px;'
                f'padding:2px 8px;font-size:11px;">{p["tipo"]}</span>&nbsp;'
                f'<span style="background:#eee;color:#555;border-radius:4px;'
                f'padding:2px 6px;font-size:11px;">{p["version"]}</span>&nbsp;'
                f'<span style="background:#f0f0f0;color:#888;border-radius:4px;'
                f'padding:2px 6px;font-size:10px;">{badge_src}</span>'
                f'</div>'
                f'<div style="color:#888;font-size:12px;">{p["descripcion"][:90]}…</div>',
                unsafe_allow_html=True
            )

            prev_key = f"plt_prev_{p['nombre']}"
            if cols[1].button("Ver", key=f"pver_{p['nombre']}", use_container_width=True):
                st.session_state[prev_key] = not st.session_state.get(prev_key, False)
                st.rerun()

            # Botón descargar
            if is_drive:
                # Plantilla real de Drive: descarga al hacer clic
                dl_key = f"pdl_drive_{p['nombre']}"
                if cols[2].button("⬇", key=dl_key, use_container_width=True, help="Descargar desde Drive"):
                    with st.spinner("Descargando..."):
                        file_bytes = _get_drive_file_bytes(p["drive_id"])
                    if file_bytes:
                        st.download_button(
                            "Guardar archivo",
                            data=file_bytes,
                            file_name=p["nombre"],
                            mime="application/octet-stream",
                            key=f"pdl_save_{p['nombre']}"
                        )
                        st.toast(f"Listo: {p['nombre']}", icon="✅")
                    else:
                        st.warning("No se pudo descargar. Verifica los permisos de Drive.", icon="⚠️")
            elif p.get("texto"):
                # Plantilla estática: descarga directa como .txt
                cols[2].download_button(
                    "⬇",
                    data=p["texto"].encode("utf-8"),
                    file_name=p["nombre"].replace(".docx", ".txt"),
                    mime="text/plain",
                    key=f"pdl_{p['nombre']}",
                    use_container_width=True,
                    help="Descargar plantilla como texto"
                )
            else:
                if cols[2].button("⬇", key=f"pdl_na_{p['nombre']}", use_container_width=True,
                                   help="Conecta Drive para descargar"):
                    st.toast("Conecta Drive en Ajustes para descargar este archivo.", icon="ℹ️")

            if cols[3].button("Cmp", key=f"pcmp_{p['nombre']}", use_container_width=True,
                               help="Preseleccionar para comparar"):
                st.session_state["plt_cmp_a"] = p["nombre"]
                st.toast(f"'{p['nombre']}' preseleccionada para comparar", icon="✅")

            if st.session_state.get(prev_key, False):
                with st.expander(f"📄 {p['nombre']}", expanded=True):
                    st.markdown(f"**{p['descripcion']}**")
                    if p.get("texto"):
                        st.text_area(
                            "plt_text", value=p["texto"], height=300,
                            disabled=True, label_visibility="collapsed",
                            key=f"ta_plt_{p['nombre']}"
                        )
                    elif is_drive:
                        st.info("Vista previa no disponible para archivos de Drive. Usa **Descargar** para ver el contenido.")
            st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — COMPARAR PLANTILLAS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_comparar:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Comparar dos plantillas")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Selecciona dos plantillas para ver su contenido lado a lado. "
            "El sistema calcula similitud y muestra las diferencias línea a línea. "
            "Solo disponible para plantillas del catálogo estático."
        )

    # Solo plantillas con texto disponible para comparar
    plt_con_texto = [p for p in PLANTILLAS if p.get("texto")]
    nombres_cmp = [p["nombre"] for p in plt_con_texto]

    if len(plt_con_texto) < 2:
        st.markdown(
            '<div style="text-align:center;padding:40px;color:#999;">'
            '<div style="font-size:40px;">🔀</div>'
            '<div style="font-size:16px;margin-top:8px;">Se necesitan al menos 2 plantillas con texto para comparar</div>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        presel_a = st.session_state.get("plt_cmp_a", nombres_cmp[0])
        def_a = nombres_cmp.index(presel_a) if presel_a in nombres_cmp else 0

        col_a, col_b = st.columns(2)
        with col_a:
            sel_a = st.selectbox("Plantilla A", nombres_cmp, index=def_a, key="cmp_plt_a")
        with col_b:
            sel_b = st.selectbox("Plantilla B", nombres_cmp,
                                  index=min(1, len(nombres_cmp) - 1), key="cmp_plt_b")

        plt_a = next((p for p in plt_con_texto if p["nombre"] == sel_a), None)
        plt_b = next((p for p in plt_con_texto if p["nombre"] == sel_b), None)

        if plt_a and plt_b:
            col_ta, col_tb = st.columns(2)
            with col_ta:
                color_a = TIPO_COLOR.get(plt_a["tipo"], "#915BD8")
                st.markdown(
                    f'<span style="background:{color_a};color:white;border-radius:4px;'
                    f'padding:2px 8px;font-size:12px;">{plt_a["tipo"]} — {plt_a["version"]}</span>',
                    unsafe_allow_html=True
                )
                st.text_area("cmp_ta", value=plt_a["texto"], height=350,
                              disabled=True, label_visibility="collapsed", key="cmp_ta_content")
            with col_tb:
                color_b = TIPO_COLOR.get(plt_b["tipo"], "#915BD8")
                st.markdown(
                    f'<span style="background:{color_b};color:white;border-radius:4px;'
                    f'padding:2px 8px;font-size:12px;">{plt_b["tipo"]} — {plt_b["version"]}</span>',
                    unsafe_allow_html=True
                )
                st.text_area("cmp_tb", value=plt_b["texto"], height=350,
                              disabled=True, label_visibility="collapsed", key="cmp_tb_content")

            # Similitud
            ratio = difflib.SequenceMatcher(
                None, plt_a["texto"].split(), plt_b["texto"].split()
            ).ratio()
            sim_pct = int(ratio * 100)
            color_sim = "#388e3c" if sim_pct > 60 else "#f57c00" if sim_pct > 30 else "#e53935"
            st.markdown(
                f'<div style="padding:10px;border-left:4px solid {color_sim};'
                f'background:white;border-radius:0 8px 8px 0;margin:12px 0;">'
                f'<b>Similitud:</b> <span style="color:{color_sim};font-size:20px;'
                f'font-weight:900;">{sim_pct}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            if sel_a != sel_b:
                diff_lines = list(difflib.unified_diff(
                    plt_a["texto"].splitlines(),
                    plt_b["texto"].splitlines(),
                    fromfile=sel_a,
                    tofile=sel_b,
                    lineterm="",
                    n=2
                ))
                if diff_lines:
                    # Diff visual con colores
                    html_diff = []
                    for line in diff_lines:
                        if line.startswith("+") and not line.startswith("+++"):
                            html_diff.append(
                                f'<div style="background:#e8f5e9;color:#1b5e20;'
                                f'font-family:monospace;font-size:12px;padding:1px 6px;">{line}</div>'
                            )
                        elif line.startswith("-") and not line.startswith("---"):
                            html_diff.append(
                                f'<div style="background:#ffebee;color:#b71c1c;'
                                f'font-family:monospace;font-size:12px;padding:1px 6px;">{line}</div>'
                            )
                        elif line.startswith("@@"):
                            html_diff.append(
                                f'<div style="background:#e3f2fd;color:#0d47a1;'
                                f'font-family:monospace;font-size:12px;padding:1px 6px;">{line}</div>'
                            )
                        else:
                            html_diff.append(
                                f'<div style="font-family:monospace;font-size:12px;'
                                f'padding:1px 6px;color:#555;">{line}</div>'
                            )
                    with st.expander("Ver diferencias detalladas", expanded=False):
                        st.markdown(
                            '<div style="border:1px solid #e0e0e0;border-radius:8px;'
                            'overflow:auto;max-height:400px;">'
                            + "".join(html_diff) +
                            '</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.info("Selecciona dos plantillas diferentes para ver las diferencias.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GENERAR DESDE PLANTILLA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_generar:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Generar borrador desde plantilla")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Selecciona una plantilla del catálogo, completa los campos variables "
            "y obtén un borrador con tus datos. "
            "🔮 *Con Gemini activo, JuanMitaBot ampliará cada cláusula automáticamente.*"
        )

    # Solo plantillas del catálogo estático (tienen campos definidos)
    plt_con_campos = [p for p in PLANTILLAS_ESTATICAS if p.get("campos")]
    if not plt_con_campos:
        st.info("No hay plantillas con campos configurados.")
    else:
        nombres_gen = [p["nombre"] for p in plt_con_campos]
        sel_gen = st.selectbox(
            "Selecciona una plantilla base",
            nombres_gen,
            key="gen_plt_sel",
            format_func=lambda n: next(
                (f"{p['tipo']} — {p['nombre']}" for p in plt_con_campos if p["nombre"] == n), n
            )
        )
        plt_gen = next((p for p in plt_con_campos if p["nombre"] == sel_gen), None)

        if plt_gen:
            st.markdown(
                f'<div style="padding:10px 14px;background:#f9f5ff;border-radius:8px;'
                f'border-left:4px solid #915BD8;margin-bottom:16px;">'
                f'<b>{plt_gen["nombre"]}</b> — {plt_gen["descripcion"]}'
                f'</div>',
                unsafe_allow_html=True
            )

            col_form, col_prev = st.columns([1, 1])

            with col_form:
                st.markdown("**Completa los campos:**")
                valores = {}
                for campo, etiqueta in plt_gen["campos"].items():
                    valores[campo] = st.text_input(
                        etiqueta,
                        placeholder=f"[{campo}]",
                        key=f"gen_{sel_gen}_{campo}"
                    )

                from core.llm_service import LLM_AVAILABLE
                generar_label = "✨ Generar con JuanMitaBot" if LLM_AVAILABLE else "👁️ Vista previa del borrador"
                generar = st.button(generar_label, type="primary", use_container_width=True, key="btn_generar_plt")

            with col_prev:
                st.markdown("**Vista previa:**")
                # Sustituir campos en el texto base
                texto_preview = plt_gen["texto"]
                campos_vacios = []
                for campo, valor in valores.items():
                    if valor.strip():
                        texto_preview = texto_preview.replace(f"[{campo}]", f"**{valor.strip()}**")
                    else:
                        campos_vacios.append(campo)

                # Resaltar campos pendientes
                for campo in campos_vacios:
                    texto_preview = texto_preview.replace(
                        f"[{campo}]",
                        f"[⚠️ {campo}]"
                    )

                if campos_vacios:
                    st.caption(f"⚠️ {len(campos_vacios)} campo(s) pendiente(s)")

                st.text_area(
                    "preview_borrador",
                    value=texto_preview.replace("**", ""),
                    height=380,
                    disabled=True,
                    label_visibility="collapsed",
                    key="ta_gen_preview"
                )

            # Acción del botón generar
            if generar:
                campos_completos = all(v.strip() for v in valores.values())
                if not campos_completos:
                    st.warning("Completa todos los campos antes de generar.", icon="⚠️")
                else:
                    texto_final = plt_gen["texto"]
                    for campo, valor in valores.items():
                        texto_final = texto_final.replace(f"[{campo}]", valor.strip())

                    if LLM_AVAILABLE:
                        # Placeholder: cuando Gemini esté activo, llamar a llm_service
                        st.info(
                            "JuanMitaBot está listo para ampliar este borrador. "
                            "Activa la API key de Gemini para generar el contrato completo.",
                            icon="🔮"
                        )
                    else:
                        st.success("Borrador generado con los campos completados.", icon="✅")

                    # Mostrar texto final y opción de descargar
                    with st.expander("📄 Borrador generado", expanded=True):
                        st.text_area(
                            "borrador_final",
                            value=texto_final,
                            height=400,
                            key="ta_borrador_final"
                        )
                        nombre_salida = sel_gen.replace(".docx", f"_borrador.txt")
                        st.download_button(
                            "⬇ Descargar borrador",
                            data=texto_final.encode("utf-8"),
                            file_name=nombre_salida,
                            mime="text/plain",
                            use_container_width=True,
                            key="dl_borrador_final"
                        )

                        # Guardar en sesión para usar en Editor de Legal
                        if st.button("📝 Abrir en Editor de Borradores", use_container_width=True,
                                      key="btn_abrir_editor"):
                            st.session_state["draft_content"] = texto_final
                            st.session_state["draft_filename"] = nombre_salida
                            st.toast("Borrador enviado al Editor de Legal.", icon="✅")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NUEVA PLANTILLA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_nueva:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Agregar plantilla personalizada")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Escribe o pega el texto de una nueva plantilla para guardarla en la sesión. "
            "🔮 *Con Gemini activo, JuanMitaBot podrá generarla desde una descripción.*"
        )

    col_form, col_ai = st.columns([3, 2])
    with col_form:
        nombre_nueva = st.text_input(
            "Nombre de la plantilla",
            placeholder="Ej: Contrato_Marco_2025.docx",
            key="nueva_plt_nombre"
        )
        tipo_nueva = st.selectbox(
            "Tipo",
            ["PPA", "EPC", "O&M", "Legal", "SHA", "NDA", "Otro"],
            key="nueva_plt_tipo"
        )
        texto_nueva = st.text_area(
            "Contenido de la plantilla",
            placeholder="Escribe o pega aquí el contenido de la plantilla...",
            height=300,
            key="nueva_plt_texto"
        )
        if st.button("💾 Guardar en sesión", type="primary", use_container_width=True, key="btn_guardar_nueva"):
            if nombre_nueva and texto_nueva:
                if "plantillas_custom" not in st.session_state:
                    st.session_state.plantillas_custom = []
                # Evitar duplicados por nombre
                existing = next(
                    (i for i, pc in enumerate(st.session_state.plantillas_custom)
                     if pc["nombre"] == nombre_nueva), None
                )
                if existing is not None:
                    st.session_state.plantillas_custom[existing] = {
                        "nombre": nombre_nueva,
                        "tipo": tipo_nueva,
                        "texto": texto_nueva
                    }
                    st.toast(f"Plantilla '{nombre_nueva}' actualizada.", icon="✅")
                else:
                    st.session_state.plantillas_custom.append({
                        "nombre": nombre_nueva,
                        "tipo": tipo_nueva,
                        "texto": texto_nueva
                    })
                    st.toast(f"Plantilla '{nombre_nueva}' guardada en la sesión.", icon="✅")
            else:
                st.error("Completa el nombre y el contenido.", icon="⚠️")

    with col_ai:
        from core.llm_service import LLM_AVAILABLE as _LLM
        ai_color = "#e8f5e9" if _LLM else "#f9f5ff"
        ai_badge = "🟢 Activo" if _LLM else "⚫ Inactivo"
        st.markdown(
            f'<div style="padding:16px;background:{ai_color};border-radius:12px;'
            f'border:1px solid #e0d4f7;">'
            f'<div style="font-weight:900;color:#2C2039;margin-bottom:8px;">'
            f'🔮 Generación con JuanMitaBot <span style="font-size:11px;">{ai_badge}</span></div>'
            f'<div style="font-size:13px;color:#666;margin-bottom:12px;">'
            f'{"Describe el contrato que necesitas y JuanMitaBot lo generará completo." if _LLM else "Próximamente: describe el contrato que necesitas y JuanMitaBot generará una plantilla completa basada en los estándares de Pactora."}'
            f'</div>'
            f'<div style="font-size:12px;color:#915BD8;font-weight:600;">'
            f'{"Usa la pestaña Generar para activarlo." if _LLM else "Disponible con Gemini API"}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Plantillas guardadas en sesión
        if st.session_state.get("plantillas_custom"):
            st.markdown("**Plantillas guardadas en sesión:**")
            for i, pc in enumerate(st.session_state.plantillas_custom):
                color_pc = TIPO_COLOR.get(pc["tipo"], "#607D8B")
                col1, col2 = st.columns([4, 1])
                col1.markdown(
                    f'<span style="background:{color_pc};color:white;border-radius:4px;'
                    f'padding:1px 6px;font-size:10px;">{pc["tipo"]}</span> {pc["nombre"]}',
                    unsafe_allow_html=True
                )
                if col2.button("🗑", key=f"del_custom_{i}", help="Eliminar"):
                    st.session_state.plantillas_custom.pop(i)
                    st.rerun()
