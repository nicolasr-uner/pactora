import streamlit as st
import difflib
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Biblioteca de Plantillas")
st.caption("Accede, previsualiza y compara las plantillas contractuales estándar de Pactora.")

# ─── Datos de plantillas mock ──────────────────────────────────────────────────
PLANTILLAS = [
    {
        "nombre": "PPA_Standard_V2.docx",
        "tipo": "PPA",
        "version": "v2.1",
        "descripcion": "Contrato estándar de Compra de Energía (Power Purchase Agreement). "
                       "Incluye cláusulas de capacidad, precio, despacho y penalidades.",
        "texto": """CONTRATO DE COMPRA DE ENERGÍA (PPA)

PARTES:
- Vendedor: [EMPRESA GENERADORA]
- Comprador: [EMPRESA COMPRADORA]

OBJETO: El Vendedor se obliga a generar y entregar energía eléctrica al Comprador bajo las condiciones establecidas.

PLAZO: El presente contrato tendrá una duración de [15] años contados desde la Fecha de Inicio.

PRECIO DE ENERGÍA: El precio aplicable será de [XX] COP/kWh, indexado anualmente según el IPC.

CAPACIDAD CONTRATADA: [X] MW en condiciones estándar de despacho.

PENALIDADES: En caso de incumplimiento en la entrega, se aplicará una penalidad del [5%] sobre el valor mensual incumplido.

FUERZA MAYOR: Ninguna de las partes será responsable por el incumplimiento de sus obligaciones causado por eventos de fuerza mayor o caso fortuito.

TERMINACIÓN: Cualquiera de las partes podrá terminar el contrato con [90] días de preaviso en caso de incumplimiento material no subsanado.

CONFIDENCIALIDAD: Las partes se obligan a mantener la confidencialidad de los términos del presente contrato.
""",
    },
    {
        "nombre": "EPC_Contrato_Base.docx",
        "tipo": "EPC",
        "version": "v1.3",
        "descripcion": "Contrato de Ingeniería, Procura y Construcción. "
                       "Cubre diseño, adquisición de equipos, construcción y puesta en marcha.",
        "texto": """CONTRATO EPC — INGENIERÍA, PROCURA Y CONSTRUCCIÓN

PARTES:
- Contratante: [EMPRESA DUEÑA DEL PROYECTO]
- Contratista EPC: [EMPRESA CONSTRUCTORA]

OBJETO: El Contratista se obliga a ejecutar, por su cuenta y riesgo, el proyecto de construcción del parque solar fotovoltaico de [X] MW.

ALCANCE DEL TRABAJO: Diseño, ingeniería de detalle, suministro de equipos, construcción civil, instalación electromecánica y puesta en marcha.

PRECIO TOTAL: [USD X,XXX,XXX] precio fijo llave en mano.

PLAZO DE EJECUCIÓN: [18] meses contados desde la firma del contrato.

GARANTÍAS: El Contratista otorgará garantía de buen funcionamiento por [2] años.

PENALIDADES POR MORA: Por cada día de retraso en la entrega, se aplicará una penalidad del [0.1%] del valor total del contrato, con un tope del [10%].

RETENCIONES: Se retendrá el [10%] de cada factura hasta la recepción definitiva de las obras.

SEGUROS: El Contratista deberá mantener vigentes seguros de responsabilidad civil, todo riesgo construcción y de accidentes de trabajo.
""",
    },
    {
        "nombre": "OyM_Marco_General.docx",
        "tipo": "O&M",
        "version": "v1.0",
        "descripcion": "Contrato de Operación y Mantenimiento para plantas de generación. "
                       "Define niveles de servicio, disponibilidad y reportes.",
        "texto": """CONTRATO DE OPERACIÓN Y MANTENIMIENTO (O&M)

PARTES:
- Propietario: [EMPRESA PROPIETARIA]
- Operador: [EMPRESA OPERADORA]

OBJETO: El Operador prestará los servicios de operación y mantenimiento de la planta de generación solar de [X] MW.

DISPONIBILIDAD GARANTIZADA: El Operador garantiza una disponibilidad mínima del [98%] anual de la planta.

SERVICIOS INCLUIDOS:
- Operación diaria de la planta
- Mantenimiento preventivo y correctivo
- Reporte mensual de generación
- Gestión de garantías de equipos

REMUNERACIÓN: Tarifa fija mensual de [USD XX,XXX] más variable según generación real.

PENALIDADES: Por cada punto porcentual de disponibilidad por debajo del 98%, se aplicará una penalidad del [2%] de la tarifa mensual.

INFORMES: El Operador entregará informes mensuales de generación, disponibilidad e incidencias antes del día [5] de cada mes.

DURACIÓN: [5] años renovables automáticamente por períodos iguales salvo aviso contrario con [90] días de anticipación.
""",
    },
    {
        "nombre": "NDA_Confidencialidad.docx",
        "tipo": "Legal",
        "version": "v2.0",
        "descripcion": "Acuerdo de Confidencialidad y No Divulgación (NDA) para proyectos de energía renovable.",
        "texto": """ACUERDO DE CONFIDENCIALIDAD Y NO DIVULGACIÓN

PARTES:
- Parte Reveladora: [EMPRESA A]
- Parte Receptora: [EMPRESA B]

OBJETO: Las partes desean compartir información confidencial relacionada con el proyecto de energía renovable [NOMBRE DEL PROYECTO] con el propósito de evaluar una posible relación comercial.

INFORMACIÓN CONFIDENCIAL: Se considera confidencial toda información técnica, financiera, comercial o de cualquier otra naturaleza relacionada con el proyecto.

OBLIGACIONES: La Parte Receptora se obliga a: (i) mantener la confidencialidad; (ii) no divulgar a terceros; (iii) usar la información solo para los fines del acuerdo.

EXCEPCIONES: No aplica para información de dominio público, conocida previamente o revelada por orden judicial.

VIGENCIA: [2] años desde la fecha de firma.

INDEMNIZACIÓN: El incumplimiento dará lugar a la indemnización de todos los daños y perjuicios causados.
""",
    },
    {
        "nombre": "Cesion_Derechos.docx",
        "tipo": "Legal",
        "version": "v1.2",
        "descripcion": "Contrato de Cesión de Derechos sobre activos de proyectos de energía.",
        "texto": """CONTRATO DE CESIÓN DE DERECHOS

PARTES:
- Cedente: [EMPRESA CEDENTE]
- Cesionario: [EMPRESA CESIONARIA]

OBJETO: El Cedente transfiere al Cesionario todos los derechos, títulos e intereses sobre [DESCRIPCIÓN DEL ACTIVO/PROYECTO].

PRECIO: El precio de la cesión es de [USD XX,XXX,XXX], pagadero de la siguiente forma: [DESCRIBIR FORMA DE PAGO].

DECLARACIONES Y GARANTÍAS: El Cedente declara que: (i) es el legítimo titular de los derechos cedidos; (ii) los derechos están libres de gravámenes; (iii) cuenta con todas las autorizaciones necesarias.

CONDICIONES PRECEDENTES: La cesión estará sujeta a: obtención de aprobaciones regulatorias, ausencia de litigios y cumplimiento de condiciones financieras.

PERFECCIONAMIENTO: La cesión se perfeccionará con el pago del precio y el otorgamiento de la escritura pública correspondiente.

COSTOS: Los costos notariales y de registro serán asumidos por el Cesionario.
""",
    },
]

