import streamlit as st
import datetime
import calendar
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()


def _mini_calendar(year, month, event_days):
    """Renderiza calendario mensual en HTML."""
    MONTH_NAMES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    TIPO_COLOR = {
        "inicio": "#4CAF50", "vencimiento": "#e53935", "renovacion": "#FF9800",
        "pago": "#2196F3", "hito": "#9C27B0"
    }
    today = datetime.date.today()
    cal_matrix = calendar.monthcalendar(year, month)

    html = (
        '<div style="background:white;border-radius:12px;padding:16px;'
        'box-shadow:0 2px 12px rgba(145,91,216,0.08);">'
        f'<div style="text-align:center;font-weight:900;color:#2C2039;'
        f'margin-bottom:10px;font-size:14px;">{MONTH_NAMES[month]} {year}</div>'
        '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        '<tr>'
    )
    for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]:
        html += f'<th style="text-align:center;color:#915BD8;padding:3px;font-weight:700;">{d}</th>'
    html += "</tr>"

    for week in cal_matrix:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += '<td style="padding:4px;"></td>'
            elif day == today.day and year == today.year and month == today.month:
                html += (
                    f'<td style="text-align:center;padding:4px;">'
                    f'<div style="background:#915BD8;color:white;border-radius:50%;'
                    f'width:24px;height:24px;display:inline-flex;align-items:center;'
                    f'justify-content:center;font-weight:900;font-size:11px;">{day}</div></td>'
                )
            elif day in event_days:
                color = TIPO_COLOR.get(event_days[day], "#915BD8")
                html += (
                    f'<td style="text-align:center;padding:4px;">'
                    f'<div style="background:{color};color:white;border-radius:50%;'
                    f'width:24px;height:24px;display:inline-flex;align-items:center;'
                    f'justify-content:center;font-size:11px;">{day}</div></td>'
                )
            else:
                html += f'<td style="text-align:center;padding:4px;color:#444;">{day}</td>'
        html += "</tr>"
    html += "</table>"
    if event_days:
        html += f'<div style="font-size:11px;color:#666;margin-top:6px;text-align:center;">{len(event_days)} evento(s) este mes</div>'
    html += "</div>"
    return html


# ─── Layout principal ──────────────────────────────────────────────────────────
col_explorer, col_right = st.columns([3, 2])

# ─── Explorador de Archivos ───────────────────────────────────────────────────
with col_explorer:
    hrow = st.columns([9, 1])
    hrow[0].markdown('<div class="card-title">Explorador de Archivos</div>', unsafe_allow_html=True)
    with hrow[1].popover("ℹ️"):
        st.markdown(
            "Lista los contratos cargados en el sistema. "
            "Haz clic en el nombre para ver una previsualización del texto. "
            "El icono **✓** indica que el contrato está disponible para búsqueda en JuanMitaChat."
        )

    stats = st.session_state.chatbot.get_stats()
    sources = stats.get("sources", [])

    if not sources:
        st.info("Aún no hay contratos cargados. Ve a **Ajustes** para subir documentos.")
        st.markdown("**Vista de ejemplo:**")
        mock = [
            ("📄", "PPA_Empresa_Solar.pdf"),
            ("📝", "EPC_Construccion_2024.docx"),
            ("📄", "Contrato_OyM_Unergy.pdf"),
            ("📝", "NDA_Confidencialidad.docx"),
        ]
        for icon, name in mock:
            st.markdown(
                f'<div style="padding:6px 10px;border:1px dashed #ccc;border-radius:8px;'
                f'margin-bottom:6px;color:#aaa;font-size:13px;">{icon} {name} <i>(demo)</i></div>',
                unsafe_allow_html=True
            )
    else:
        search = st.text_input(
            "buscar_explorer", placeholder="🔍 Filtrar por nombre...",
            label_visibility="collapsed", key="explorer_search"
        )
        filtered = [s for s in sources if search.lower() in s.lower()] if search else sources
        st.caption(f"{len(filtered)} archivo(s) indexado(s)")

        for src in filtered[:25]:
            ext = src.lower().split(".")[-1] if "." in src else ""
            icon = "📄" if ext == "pdf" else "📝"
            prev_key = f"inicio_prev_{src}"

            row = st.columns([1, 8, 1])
            row[0].markdown(f"{icon} ✓")
            if row[1].button(src, key=f"file_btn_{src}", use_container_width=True):
                st.session_state[prev_key] = not st.session_state.get(prev_key, False)
                st.rerun()

            with row[2].popover("👁"):
                try:
                    all_docs = st.session_state.chatbot.vectorstore.get(
                        include=["documents", "metadatas"]
                    )
                    chunks = [
                        d for d, m in zip(
                            all_docs.get("documents", []),
                            all_docs.get("metadatas", [])
                        )
                        if m and m.get("source") == src
                    ]
                    if chunks:
                        st.markdown(f"**{src}**")
                        st.text(chunks[0][:500] + "…")
                    else:
                        st.caption("Sin texto disponible.")
                except Exception:
                    st.caption("Error al cargar previsualización.")

            if st.session_state.get(prev_key, False):
                with st.expander(f"📄 {src}", expanded=True):
                    try:
                        all_docs = st.session_state.chatbot.vectorstore.get(
                            include=["documents", "metadatas"]
                        )
                        chunks = [
                            d for d, m in zip(
                                all_docs.get("documents", []),
                                all_docs.get("metadatas", [])
                            )
                            if m and m.get("source") == src
                        ]
                        if chunks:
                            st.text_area(
                                "preview_ta", value="\n\n---\n\n".join(chunks[:3])[:2000],
                                height=250, disabled=True, label_visibility="collapsed",
                                key=f"ta_inicio_{src}"
                            )
                            st.caption(f"{len(chunks)} fragmentos indexados")
                        else:
                            st.caption("Sin texto previsualizable.")
                    except Exception:
                        st.caption("No se pudo cargar el texto.")

