import streamlit as st
import datetime
import re
from collections import defaultdict
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Calendario Operativo de Contratos")
st.caption("Extrae y visualiza las fechas importantes de los contratos: vencimientos, pagos, renovaciones e hitos.")

# ─── Helpers de extracción local ──────────────────────────────────────────────
MONTH_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

TIPO_KEYWORDS = {
    "vencimiento": ["vencimiento", "vence", "expira", "expiración", "expirar", "plazo final"],
    "pago": ["pago", "factura", "cuota", "abono", "cancelación"],
    "inicio": ["inicio", "vigencia", "entra en vigor", "firma", "suscripción"],
    "renovacion": ["renovación", "prórroga", "extensión", "renovar"],
}

TIPO_COLOR = {
    "vencimiento": "#e53935",
    "pago": "#2196F3",
    "inicio": "#4CAF50",
    "renovacion": "#FF9800",
    "hito": "#9C27B0",
}

TIPO_ICON = {
    "vencimiento": "🔴",
    "pago": "🔵",
    "inicio": "🟢",
    "renovacion": "🟠",
    "hito": "🟣",
}


def _extract_dates_from_text(text, source_name):
    """Extrae fechas del texto usando regex. Retorna lista de eventos."""
    events = []
    sentences = re.split(r'[.;\n]', text)

    for sent in sentences:
        sent_lower = sent.lower().strip()
        if not sent_lower:
            continue

        # Patrón 1: dd/mm/yyyy o dd-mm-yyyy
        for m in re.finditer(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', sent):
            try:
                day, mon, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1 <= mon <= 12 and 1 <= day <= 31 and 2000 <= year <= 2050:
                    fecha = datetime.date(year, mon, day)
                    tipo = _infer_tipo(sent_lower)
                    events.append({
                        "contrato": source_name,
                        "fecha": fecha.isoformat(),
                        "tipo_evento": tipo,
                        "descripcion": sent.strip()[:80],
                    })
            except ValueError:
                pass

        # Patrón 2: yyyy-mm-dd
        for m in re.finditer(r'\b(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b', sent):
            try:
                year, mon, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1 <= mon <= 12 and 1 <= day <= 31 and 2000 <= year <= 2050:
                    fecha = datetime.date(year, mon, day)
                    tipo = _infer_tipo(sent_lower)
                    events.append({
                        "contrato": source_name,
                        "fecha": fecha.isoformat(),
                        "tipo_evento": tipo,
                        "descripcion": sent.strip()[:80],
                    })
            except ValueError:
                pass

        # Patrón 3: dd de [mes] de yyyy
        for m in re.finditer(
            r'\b(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})\b', sent_lower
        ):
            try:
                day = int(m.group(1))
                mon = MONTH_ES.get(m.group(2))
                year = int(m.group(3))
                if mon and 1 <= day <= 31 and 2000 <= year <= 2050:
                    fecha = datetime.date(year, mon, day)
                    tipo = _infer_tipo(sent_lower)
                    events.append({
                        "contrato": source_name,
                        "fecha": fecha.isoformat(),
                        "tipo_evento": tipo,
                        "descripcion": sent.strip()[:80],
                    })
            except (ValueError, TypeError):
                pass

    # Deduplicar por fecha+contrato
    seen = set()
    unique = []
    for e in events:
        key = (e["fecha"], e["contrato"][:20])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def _infer_tipo(text_lower):
    for tipo, keywords in TIPO_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return tipo
    return "hito"


def _get_all_text(src):
    try:
        all_docs = st.session_state.chatbot.vectorstore.get(include=["documents", "metadatas"])
        return " ".join(
            d for d, m in zip(all_docs.get("documents", []), all_docs.get("metadatas", []))
            if m and m.get("source") == src
        )
    except Exception:
        return ""


# ─── Panel de control ─────────────────────────────────────────────────────────
stats = st.session_state.chatbot.get_stats()
sources = stats.get("sources", [])

# Auto-extracción al entrar si hay contratos y aún no hay eventos en sesión
if sources and not st.session_state.get("contract_events"):
    with st.spinner(f"Extrayendo fechas de {len(sources)} contrato(s)..."):
        _auto_events = []
        for src in sources:
            text = _get_all_text(src)
            if text:
                _auto_events.extend(_extract_dates_from_text(text, src))
        st.session_state.contract_events = _auto_events
    if _auto_events:
        st.toast(f"{len(_auto_events)} fecha(s) extraída(s) automáticamente.", icon="📅")

tool_row = st.columns([4, 4, 1])
with tool_row[0]:
    if sources:
        if st.button("🔄 Re-extraer fechas", type="primary", use_container_width=True):
            all_events = []
            progress = st.progress(0)
            for i, src in enumerate(sources):
                text = _get_all_text(src)
                if text:
                    evs = _extract_dates_from_text(text, src)
                    all_events.extend(evs)
                progress.progress((i + 1) / len(sources))
            progress.empty()
            st.session_state.contract_events = all_events
            st.success(f"✅ {len(all_events)} fecha(s) extraída(s) de {len(sources)} contrato(s).")
            st.rerun()
    else:
        st.info("Carga contratos en **Ajustes** para extraer fechas.")

with tool_row[1]:
    if st.session_state.get("contract_events"):
        if st.button("🗑 Limpiar eventos", use_container_width=True):
            st.session_state.contract_events = []
            st.rerun()

with tool_row[2]:
    with st.popover("ℹ️"):
        st.markdown(
            "**Cómo funciona:**\n\n"
            "La extracción de fechas analiza el texto de cada contrato usando patrones "
            "de expresiones regulares (sin IA). Detecta fechas en formatos:\n\n"
            "- `dd/mm/yyyy` o `dd-mm-yyyy`\n"
            "- `yyyy-mm-dd`\n"
            "- `dd de [mes] de yyyy`\n\n"
            "El tipo de evento se infiere según palabras clave cercanas a la fecha "
            "(vencimiento, pago, inicio, renovación).\n\n"
            "🔮 *Próximamente: extracción semántica con IA para mayor precisión.*"
        )

# ─── Leyenda ──────────────────────────────────────────────────────────────────
leg_cols = st.columns(5)
for col, (tipo, color) in zip(leg_cols, TIPO_COLOR.items()):
    icon = TIPO_ICON[tipo]
    col.markdown(
        f'<span style="background:{color};color:white;border-radius:4px;'
        f'padding:2px 8px;font-size:11px;">{icon} {tipo.capitalize()}</span>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ─── Vista del calendario ─────────────────────────────────────────────────────
events = st.session_state.get("contract_events", [])

if not events:
    if sources:
        st.info("Haz clic en **Extraer fechas de contratos** para poblar el calendario.")
    # Mostrar calendario vacío con streamlit-calendar
    try:
        from streamlit_calendar import calendar as st_calendar
        cal_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,listMonth"
            },
            "locale": "es",
            "height": 500,
        }
        st_calendar(events=[], options=cal_options, key="cal_empty")
    except ImportError:
        st.caption("Instala `streamlit-calendar` para ver el calendario visual.")