TIPO_COLOR = {
    "PPA": "#4CAF50",
    "EPC": "#2196F3",
    "O&M": "#FF9800",
    "Legal": "#9C27B0",
}

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_biblioteca, tab_comparar, tab_nueva = st.tabs([
    "📚 Biblioteca",
    "🔀 Comparar plantillas",
    "📝 Nueva plantilla",
])

# ─── BIBLIOTECA ───────────────────────────────────────────────────────────────
with tab_biblioteca:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Plantillas disponibles")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Biblioteca de plantillas contractuales estándar de Pactora. "
            "**Ver** muestra el contenido completo. "
            "**Descargar** exporta la plantilla como archivo de texto. "
            "**Comparar** la preselecciona para la pestaña de comparación."
        )

    tipo_filter = st.multiselect(
        "Filtrar por tipo",
        ["PPA", "EPC", "O&M", "Legal"],
        default=[],
        placeholder="Todos los tipos",
        key="plt_filter"
    )
    filtered_plt = [
        p for p in PLANTILLAS
        if not tipo_filter or p["tipo"] in tipo_filter
    ]
    st.caption(f"{len(filtered_plt)} plantilla(s)")

    for p in filtered_plt:
        color = TIPO_COLOR.get(p["tipo"], "#915BD8")
        cols = st.columns([5, 1, 1, 1])

        cols[0].markdown(
            f'<div style="padding:4px 0;">'
            f'<span style="font-weight:700;">📝 {p["nombre"]}</span>&nbsp;&nbsp;'
            f'<span style="background:{color};color:white;border-radius:4px;'
            f'padding:2px 8px;font-size:11px;">{p["tipo"]}</span>&nbsp;'
            f'<span style="background:#eee;color:#555;border-radius:4px;'
            f'padding:2px 6px;font-size:11px;">{p["version"]}</span>'
            f'</div>'
            f'<div style="color:#888;font-size:12px;">{p["descripcion"][:80]}…</div>',
            unsafe_allow_html=True
        )

        prev_key = f"plt_prev_{p['nombre']}"
        if cols[1].button("Ver", key=f"pver_{p['nombre']}", use_container_width=True):
            st.session_state[prev_key] = not st.session_state.get(prev_key, False)
            st.rerun()

        cols[2].download_button(
            "⬇",
            data=p["texto"].encode("utf-8"),
            file_name=p["nombre"].replace(".docx", ".txt"),
            mime="text/plain",
            key=f"pdl_{p['nombre']}",
            use_container_width=True,
            help="Descargar plantilla"
        )

        if cols[3].button("Cmp", key=f"pcmp_{p['nombre']}", use_container_width=True, help="Preseleccionar para comparar"):
            st.session_state["plt_cmp_a"] = p["nombre"]
            st.toast(f"'{p['nombre']}' preseleccionada", icon="✅")

        if st.session_state.get(prev_key, False):
            with st.expander(f"📄 {p['nombre']}", expanded=True):
                st.markdown(f"**{p['descripcion']}**")
                st.text_area(
                    "plt_text", value=p["texto"], height=300,
                    disabled=True, label_visibility="collapsed",
                    key=f"ta_plt_{p['nombre']}"
                )
        st.divider()

