"""
report_generator.py — Generación de informes PDF para Pactora CLM.
Usa fpdf2 con fuentes built-in (Helvetica) que soportan Latin-1 (español).
"""
from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Any, Dict, List

from fpdf import FPDF

# ─── Paleta Unergy ─────────────────────────────────────────────────────────────
_PURPLE = (145, 91, 216)   # #915BD8
_DARK   = (44, 32, 57)     # #2C2039
_GREEN  = (56, 142, 60)    # #388e3c
_YELLOW = (245, 124, 0)    # #f57c00
_RED    = (229, 57, 53)    # #e53935
_LIGHT  = (250, 248, 247)  # #FDFAF7


def _clean(text: str) -> str:
    """Elimina emojis/símbolos no Latin-1 y formatos Markdown básicos."""
    # Quitar emojis y símbolos Unicode que fpdf no puede renderizar
    cleaned = []
    for ch in text:
        cat = unicodedata.category(ch)
        # Mantener letras, números, puntuación y espacios; quitar símbolos (So, Sm, Sk, Sc)
        if cat.startswith("S") or (cat == "Cn"):
            cleaned.append(" ")
        else:
            cleaned.append(ch)
    text = "".join(cleaned)
    # Markdown → texto plano
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Codificar a Latin-1 para compatibilidad con fuentes Helvetica de fpdf2
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text


def _new_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    return pdf


def _header(pdf: FPDF, title: str, subtitle: str = "") -> None:
    """Dibuja el encabezado Unergy/Pactora."""
    pdf.add_page()
    # Franja superior
    pdf.set_fill_color(*_DARK)
    pdf.rect(0, 0, 210, 22, "F")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(246, 255, 114)   # #F6FF72
    pdf.set_xy(18, 5)
    pdf.cell(0, 12, "PACTORA CLM  |  Unergy", align="L")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 185, 230)
    pdf.set_xy(0, 5)
    pdf.cell(192, 12, datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), align="R")

    pdf.ln(10)
    # Título del informe
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_DARK)
    pdf.multi_cell(0, 9, _clean(title), align="L")
    if subtitle:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(100, 80, 130)
        pdf.multi_cell(0, 6, _clean(subtitle), align="L")
    pdf.ln(4)
    pdf.set_draw_color(*_PURPLE)
    pdf.set_line_width(0.8)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(6)


def _section(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_PURPLE)
    pdf.cell(0, 8, _clean(title), ln=True)
    pdf.set_draw_color(*_PURPLE)
    pdf.set_line_width(0.3)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(*_DARK)


def _body(pdf: FPDF, text: str, size: int = 10) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*_DARK)
    pdf.multi_cell(0, 5.5, _clean(text))
    pdf.ln(2)


def _semaforo_badge(pdf: FPDF, nivel: str, score: int) -> None:
    """Dibuja el recuadro de semáforo de riesgo."""
    nivel = nivel.upper()
    color = {"ROJO": _RED, "AMARILLO": _YELLOW, "VERDE": _GREEN}.get(nivel, _PURPLE)
    label = {"ROJO": "RIESGO ALTO", "AMARILLO": "RIESGO MEDIO", "VERDE": "RIESGO BAJO"}.get(nivel, nivel)
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*color)
    pdf.rounded_rect(18, y, 80, 16, 3, "F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(18, y + 4)
    pdf.cell(80, 8, label, align="C")
    # Compliance score
    pdf.set_text_color(*_DARK)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(110, y + 2)
    pdf.cell(0, 12, f"Compliance: {score}/100")
    pdf.set_xy(x, y + 20)
    pdf.ln(2)


# ─── API pública ───────────────────────────────────────────────────────────────

def generate_risk_report_pdf(analysis_result: Dict[str, Any], contract_name: str) -> bytes:
    """Genera PDF del análisis de riesgo de un contrato."""
    pdf = _new_pdf()
    nivel = analysis_result.get("Nivel", "VERDE")
    score = analysis_result.get("compliance_score", 0)

    _header(
        pdf,
        f"Informe de Riesgo: {contract_name}",
        f"Analisis automatico de riesgo contractual · Pactora CLM",
    )

    # Semaforo
    _section(pdf, "Resultado general")
    _semaforo_badge(pdf, nivel, score)
    pdf.ln(4)

    summary = analysis_result.get("summary", "")
    if summary:
        _body(pdf, summary)

    # Alertas
    alertas = analysis_result.get("Alertas", [])
    if alertas:
        _section(pdf, "Alertas detectadas")
        for a in alertas:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_RED)
            pdf.multi_cell(0, 5.5, f"  * {_clean(a)}")
        pdf.set_text_color(*_DARK)
        pdf.ln(2)

    # Detalle por clausula
    risks = analysis_result.get("risks", [])
    if risks:
        _section(pdf, "Detalle por clausula")
        color_map = {"Rojo": _RED, "Amarillo": _YELLOW, "Verde": _GREEN}
        for r in risks:
            lvl = r.get("level", "Verde").capitalize()
            color = color_map.get(lvl, _PURPLE)
            clausula = _clean(r.get("clause", ""))
            desc = _clean(r.get("description", ""))
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*color)
            pdf.multi_cell(0, 5.5, f"[{lvl.upper()}] {clausula}")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(80, 60, 100)
            pdf.multi_cell(0, 5, f"  {desc}")
            pdf.ln(1)
        pdf.set_text_color(*_DARK)

    # Recomendaciones
    recomendaciones = analysis_result.get("recomendaciones", "")
    if not recomendaciones:
        recomendaciones = analysis_result.get("Recomendaciones", "")
    if recomendaciones:
        _section(pdf, "Recomendaciones")
        _body(pdf, recomendaciones)

    # Pie de pagina
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 130, 170)
    pdf.multi_cell(
        0, 5,
        f"Generado por Pactora CLM · Unergy · {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        "Este informe es orientativo y no constituye asesoramiento legal."
    )

    return bytes(pdf.output())


