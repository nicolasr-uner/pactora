def generate_investor_report(contract_type: str, metrics: dict, policies: list, risk_data: dict) -> str:
    """
    Generates a Markdown executive report (Investor-Ready) representing the Document Snapshot.
    """
    
    # Safely get values with fallbacks
    nivel_riesgo = risk_data.get("Nivel", "Desconocido")
    justificacion = risk_data.get("Justificacion", "No disponible.")
    alertas = risk_data.get("Alertas", [])
    
    precio = metrics.get("Precio", "No especificado")
    vigencia = metrics.get("Vigencia", "No especificada")
    hitos = metrics.get("Hitos", "No especificados")
    obligaciones = metrics.get("Obligaciones", "No especificadas")
    
    alertas_md = "\n".join([f"- {a}" for a in alertas]) if alertas else "Ninguna detectada."
    
    polizas_md = ""
    if policies:
        for p in policies:
            tipo = p.get('Tipo', 'N/A')
            venc = p.get('Vencimiento', 'N/A')
            valor = p.get('Valor', 'N/A')
            polizas_md += f"- **{tipo}**: {valor} (Vence: {venc})\n"
    else:
        polizas_md = "No se detectaron pólizas exigidas."

    report = f"""# Resumen Ejecutivo (Investor Ready) - Unergy
> **Generado por Pactora DocBrain**

## 1. Información General del Contrato
- **Tipo de Contrato:** {contract_type}
- **Precio/Tarifa (IPP/IPC):** {precio}
- **Vigencia Comercial:** {vigencia}
- **Hitos Clave (Ej. NTP, COD):** {hitos}

## 2. Obligaciones y Deberes
{obligaciones}

## 3. Pólizas y Garantías Activas
{polizas_md}

## 4. Análisis Regulatorio y Semáforo de Riesgo (CREG/BMA)
### Nivel de Riesgo: **{nivel_riesgo}**
**Justificación Legal:**
{justificacion}

**Alertas Identificadas:**
{alertas_md}

---
*Este reporte ha sido generado automáticamente por Inteligencia Artificial y validado por el equipo legal de la Trifuerza Energética (Unergy, Suno, Solenium).*
"""
    return report