# ─── COMPARAR PLANTILLAS ──────────────────────────────────────────────────────
with tab_comparar:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Comparar dos plantillas")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Selecciona dos plantillas para ver su contenido lado a lado. "
            "El sistema calcula automáticamente el porcentaje de similitud y muestra las diferencias. "
            "Útil para identificar qué cambió entre versiones de un mismo tipo de contrato."
        )

    nombres = [p["nombre"] for p in PLANTILLAS]
    presel_a = st.session_state.get("plt_cmp_a", nombres[0])
    def_a = nombres.index(presel_a) if presel_a in nombres else 0

    col_a, col_b = st.columns(2)
    with col_a:
        sel_a = st.selectbox("Plantilla A", nombres, index=def_a, key="cmp_plt_a")
    with col_b:
        sel_b = st.selectbox("Plantilla B", nombres, index=min(1, len(nombres) - 1), key="cmp_plt_b")

    plt_a = next((p for p in PLANTILLAS if p["nombre"] == sel_a), None)
    plt_b = next((p for p in PLANTILLAS if p["nombre"] == sel_b), None)

    if plt_a and plt_b:
        col_ta, col_tb = st.columns(2)
        with col_ta:
            color_a = TIPO_COLOR.get(plt_a["tipo"], "#915BD8")
            st.markdown(
                f'<span style="background:{color_a};color:white;border-radius:4px;'
                f'padding:2px 8px;font-size:12px;">{plt_a["tipo"]} — {plt_a["version"]}</span>',
                unsafe_allow_html=True
            )
            st.text_area(
                "cmp_ta", value=plt_a["texto"], height=350,
                disabled=True, label_visibility="collapsed", key="cmp_ta_content"
            )
        with col_tb:
            color_b = TIPO_COLOR.get(plt_b["tipo"], "#915BD8")
            st.markdown(
                f'<span style="background:{color_b};color:white;border-radius:4px;'
                f'padding:2px 8px;font-size:12px;">{plt_b["tipo"]} — {plt_b["version"]}</span>',
                unsafe_allow_html=True
            )
            st.text_area(
                "cmp_tb", value=plt_b["texto"], height=350,
                disabled=True, label_visibility="collapsed", key="cmp_tb_content"
            )

        # Similitud
        ratio = difflib.SequenceMatcher(None, plt_a["texto"].split(), plt_b["texto"].split()).ratio()
        sim_pct = int(ratio * 100)
        color_sim = "#388e3c" if sim_pct > 60 else "#f57c00" if sim_pct > 30 else "#e53935"
        st.markdown(
            f'<div style="padding:10px;border-left:4px solid {color_sim};'
            f'background:white;border-radius:0 8px 8px 0;margin:12px 0;">'
            f'<b>Similitud:</b> <span style="color:{color_sim};font-size:20px;font-weight:900;">{sim_pct}%</span>'
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
                n=1
            ))
            if diff_lines:
                with st.expander("Ver diferencias detalladas"):
                    st.text_area(
                        "diff_plt", value="\n".join(diff_lines), height=300,
                        disabled=True, label_visibility="collapsed"
                    )
        else:
            st.info("Selecciona dos plantillas diferentes para ver diferencias.")

