import streamlit as st
import datetime
import re
import json
import io
from collections import defaultdict
from utils.shared import apply_styles, page_header, init_session_state, api_status_banner
from core.llm_service import LLM_AVAILABLE, generate_response

apply_styles()
init_session_state()
page_header()
api_status_banner()

st.markdown("## Calendario Operativo de Contratos")

# ─── Constantes ───────────────────────────────────────────────────────────────
MONTH_ES = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12
}
MONTH_NAME_ES = ["","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
TIPO_KEYWORDS = {
    "vencimiento":["vencimiento","vence","expira","expiración","plazo final"],
    "pago":["pago","factura","cuota","abono","cancelación"],
    "inicio":["inicio","vigencia","entra en vigor","firma","suscripción"],
    "renovacion":["renovación","prórroga","extensión","renovar"],
    "sesion":["sesión","sesion","reunión","junta","asamblea","convocatoria"],
    "resolucion":["resolución","resolucion","acuerdo","aprobó","aprobación"],
    "inscripcion":["inscripción","inscripcion","registro","matrícula"],
}
TIPO_COLOR = {
    "vencimiento":"#e53935","pago":"#2196F3","inicio":"#4CAF50",
    "renovacion":"#FF9800","sesion":"#673AB7","resolucion":"#00796B",
    "inscripcion":"#455A64","hito":"#9C27B0","otro":"#607D8B",
}
TIPO_ICON = {
    "vencimiento":"🔴","pago":"🔵","inicio":"🟢","renovacion":"🟠",
    "sesion":"📋","resolucion":"⚖️","inscripcion":"📝","hito":"🟣","otro":"⚫",
}
ORIGEN_BADGE = {
    "manual": ("✋","#E91E63","Manual"),
    "regex":  ("🔤","#607D8B","Texto"),
    "ia":     ("✨","#915BD8","IA"),
}
_CAL_EVENTS_FILE = "_pactora_calendar_events.json"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _badge(origen: str) -> str:
    icon, bg, label = ORIGEN_BADGE.get(origen, ("🔤","#607D8B","Texto"))
    return (f'<span style="background:{bg};color:white;border-radius:4px;'
            f'padding:1px 6px;font-size:10px;">{icon} {label}</span>')


def _infer_tipo(text_lower: str) -> str:
    for tipo, kws in TIPO_KEYWORDS.items():
        if any(k in text_lower for k in kws):
            return tipo
    return "hito"


def _get_all_text(src: str) -> str:
    try:
        r = st.session_state.chatbot.vectorstore.get(include=["documents","metadatas"])
        return " ".join(d for d,m in zip(r.get("documents",[]),r.get("metadatas",[]))
                        if m and m.get("source")==src)
    except Exception:
        return ""


def _extract_dates(text: str, source: str, origen: str = "regex") -> list:
    events, seen = [], set()
    for sent in re.split(r'[.;\n]', text):
        s = sent.lower().strip()
        if not s:
            continue
        for m in re.finditer(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', sent):
            try:
                d = datetime.date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
                if 2000<=d.year<=2050:
                    _add_ev(events,seen,source,d,_infer_tipo(s),sent.strip()[:80],origen)
            except ValueError: pass
        for m in re.finditer(r'\b(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b', sent):
            try:
                d = datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
                if 2000<=d.year<=2050:
                    _add_ev(events,seen,source,d,_infer_tipo(s),sent.strip()[:80],origen)
            except ValueError: pass
        for m in re.finditer(r'\b(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})\b', s):
            try:
                mon = MONTH_ES.get(m.group(2))
                d = datetime.date(int(m.group(3)),mon,int(m.group(1)))
                if mon and 2000<=d.year<=2050:
                    _add_ev(events,seen,source,d,_infer_tipo(s),sent.strip()[:80],origen)
            except (ValueError,TypeError): pass
    return events


def _add_ev(lst, seen, contrato, fecha, tipo, desc, origen):
    key = (fecha.isoformat(), contrato[:20])
    if key not in seen:
        seen.add(key)
        lst.append({"contrato":contrato,"fecha":fecha.isoformat(),
                    "tipo_evento":tipo,"descripcion":desc,"origen":origen})


# ─── Drive persistence para eventos manuales ──────────────────────────────────
def _save_manual_events() -> bool:
    root = st.session_state.get("drive_root_id","")
    if not root:
        return False
    try:
        from utils.auth_helper import get_drive_service
        from googleapiclient.http import MediaIoBaseUpload
        svc = get_drive_service()
        if not svc:
            return False
        manual = [e for e in st.session_state.get("contract_events",[])
                  if e.get("origen")=="manual"]
        data = json.dumps(manual, ensure_ascii=False, indent=2).encode()
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/json", resumable=False)
        q = f"name='{_CAL_EVENTS_FILE}' and '{root}' in parents and trashed=false"
        ex = svc.files().list(q=q, fields="files(id)",
                              supportsAllDrives=True, includeItemsFromAllDrives=True
                              ).execute().get("files",[])
        if ex:
            svc.files().update(fileId=ex[0]["id"], media_body=media).execute()
        else:
            svc.files().create(body={"name":_CAL_EVENTS_FILE,"parents":[root]},
                               media_body=media, fields="id",
                               supportsAllDrives=True).execute()
        return True
    except Exception as e:
        import logging; logging.getLogger("pactora").warning("[cal] save manual: %s",e)
        return False


def _load_manual_events() -> list:
    root = st.session_state.get("drive_root_id","")
    if not root or st.session_state.get("_cal_manual_loaded"):
        return []
    try:
        from utils.auth_helper import get_drive_service
        from utils.drive_manager import _do_download
        svc = get_drive_service()
        if not svc:
            return []
        q = f"name='{_CAL_EVENTS_FILE}' and '{root}' in parents and trashed=false"
        found = svc.files().list(q=q, fields="files(id)",
                                 supportsAllDrives=True, includeItemsFromAllDrives=True
                                 ).execute().get("files",[])
        if not found:
            return []
        raw = _do_download(svc, found[0]["id"]).read()
        st.session_state["_cal_manual_loaded"] = True
        return json.loads(raw)
    except Exception:
        return []


# ─── Startup: cargar manuales + auto-extraer ──────────────────────────────────
if not st.session_state.get("_cal_manual_loaded"):
    _manual = _load_manual_events()
    if _manual:
        existing = st.session_state.get("contract_events",[])
        _existing_keys = {(e["fecha"],e["contrato"][:20]) for e in existing}
        for me in _manual:
            k = (me.get("fecha",""), me.get("contrato","")[:20])
            if k not in _existing_keys:
                existing.append(me)
        st.session_state.contract_events = existing

stats = st.session_state.chatbot.get_stats()
sources = stats.get("sources",[])

if sources and not st.session_state.get("contract_events"):
    with st.spinner(f"Extrayendo fechas de {len(sources)} contrato(s)..."):
        _evs = []
        for src in sources:
            txt = _get_all_text(src)
            if txt:
                _evs.extend(_extract_dates(txt, src, "regex"))
        st.session_state.contract_events = _evs
    if _evs:
        st.toast(f"{len(_evs)} fecha(s) extraída(s).", icon="📅")

# ─── Barra de herramientas ────────────────────────────────────────────────────
tool_row = st.columns([4,4,1])
with tool_row[0]:
    if sources and st.button("🔄 Re-extraer fechas", type="primary", width="stretch"):
        _manual_ev = [e for e in st.session_state.get("contract_events",[])
                      if e.get("origen")=="manual"]
        _new_evs = list(_manual_ev)
        prog = st.progress(0)
        for i,src in enumerate(sources):
            txt = _get_all_text(src)
            if txt:
                _new_evs.extend(_extract_dates(txt, src, "regex"))
            prog.progress((i+1)/len(sources))
        prog.empty()
        st.session_state.contract_events = _new_evs
        st.success(f"✅ {len(_new_evs)} fecha(s) extraída(s).")
        st.rerun()
with tool_row[1]:
    if st.session_state.get("contract_events"):
        if st.button("🗑 Limpiar eventos (no manuales)", width="stretch"):
            st.session_state.contract_events = [
                e for e in st.session_state.contract_events if e.get("origen")=="manual"
            ]
            st.rerun()
with tool_row[2]:
    with st.popover("ℹ️"):
        st.markdown("Detecta fechas con regex (dd/mm/yyyy, yyyy-mm-dd, 'dd de mes de yyyy') "
                    "e infiere el tipo por palabras clave.\n\n"
                    + ("✨ *IA disponible para enriquecimiento semántico.*" if LLM_AVAILABLE
                       else "*Activa Gemini para extracción semántica.*"))

# Extracción con IA
if LLM_AVAILABLE and sources:
    with st.expander("✨ Enriquecer con IA", expanded=False):
        srcs_ia = st.multiselect("Contratos a analizar", options=sources,
                                 default=sources[:3], key="cal_ia_srcs")
        if st.button("✨ Extraer con IA", type="primary", width="stretch", key="btn_cal_ia"):
            if srcs_ia:
                _ia_evs = list(st.session_state.get("contract_events",[]))
                _ia_new = 0
                with st.status("Analizando con Gemini...", expanded=True) as _st:
                    for _src in srcs_ia:
                        st.write(f"📄 {_src}...")
                        _txt = _get_all_text(_src)
                        if not _txt:
                            continue
                        _p = (f"Extrae TODAS las fechas importantes del documento. "
                              f"Responde SOLO con JSON array:\n"
                              f'[{{"fecha":"YYYY-MM-DD","tipo_evento":"vencimiento|pago|inicio|'
                              f'renovacion|sesion|resolucion|inscripcion|hito",'
                              f'"descripcion":"max 80 chars"}}]\n\n'
                              f"DOCUMENTO ({_src}):\n{_txt[:4000]}")
                        try:
                            _r = generate_response(_p, context="")
                            _jm = re.search(r'\[[\s\S]*\]', _r) if _r else None
                            if _jm:
                                _ex_keys = {(e["fecha"],e["contrato"][:20]) for e in _ia_evs}
                                for _ev in json.loads(_jm.group()):
                                    k = (_ev.get("fecha",""), _src[:20])
                                    if k not in _ex_keys:
                                        _ia_evs.append({"contrato":_src,"fecha":_ev.get("fecha",""),
                                                        "tipo_evento":_ev.get("tipo_evento","hito"),
                                                        "descripcion":_ev.get("descripcion","")[:80],
                                                        "origen":"ia"})
                                        _ex_keys.add(k); _ia_new+=1
                                st.write(f"  ✅ {len(json.loads(_jm.group()))} fecha(s)")
                            else:
                                st.write("  ⚠️ Sin fechas detectadas")
                        except Exception as _ex:
                            st.write(f"  ❌ {str(_ex)[:60]}")
                    st.session_state.contract_events = _ia_evs
                    _st.update(label=f"✅ {_ia_new} fecha(s) nuevas", state="complete", expanded=False)
                if _ia_new > 0:
                    st.rerun()

# Leyenda
_leg = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0;">'
for t,c in TIPO_COLOR.items():
    _leg += (f'<span style="background:{c};color:white;border-radius:4px;'
             f'padding:2px 8px;font-size:11px;">{TIPO_ICON.get(t,"⚫")} {t.capitalize()}</span>')
_leg += '</div>'
st.markdown(_leg, unsafe_allow_html=True)
st.markdown("---")

events = st.session_state.get("contract_events",[])

# ─── Calendario visual ────────────────────────────────────────────────────────
try:
    from streamlit_calendar import calendar as st_calendar
    cal_events = []
    for ev in events:
        if not ev.get("fecha"):
            continue
        tipo = ev.get("tipo_evento","hito")
        color = TIPO_COLOR.get(tipo,"#915BD8")
        origen = ev.get("origen","regex")
        ce = {
            "title": f"{'✋ ' if origen=='manual' else ''}{ev.get('contrato','')[:18]} — {ev.get('descripcion','')[:22]}",
            "start": ev["fecha"], "end": ev["fecha"], "color": color,
            "extendedProps": {"contrato":ev.get("contrato",""),"tipo":tipo,
                              "descripcion":ev.get("descripcion",""),"origen":origen},
        }
        if origen == "manual":
            ce["borderColor"] = "#E91E63"
        cal_events.append(ce)

    cal_options = {
        "initialView":"dayGridMonth",
        "headerToolbar":{"left":"prev,next today","center":"title","right":"dayGridMonth,timeGridWeek,listMonth"},
        "locale":"es","height":540,
    }
    clicked = st_calendar(events=cal_events, options=cal_options, key="main_cal")

    if clicked and clicked.get("eventClick"):
        ev_data = clicked["eventClick"].get("event",{})
        ep = ev_data.get("extendedProps",{})
        st.markdown("---")
        c1,c2 = st.columns(2)
        with c1:
            st.markdown(f"**Contrato:** {ep.get('contrato','')}  ")
            st.markdown(f"**Tipo:** {ep.get('tipo','').upper()}  {_badge(ep.get('origen','regex'))}", unsafe_allow_html=True)
            st.markdown(f"**Descripción:** {ep.get('descripcion','')}")
        with c2:
            src = ep.get("contrato","")
            if src in (st.session_state.chatbot._indexed_sources or []):
                from utils.shared import render_document_preview
                render_document_preview(src, height=300)
except ImportError:
    st.warning("`streamlit-calendar` no disponible — mostrando lista.")
    by_month = defaultdict(list)
    for ev in sorted(events, key=lambda x: x.get("fecha","")):
        try:
            d = datetime.date.fromisoformat(ev["fecha"])
            by_month[d.strftime("%Y — %B")].append((d,ev))
        except Exception: pass
    for ml, mes_evs in sorted(by_month.items()):
        st.markdown(f"### {ml}")
        for d,ev in mes_evs:
            tipo = ev.get("tipo_evento","hito")
            st.markdown(
                f'<div style="border-left:3px solid {TIPO_COLOR.get(tipo,"#915BD8")};'
                f'padding:6px 10px;margin-bottom:4px;border-radius:0 6px 6px 0;">'
                f'{TIPO_ICON.get(tipo,"⚫")} <b>{d.strftime("%d/%m/%Y")}</b> — '
                f'{ev.get("contrato","")[:30]} {_badge(ev.get("origen","regex"))}</div>',
                unsafe_allow_html=True)

st.markdown("---")

# ─── Tabs: Próximos / Pasados / Resumen / Agregar ─────────────────────────────
today = datetime.date.today()
upcoming, past = [], []
for ev in events:
    try:
        d = datetime.date.fromisoformat(ev.get("fecha",""))
        (upcoming if d>=today else past).append((d,ev))
    except Exception: pass
upcoming.sort(key=lambda x: x[0])
past.sort(key=lambda x: x[0], reverse=True)

tab_upcom, tab_past, tab_resumen, tab_add = st.tabs([
    f"Próximos ({len(upcoming)})",
    f"Pasados ({len(past)})",
    "📊 Resumen",
    "➕ Agregar evento",
])

# ── Próximos ──────────────────────────────────────────────────────────────────
with tab_upcom:
    if not upcoming:
        st.caption("No hay eventos futuros detectados.")
    else:
        _groups = [
            ("HOY","#e53935",   [x for x in upcoming if (x[0]-today).days==0]),
            ("Esta semana","#f57c00", [x for x in upcoming if 1<=(x[0]-today).days<=7]),
            ("Este mes","#f9a825",    [x for x in upcoming if 8<=(x[0]-today).days<=30]),
            ("Próximos 90 días","#607D8B",[x for x in upcoming if 31<=(x[0]-today).days<=90]),
            ("Más adelante","#9d87c0",[x for x in upcoming if (x[0]-today).days>90]),
        ]
        _shown = set()
        for grp_label, grp_color, grp_items in _groups:
            if not grp_items:
                continue
            st.markdown(
                f'<div style="background:{grp_color}22;border-left:4px solid {grp_color};'
                f'padding:4px 12px;border-radius:0 6px 6px 0;margin:10px 0 4px 0;'
                f'font-weight:700;font-size:13px;color:{grp_color};">{grp_label} — {len(grp_items)} evento(s)</div>',
                unsafe_allow_html=True)
            for d,ev in grp_items[:10]:
                _id = id(ev)
                if _id in _shown: continue
                _shown.add(_id)
                diff = (d-today).days
                tipo = ev.get("tipo_evento","hito")
                color = TIPO_COLOR.get(tipo,"#915BD8")
                origen = ev.get("origen","regex")
                contrato = ev.get("contrato","")
                c1,c2 = st.columns([6,1])
                with c1:
                    badge_t = f"HOY" if diff==0 else f"{diff}d"
                    st.markdown(
                        f'<div style="border-left:3px solid {color};padding:8px 12px;'
                        f'margin-bottom:4px;border-radius:0 6px 6px 0;">'
                        f'<span style="font-weight:700;">{TIPO_ICON.get(tipo,"⚫")} '
                        f'{d.strftime("%d/%m/%Y")}</span> '
                        f'<span style="background:{color};color:white;border-radius:3px;'
                        f'padding:1px 5px;font-size:10px;">{badge_t}</span> '
                        f'{_badge(origen)}<br>'
                        f'<span style="font-size:12px;">{contrato[:50]}</span><br>'
                        f'<span style="font-size:11px;color:#777;">{ev.get("descripcion","")[:80]}</span>'
                        f'</div>', unsafe_allow_html=True)
                with c2:
                    if contrato in (st.session_state.chatbot._indexed_sources or []):
                        if st.button("📚", key=f"upv_{_id}", help="Ver en Biblioteca"):
                            st.session_state["library_selected"] = contrato
                            st.switch_page("pages/biblioteca.py")
                    if origen == "manual":
                        if st.button("🗑", key=f"del_{_id}", help="Eliminar evento"):
                            st.session_state["_del_ev_id"] = _id
                            st.session_state.contract_events = [
                                e for e in st.session_state.contract_events if id(e)!=_id
                            ]
                            _save_manual_events()
                            st.rerun()

# ── Pasados ───────────────────────────────────────────────────────────────────
with tab_past:
    if not past:
        st.caption("No hay eventos pasados detectados.")
    else:
        by_month_past = defaultdict(list)
        for d,ev in past[:30]:
            by_month_past[f"{MONTH_NAME_ES[d.month]} {d.year}"].append((d,ev))
        for ml in list(by_month_past.keys()):
            st.markdown(f"**{ml}**")
            for d,ev in by_month_past[ml]:
                tipo = ev.get("tipo_evento","hito")
                diff = (today-d).days
                origen = ev.get("origen","regex")
                st.markdown(
                    f'<div style="border-left:3px solid {TIPO_COLOR.get(tipo,"#915BD8")};'
                    f'padding:6px 10px;margin-bottom:3px;border-radius:0 6px 6px 0;opacity:0.75;">'
                    f'{TIPO_ICON.get(tipo,"⚫")} <b>{d.strftime("%d/%m/%Y")}</b> '
                    f'<span style="color:#999;">hace {diff}d</span> — '
                    f'{ev.get("contrato","")[:30]} {_badge(origen)}<br>'
                    f'<span style="font-size:11px;color:#777;">{ev.get("descripcion","")[:70]}</span>'
                    f'</div>', unsafe_allow_html=True)
        if len(past) > 30:
            st.caption(f"Mostrando 30 de {len(past)} eventos pasados.")

# ── Resumen ───────────────────────────────────────────────────────────────────
with tab_resumen:
    if not events:
        st.info("Sin eventos para resumir.")
    else:
        _r1, _r2, _r3 = st.columns(3)
        _r1.metric("Total eventos", len(events))
        _r2.metric("Próximos", len(upcoming))
        _r3.metric("Pasados", len(past))

        # Por tipo
        _tipo_count = defaultdict(int)
        for ev in events:
            _tipo_count[ev.get("tipo_evento","hito")] += 1
        st.markdown("**Por tipo:**")
        _tc_cols = st.columns(min(len(_tipo_count),4))
        for i,(t,n) in enumerate(sorted(_tipo_count.items(), key=lambda x:-x[1])):
            _tc_cols[i%4].markdown(
                f'<div style="background:{TIPO_COLOR.get(t,"#915BD8")}22;border-radius:8px;'
                f'padding:8px;text-align:center;margin-bottom:4px;">'
                f'<div style="font-size:20px;">{TIPO_ICON.get(t,"⚫")}</div>'
                f'<div style="font-weight:700;">{n}</div>'
                f'<div style="font-size:11px;">{t.capitalize()}</div></div>',
                unsafe_allow_html=True)

        # Por origen
        st.markdown("**Por origen:**")
        _orig_count = defaultdict(int)
        for ev in events:
            _orig_count[ev.get("origen","regex")] += 1
        _oc_html = '<div style="display:flex;gap:10px;margin-bottom:8px;">'
        for orig,cnt in _orig_count.items():
            icon,bg,label = ORIGEN_BADGE.get(orig,("🔤","#607D8B","Texto"))
            _oc_html += (f'<span style="background:{bg};color:white;border-radius:6px;'
                         f'padding:4px 10px;font-size:12px;">{icon} {label}: <b>{cnt}</b></span>')
        _oc_html += '</div>'
        st.markdown(_oc_html, unsafe_allow_html=True)

        # Próximo evento crítico
        _prox = [x for x in upcoming if x[1].get("tipo_evento") in ("vencimiento","pago","renovacion")]
        if _prox:
            d_c, ev_c = _prox[0]
            diff_c = (d_c-today).days
            st.markdown(
                f'<div style="background:#fff8f0;border:1px solid #ffcc80;border-radius:8px;'
                f'padding:10px 14px;margin-top:8px;">'
                f'<b>Próximo evento crítico:</b> {ev_c.get("contrato","")[:40]}<br>'
                f'{d_c.strftime("%d/%m/%Y")} — {ev_c.get("tipo_evento","").upper()} — en {diff_c} día(s)'
                f'</div>', unsafe_allow_html=True)

# ── Agregar evento manual ─────────────────────────────────────────────────────
with tab_add:
    st.markdown("#### Agregar evento manualmente")
    with st.form("form_add_event", clear_on_submit=True):
        f_fecha = st.date_input("Fecha del evento", value=today, key="form_fecha")
        f_tipo = st.selectbox("Tipo de evento", options=[
            "vencimiento","pago","inicio","renovacion","sesion","resolucion","inscripcion","hito","otro"
        ], key="form_tipo")
        _contrato_opts = ["Sin contrato asociado / General"] + sources
        f_contrato = st.selectbox("Contrato asociado", options=_contrato_opts, key="form_contrato")
        f_desc = st.text_input("Descripción (máx. 120 chars)", max_chars=120, key="form_desc")
        submitted = st.form_submit_button("➕ Agregar evento", type="primary")

    if submitted:
        _contrato_val = "" if f_contrato == "Sin contrato asociado / General" else f_contrato
        # Validar duplicado
        _new_key = (f_fecha.isoformat(), _contrato_val[:20], f_desc[:20])
        _existing_events = st.session_state.get("contract_events",[])
        _dup = any(
            (e.get("fecha")==f_fecha.isoformat() and
             e.get("contrato","")[:20]==_contrato_val[:20] and
             e.get("descripcion","")[:20]==f_desc[:20])
            for e in _existing_events
        )
        if _dup:
            st.warning("Ya existe un evento con la misma fecha, contrato y descripción.")
        else:
            _new_ev = {
                "contrato": _contrato_val,
                "fecha": f_fecha.isoformat(),
                "tipo_evento": f_tipo,
                "descripcion": f_desc[:120],
                "origen": "manual",
            }
            _existing_events.append(_new_ev)
            st.session_state.contract_events = _existing_events
            _saved = _save_manual_events()
            st.success(f"✅ Evento agregado{' y guardado en Drive' if _saved else ' (sin Drive configurado)'}.")
            st.rerun()

    # Lista de eventos manuales existentes con editar/eliminar
    _manual_evs = [(i,e) for i,e in enumerate(st.session_state.get("contract_events",[]))
                   if e.get("origen")=="manual"]
    if _manual_evs:
        st.markdown(f"**Eventos manuales existentes ({len(_manual_evs)}):**")
        for idx, ev in _manual_evs:
            cols = st.columns([5,1,1])
            with cols[0]:
                st.markdown(
                    f'<div style="border-left:3px solid #E91E63;padding:5px 10px;'
                    f'border-radius:0 6px 6px 0;margin-bottom:3px;">'
                    f'✋ <b>{ev.get("fecha","")}</b> — {ev.get("tipo_evento","").upper()}<br>'
                    f'<span style="font-size:12px;">{ev.get("contrato","") or "(sin contrato)"}</span><br>'
                    f'<span style="font-size:11px;color:#777;">{ev.get("descripcion","")}</span>'
                    f'</div>', unsafe_allow_html=True)
            with cols[1]:
                if st.button("✏️", key=f"edit_{idx}", help="Editar"):
                    st.session_state["_editing_ev_idx"] = idx
            with cols[2]:
                if st.button("🗑", key=f"deladm_{idx}", help="Eliminar"):
                    st.session_state.contract_events.pop(idx)
                    _save_manual_events()
                    st.rerun()

        # Formulario de edición inline
        _edit_idx = st.session_state.get("_editing_ev_idx")
        if _edit_idx is not None and _edit_idx < len(st.session_state.contract_events):
            _ev_edit = st.session_state.contract_events[_edit_idx]
            st.markdown("**Editando evento:**")
            with st.form("form_edit_event"):
                ef_fecha = st.date_input("Fecha", value=datetime.date.fromisoformat(_ev_edit.get("fecha",today.isoformat())))
                ef_tipo = st.selectbox("Tipo", options=list(TIPO_COLOR.keys()),
                                       index=list(TIPO_COLOR.keys()).index(_ev_edit.get("tipo_evento","hito")))
                ef_desc = st.text_input("Descripción", value=_ev_edit.get("descripcion",""), max_chars=120)
                ec1,ec2 = st.columns(2)
                if ec1.form_submit_button("💾 Guardar cambios", type="primary"):
                    st.session_state.contract_events[_edit_idx].update({
                        "fecha": ef_fecha.isoformat(),
                        "tipo_evento": ef_tipo,
                        "descripcion": ef_desc,
                    })
                    _save_manual_events()
                    del st.session_state["_editing_ev_idx"]
                    st.rerun()
                if ec2.form_submit_button("✖ Cancelar"):
                    del st.session_state["_editing_ev_idx"]
                    st.rerun()