# ─── Columna derecha: Mini Calendario + Próximos eventos ─────────────────────
with col_right:
    # Mini Calendario
    hrow2 = st.columns([9, 1])
    hrow2[0].markdown('<div class="card-title">Calendario</div>', unsafe_allow_html=True)
    with hrow2[1].popover("ℹ️"):
        st.markdown(
            "Vista del mes actual. Los días marcados tienen eventos extraídos de los contratos. "
            "Ve a **Calendario** para ver todos los eventos y extraer fechas de los documentos."
        )

    today = datetime.date.today()
    events = st.session_state.get("contract_events", [])
    event_days = {}
    for e in events:
        try:
            d = datetime.date.fromisoformat(e.get("fecha", ""))
            if d.year == today.year and d.month == today.month:
                event_days[d.day] = e.get("tipo_evento", "hito")
        except Exception:
            pass

    st.markdown(_mini_calendar(today.year, today.month, event_days), unsafe_allow_html=True)

    # Leyenda
    TIPO_COLOR = {
        "inicio": "#4CAF50", "vencimiento": "#e53935",
        "renovacion": "#FF9800", "pago": "#2196F3", "hito": "#9C27B0"
    }
    if event_days:
        tipos_mes = set(event_days.values())
        leyenda_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">'
        for tipo, color in TIPO_COLOR.items():
            if tipo in tipos_mes:
                leyenda_html += (
                    f'<span style="background:{color};color:white;border-radius:4px;'
                    f'padding:2px 8px;font-size:10px;">{tipo.capitalize()}</span>'
                )
        leyenda_html += "</div>"
        st.markdown(leyenda_html, unsafe_allow_html=True)
    else:
        st.caption("Sin eventos este mes. Ve a **Calendario** para extraer fechas.")

    # Próximos eventos
    st.markdown("<br>", unsafe_allow_html=True)
    upcoming = []
    for e in events:
        try:
            d = datetime.date.fromisoformat(e.get("fecha", ""))
            if d >= today:
                upcoming.append((d, e))
        except Exception:
            pass
    upcoming.sort(key=lambda x: x[0])

    if upcoming:
        st.markdown('<div class="card-title" style="font-size:14px;">Próximos eventos</div>', unsafe_allow_html=True)
        for d, e in upcoming[:4]:
            diff = (d - today).days
            label = "Hoy" if diff == 0 else f"en {diff}d"
            tipo = e.get("tipo_evento", "hito")
            color = TIPO_COLOR.get(tipo, "#915BD8")
            st.markdown(
                f'<div style="border-left:3px solid {color};padding:6px 10px;'
                f'margin-bottom:6px;border-radius:0 6px 6px 0;background:white;">'
                f'<div style="font-size:12px;font-weight:700;">'
                f'{d.strftime("%d/%m/%Y")} <span style="color:#999;">({label})</span></div>'
                f'<div style="font-size:11px;color:#555;">{e.get("contrato","")[:30]}</div>'
                f'<div style="font-size:10px;color:{color};">{tipo.upper()}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

# ─── Estado del Workspace ─────────────────────────────────────────────────────
st.markdown("---")
ws_row = st.columns([9, 1])
ws_row[0].markdown('<div class="card-title">Estado del Workspace</div>', unsafe_allow_html=True)
with ws_row[1].popover("ℹ️"):
    st.markdown(
        "Resumen del estado del sistema: cuántos contratos están cargados, "
        "cuántos fragmentos están disponibles para búsqueda y cuántos eventos de calendario se han extraído."
    )

stats = st.session_state.chatbot.get_stats()
m1, m2, m3 = st.columns(3)
m1.markdown(
    f'<div class="metric-card"><div class="metric-val">{stats["total_docs"]}</div>'
    '<div class="metric-lbl">Contratos cargados</div></div>',
    unsafe_allow_html=True
)
m2.markdown(
    f'<div class="metric-card"><div class="metric-val">{stats["total_chunks"]}</div>'
    '<div class="metric-lbl">Fragmentos indexados</div></div>',
    unsafe_allow_html=True
)
m3.markdown(
    f'<div class="metric-card"><div class="metric-val">{len(st.session_state.get("contract_events", []))}</div>'
    '<div class="metric-lbl">Eventos de calendario</div></div>',
    unsafe_allow_html=True
)

if stats["sources"]:
    with st.expander(f"Ver contratos disponibles ({len(stats['sources'])})"):
        for s in stats["sources"]:
            st.markdown(f"✓ &nbsp; {s}")
else:
    st.info("Sin contratos cargados. Ve a **Ajustes** para subir documentos PDF o DOCX.")