else:
    # Intentar componente streamlit-calendar
    try:
        from streamlit_calendar import calendar as st_calendar

        cal_events = []
        for ev in events:
            fecha = ev.get("fecha")
            if not fecha:
                continue
            tipo = ev.get("tipo_evento", "hito")
            color = TIPO_COLOR.get(tipo, "#915BD8")
            cal_events.append({
                "title": f"{ev.get('contrato','')[:20]} — {ev.get('descripcion','')[:25]}",
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
            "height": 550,
        }
        clicked = st_calendar(events=cal_events, options=cal_options, key="main_cal")

        # Detalle del evento clickeado
        if clicked and clicked.get("eventClick"):
            ev_data = clicked["eventClick"].get("event", {})
            ext_props = ev_data.get("extendedProps", {})
            st.markdown("---")
            st.subheader(f"Evento: {ev_data.get('title', '')}")
            dc1, dc2 = st.columns(2)
            dc1.markdown(f"**Contrato:** {ext_props.get('contrato', '')}")
            dc1.markdown(f"**Tipo:** {ext_props.get('tipo', '').upper()}")
            dc1.markdown(f"**Descripción:** {ext_props.get('descripcion', '')}")

            src = ext_props.get("contrato", "")
            if src in (st.session_state.chatbot._indexed_sources or []):
                with dc2:
                    st.markdown("**Vista previa del contrato:**")
                    try:
                        all_docs = st.session_state.chatbot.vectorstore.get(
                            include=["documents", "metadatas"]
                        )
                        chunks = [
                            d for d, m in zip(
                                all_docs.get("documents", []), all_docs.get("metadatas", [])
                            )
                            if m and m.get("source") == src
                        ]
                        if chunks:
                            st.text_area(
                                "cal_prev", value=chunks[0][:500], height=150,
                                disabled=True, label_visibility="collapsed"
                            )
                    except Exception:
                        st.caption("No se pudo cargar la vista previa.")

    except ImportError:
        # Fallback: lista agrupada por mes
        st.warning("`streamlit-calendar` no disponible — mostrando lista de eventos.")
        by_month = defaultdict(list)
        for ev in sorted(events, key=lambda x: x.get("fecha", "")):
            fecha = ev.get("fecha", "")
            if fecha:
                try:
                    d = datetime.date.fromisoformat(fecha)
                    by_month[d.strftime("%Y — %B")].append((d, ev))
                except Exception:
                    pass

        for month_label, month_evs in sorted(by_month.items()):
            st.markdown(f"### {month_label}")
            for d, ev in month_evs:
                tipo = (ev.get("tipo_evento") or "hito")
                icon = TIPO_ICON.get(tipo, "⚫")
                color = TIPO_COLOR.get(tipo, "#915BD8")
                st.markdown(
                    f'<div style="border-left:3px solid {color};padding:6px 10px;'
                    f'margin-bottom:4px;border-radius:0 6px 6px 0;background:white;">'
                    f'{icon} <b>{d.strftime("%d/%m/%Y")}</b> — '
                    f'<code>{ev.get("contrato","")[:30]}</code> — '
                    f'{ev.get("descripcion","")[:50]}'
                    f'</div>',
                    unsafe_allow_html=True
                )

    st.markdown("---")

    # Tabla resumen de próximos eventos
    res_hrow = st.columns([9, 1])
    res_hrow[0].markdown("#### Próximos eventos")
    with res_hrow[1].popover("ℹ️"):
        st.markdown("Lista de eventos futuros ordenados por fecha, con días restantes.")

    today = datetime.date.today()
    upcoming = []
    past = []
    for ev in events:
        try:
            d = datetime.date.fromisoformat(ev.get("fecha", ""))
            if d >= today:
                upcoming.append((d, ev))
            else:
                past.append((d, ev))
        except Exception:
            pass

    upcoming.sort(key=lambda x: x[0])
    past.sort(key=lambda x: x[0], reverse=True)

    tab_upcom, tab_past = st.tabs([
        f"Próximos ({len(upcoming)})",
        f"Pasados ({len(past)})"
    ])

    with tab_upcom:
        if not upcoming:
            st.caption("No hay eventos futuros detectados.")
        for d, ev in upcoming[:20]:
            diff = (d - today).days
            tipo = ev.get("tipo_evento", "hito")
            color = TIPO_COLOR.get(tipo, "#915BD8")
            icon = TIPO_ICON.get(tipo, "⚫")
            label = "Hoy" if diff == 0 else f"en {diff} día(s)"
            st.markdown(
                f'<div style="border-left:3px solid {color};padding:8px 12px;'
                f'margin-bottom:6px;border-radius:0 6px 6px 0;background:white;'
                f'display:flex;justify-content:space-between;align-items:center;">'
                f'<div>'
                f'{icon} <b>{d.strftime("%d/%m/%Y")}</b> — {ev.get("contrato","")[:30]}<br>'
                f'<span style="font-size:12px;color:#666;">{ev.get("descripcion","")[:60]}</span>'
                f'</div>'
                f'<span style="color:{color};font-weight:700;white-space:nowrap;margin-left:8px;">{label}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    with tab_past:
        if not past:
            st.caption("No hay eventos pasados detectados.")
        for d, ev in past[:10]:
            diff = (today - d).days
            tipo = ev.get("tipo_evento", "hito")
            color = TIPO_COLOR.get(tipo, "#915BD8")
            icon = TIPO_ICON.get(tipo, "⚫")
            st.markdown(
                f'<div style="border-left:3px solid {color};padding:8px 12px;'
                f'margin-bottom:4px;border-radius:0 6px 6px 0;background:#fafafa;opacity:0.8;">'
                f'{icon} <b>{d.strftime("%d/%m/%Y")}</b> '
                f'<span style="color:#999;">({diff}d atrás)</span> — '
                f'{ev.get("contrato","")[:25]}'
                f'</div>',
                unsafe_allow_html=True
            )
