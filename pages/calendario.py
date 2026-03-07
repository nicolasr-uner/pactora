import streamlit as st
import json
import datetime
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()

page_header()
api_status_banner()
st.header("Calendario Operativo")

stats = st.session_state.chatbot.get_stats()

if stats["total_docs"] == 0:
    st.info("No hay contratos indexados. Conecta Google Drive en **Ajustes** para comenzar.")
    st.stop()

# ─── Extraer fechas con JuanMitaBot ──────────────────────────────────────────
col_extract, col_sync = st.columns([2, 1])

with col_extract:
    if st.button("Extraer fechas clave de contratos", type="primary", use_container_width=True):
        with st.spinner("JuanMitaBot extrayendo fechas de todos los contratos..."):
            raw = st.session_state.chatbot.ask_question(
                "Extrae TODAS las fechas importantes de cada contrato indexado. "
                "Devuelve SOLO un JSON (sin texto adicional, sin bloques markdown): "
                "una lista de objetos con campos: "
                "contrato (nombre del archivo), "
                "tipo_evento (inicio/vencimiento/renovacion/pago/hito), "
                "fecha (YYYY-MM-DD), "
                "descripcion (breve descripcion del evento)."
            )
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            events = json.loads(clean)
            st.session_state.contract_events = events
            st.success(f"{len(events)} fecha(s) extraida(s) de {stats['total_docs']} contrato(s).")
        except Exception:
            st.warning("No se pudo parsear la respuesta como JSON.")
            with st.expander("Respuesta raw"):
                st.text(raw[:1000])

with col_sync:
    if st.session_state.get("contract_events") and st.button("Sincronizar con Google Calendar", use_container_width=True):
        try:
            from utils.auth_helper import get_calendar_service
            service = get_calendar_service()
            if service is None:
                st.error("Google Calendar no autenticado. Agrega credentials.json.")
            else:
                created = 0
                for ev in st.session_state.contract_events:
                    fecha = ev.get("fecha")
                    if not fecha:
                        continue
                    try:
                        event_body = {
                            "summary": f"[{ev.get('tipo_evento','evento').upper()}] {ev.get('contrato','?')}",
                            "description": ev.get("descripcion", ""),
                            "start": {"date": fecha},
                            "end": {"date": fecha},
                        }
                        service.events().insert(calendarId="primary", body=event_body).execute()
                        created += 1
                    except Exception:
                        pass
                st.success(f"{created} evento(s) creados en Google Calendar.")
        except Exception as e:
            st.error(f"Error al sincronizar: {e}")

st.markdown("---")

# ─── Vista de calendario ─────────────────────────────────────────────────────
events = st.session_state.get("contract_events", [])

if not events:
    st.info("Haz clic en 'Extraer fechas clave' para poblar el calendario.")
else:
    # Intentar usar streamlit-calendar si está disponible
    try:
        from streamlit_calendar import calendar as st_calendar

        COLOR_MAP = {
            "inicio": "#4CAF50",
            "vencimiento": "#e53935",
            "renovacion": "#FF9800",
            "pago": "#2196F3",
            "hito": "#9C27B0",
        }

        cal_events = []
        for ev in events:
            fecha = ev.get("fecha")
            if not fecha:
                continue
            tipo = (ev.get("tipo_evento") or "hito").lower()
            color = COLOR_MAP.get(tipo, "#915BD8")
            cal_events.append({
                "title": f"{ev.get('contrato','?')[:25]} — {ev.get('descripcion','')[:30]}",
                "start": fecha,
                "end": fecha,
                "color": color,
                "extendedProps": {
                    "contrato": ev.get("contrato", ""),
                    "tipo": tipo,
                    "descripcion": ev.get("descripcion", ""),
                }
            })

        cal_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,listMonth"
            },
            "locale": "es",
            "height": 600,
        }

        clicked = st_calendar(events=cal_events, options=cal_options, key="main_calendar")

        # Mostrar detalle del evento clickeado
        if clicked and clicked.get("eventClick"):
            ev_props = clicked["eventClick"].get("event", {})
            ext = ev_props.get("extendedProps", {})
            contrato_name = ext.get("contrato", "")
            st.markdown("---")
            st.subheader(f"Evento: {ev_props.get('title','')}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Contrato:** {contrato_name}")
            c1.markdown(f"**Tipo:** {ext.get('tipo','').upper()}")
            c1.markdown(f"**Descripcion:** {ext.get('descripcion','')}")

            # Previsualizacion del contrato si esta indexado
            if contrato_name in st.session_state.chatbot._indexed_sources:
                with c2:
                    st.markdown("**Vista previa del contrato:**")
                    try:
                        all_docs = st.session_state.chatbot.vectorstore.get(
                            include=["documents", "metadatas"]
                        )
                        docs = all_docs.get("documents", [])
                        metas = all_docs.get("metadatas", [])
                        preview_chunks = [
                            d for d, m in zip(docs, metas)
                            if m and m.get("source") == contrato_name
                        ]
                        if preview_chunks:
                            st.text_area(
                                "preview",
                                value=preview_chunks[0][:600],
                                height=180,
                                disabled=True,
                                label_visibility="collapsed"
                            )
                    except Exception:
                        st.caption("No se pudo cargar la vista previa.")

    except ImportError:
        # Fallback: lista agrupada por mes si streamlit-calendar no está instalado
        st.warning("Instala `streamlit-calendar` para ver el calendario visual. Mostrando lista de eventos.")

        # Agrupar por mes
        from collections import defaultdict
        by_month = defaultdict(list)
        for ev in sorted(events, key=lambda x: x.get("fecha", "")):
            fecha = ev.get("fecha", "")
            if fecha:
                try:
                    d = datetime.date.fromisoformat(fecha)
                    by_month[d.strftime("%Y — %B")].append((d, ev))
                except Exception:
                    pass

        for month_label, month_events in sorted(by_month.items()):
            st.markdown(f"### {month_label}")
            for d, ev in month_events:
                tipo = (ev.get("tipo_evento") or "hito").upper()
                ICONS = {"INICIO": "🟢", "VENCIMIENTO": "🔴", "RENOVACION": "🟠",
                         "PAGO": "🔵", "HITO": "🟣"}
                icon = ICONS.get(tipo, "⚫")
                st.markdown(
                    f"{icon} **{d.strftime('%d/%m/%Y')}** — `{ev.get('contrato','?')[:30]}` "
                    f"({tipo.lower()}) — {ev.get('descripcion','')}"
                )

st.markdown("---")

# ─── Leyenda ─────────────────────────────────────────────────────────────────
st.markdown("**Leyenda de colores:**")
leg_cols = st.columns(5)
leyenda = [("🟢 Inicio", "#4CAF50"), ("🔴 Vencimiento", "#e53935"), ("🟠 Renovacion", "#FF9800"),
           ("🔵 Pago", "#2196F3"), ("🟣 Hito", "#9C27B0")]
for col, (label, _) in zip(leg_cols, leyenda):
    col.caption(label)