def generate_comparison_report_pdf(
    contract_a: str,
    contract_b: str,
    similarity_pct: int,
    diff_text: str,
    ia_analysis: str = "",
) -> bytes:
    """Genera PDF del resultado de comparación entre dos contratos."""
    pdf = _new_pdf()

    _header(
        pdf,
        "Informe de Comparacion de Contratos",
        f"{contract_a}  vs.  {contract_b}",
    )

    # Similitud
    _section(pdf, "Indice de similitud")
    color = _GREEN if similarity_pct > 70 else _YELLOW if similarity_pct > 40 else _RED
    pdf.set_fill_color(*color)
    pdf.rounded_rect(18, pdf.get_y(), 60, 14, 3, "F")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(18, pdf.get_y() + 3)
    pdf.cell(60, 8, f"{similarity_pct}% similitud", align="C")
    pdf.ln(18)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_DARK)
    pdf.multi_cell(
        0, 5.5,
        f"Contrato base: {_clean(contract_a)}\nContrato comparado: {_clean(contract_b)}"
    )
    pdf.ln(4)

    # Analisis IA si existe
    if ia_analysis:
        _section(pdf, "Analisis de diferencias (IA)")
        _body(pdf, ia_analysis)

    # Diff textual
    if diff_text:
        _section(pdf, "Diferencias textuales (extracto)")
        pdf.set_font("Courier", "", 8)
        pdf.set_text_color(60, 50, 80)
        # Truncar diff para no hacer el PDF enorme
        for line in diff_text.splitlines()[:120]:
            try:
                pdf.multi_cell(0, 4.5, _clean(line))
            except Exception:
                pass
        pdf.set_text_color(*_DARK)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 130, 170)
    pdf.multi_cell(
        0, 5,
        f"Generado por Pactora CLM · Unergy · {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        "Este informe es orientativo y no constituye asesoramiento legal."
    )

    return bytes(pdf.output())


def generate_portfolio_report_pdf(
    portfolio_summary: str,
    contract_data: List[Dict[str, Any]],
) -> bytes:
    """Genera PDF del resumen ejecutivo del portfolio de contratos."""
    pdf = _new_pdf()

    _header(
        pdf,
        "Informe Ejecutivo de Portfolio",
        f"Pactora CLM · Unergy · {len(contract_data)} contrato(s) analizados",
    )

    # Resumen ejecutivo
    _section(pdf, "Resumen ejecutivo")
    _body(pdf, portfolio_summary)

    # Tabla de contratos
    if contract_data:
        pdf.ln(4)
        _section(pdf, "Detalle del portfolio")

        # Cabecera de tabla
        col_w = [90, 35, 28, 25]
        headers = ["Contrato", "Tipo", "Riesgo", "Score"]
        pdf.set_fill_color(*_DARK)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        for w, h in zip(col_w, headers):
            pdf.cell(w, 7, h, border=0, fill=True)
        pdf.ln()

        # Filas
        color_map_text = {"ROJO": _RED, "AMARILLO": _YELLOW, "VERDE": _GREEN}
        for i, c in enumerate(contract_data):
            bg = (248, 246, 252) if i % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*bg)
            pdf.set_text_color(*_DARK)
            pdf.set_font("Helvetica", "", 8)

            nombre = _clean(c.get("nombre", ""))[:45]
            tipo = _clean(c.get("tipo", "—"))[:18]
            risk = c.get("risk", "—").upper()
            score = str(c.get("compliance_score", "—"))
            rcolor = color_map_text.get(risk, _DARK)

            # Nombre
            pdf.set_fill_color(*bg)
            pdf.cell(col_w[0], 6, nombre, border=0, fill=True)
            pdf.cell(col_w[1], 6, tipo, border=0, fill=True)
            # Riesgo con color
            pdf.set_text_color(*rcolor)
            pdf.cell(col_w[2], 6, risk, border=0, fill=True)
            pdf.set_text_color(*_DARK)
            pdf.cell(col_w[3], 6, score, border=0, fill=True)
            pdf.ln()

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 130, 170)
    pdf.multi_cell(
        0, 5,
        f"Generado por Pactora CLM · Unergy · {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        "Este informe es orientativo y no constituye asesoramiento legal."
    )

    return bytes(pdf.output())
