def generate_investor_report(contract_type: str, metrics: dict, policies: list, risk_data: dict) -> str:
    """
    Generates a Markdown executive report (Investor-Ready) representing the Document Snapshot.
    Incorporating Unergy Brand Colors.
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

    report = f"""<div style="font-family: 'Lato', sans-serif; color: #2C2039; background-color: #FDFAF7; padding: 20px; border-radius: 8px;">
<h1 style="color: #915BD8; font-family: 'Lato', sans-serif; font-weight: 900;">Resumen Ejecutivo (Investor Ready) - Unergy</h1>
<p><em>Generado por Pactora DocBrain</em></p>

<h2 style="color: #2C2039; font-weight: 900;">1. Información General del Contrato</h2>
<ul>
<li><strong>Tipo de Contrato:</strong> {contract_type}</li>
<li><strong>Precio/Tarifa (IPP/IPC):</strong> {precio}</li>
<li><strong>Vigencia Comercial:</strong> {vigencia}</li>
<li><strong>Hitos Clave (Ej. NTP, COD):</strong> {hitos}</li>
</ul>

<h2 style="color: #2C2039; font-weight: 900;">2. Obligaciones y Deberes</h2>
<p>{obligaciones}</p>

<h2 style="color: #2C2039; font-weight: 900;">3. Pólizas y Garantías Activas</h2>
{polizas_md}

<h2 style="color: #2C2039; font-weight: 900;">4. Análisis Regulatorio y Semáforo de Riesgo (CREG/BMA)</h2>
<div style="background-color: rgba(145, 91, 216, 0.1); padding: 15px; border-left: 4px solid #915BD8;">
<h3>Nivel de Riesgo: <strong>{nivel_riesgo}</strong></h3>
<p><strong>Justificación Legal:</strong><br/>{justificacion}</p>
</div>

<div style="background-color: rgba(246, 255, 114, 0.2); padding: 15px; border-left: 4px solid #F6FF72; margin-top: 10px;">
<p><strong>⚠️ Alertas Identificadas:</strong><br/>{alertas_md}</p>
</div>

<hr style="border: 0; border-top: 1px solid rgba(44, 32, 57, 0.2); margin-top: 20px;">
<p style="font-size: 12px; color: #2C2039;"><em>Este reporte ha sido generado automáticamente por Inteligencia Artificial y validado por el equipo legal de la Trifuerza Energética (Unergy, Suno, Solenium).</em></p>
</div>
"""
    return report