# ─── NUEVA PLANTILLA ──────────────────────────────────────────────────────────
with tab_nueva:
    hrow = st.columns([9, 1])
    hrow[0].markdown("#### Crear nueva plantilla")
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Escribe o pega el texto de una nueva plantilla para guardarla en la sesión. "
            "🔮 *Próximamente: generación automática con IA y guardado en Google Drive.*"
        )

    col_form, col_ai = st.columns([3, 2])
    with col_form:
        nombre_nueva = st.text_input("Nombre de la plantilla", placeholder="Ej: Contrato_Marco_2025.docx")
        tipo_nueva = st.selectbox("Tipo", ["PPA", "EPC", "O&M", "Legal", "Otro"])
        texto_nueva = st.text_area(
            "Contenido de la plantilla",
            placeholder="Escribe o pega aquí el contenido de la plantilla...",
            height=300
        )
        if st.button("💾 Guardar en sesión", type="primary", use_container_width=True):
            if nombre_nueva and texto_nueva:
                if "plantillas_custom" not in st.session_state:
                    st.session_state.plantillas_custom = []
                st.session_state.plantillas_custom.append({
                    "nombre": nombre_nueva,
                    "tipo": tipo_nueva,
                    "texto": texto_nueva
                })
                st.success(f"Plantilla '{nombre_nueva}' guardada en la sesión.")
            else:
                st.error("Completa el nombre y el contenido.")

    with col_ai:
        st.markdown(
            '<div style="padding:16px;background:#f9f5ff;border-radius:12px;'
            'border:1px solid #e0d4f7;">'
            '<div style="font-weight:900;color:#2C2039;margin-bottom:8px;">🔮 Generación con IA</div>'
            '<div style="font-size:13px;color:#666;margin-bottom:12px;">'
            'Próximamente podrás describir el contrato que necesitas y JuanMitaBot '
            'generará una plantilla completa basada en los estándares de Pactora.'
            '</div>'
            '<div style="font-size:12px;color:#915BD8;font-weight:600;">Disponible con Gemini API</div>'
            '</div>',
            unsafe_allow_html=True
        )

        # Mostrar plantillas custom guardadas en sesión
        if st.session_state.get("plantillas_custom"):
            st.markdown("**Plantillas guardadas en sesión:**")
            for pc in st.session_state.plantillas_custom:
                st.markdown(f"• {pc['nombre']} ({pc['tipo']})")
