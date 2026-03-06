from datetime import datetime, timedelta
from utils.auth_helper import get_calendar_service

def create_contract_event(summary, description, start_date_str, location="Pactora CLM / Google Drive"):
    """
    Crea un evento en Google Calendar para hitos del contrato (NTP, COD, Pólizas).
    start_date_str debe estar en formato YYYY-MM-DD.
    """
    try:
        service = get_calendar_service()
        
        # El calendario de Google usa formato RFC3339
        start_time = f"{start_date_str}T09:00:00Z"
        end_time = f"{start_date_str}T10:00:00Z"
        
        event = {
            'summary': f"📄 Pactora: {summary}",
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 60},
                    {'method': 'popup', 'minutes': 30 * 24 * 60}, # 30 días antes para pólizas
                ],
            },
        }
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        return {"id": event.get('id'), "link": event.get('htmlLink')}
        
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return {"error": str(e)}

def sync_policies_to_calendar(policies):
    """
    Itera sobre una lista de pólizas (dict con Tipo y Vencimiento) y las sincroniza.
    """
    results = []
    for policy in policies:
        if policy.get('Vencimiento') and policy.get('Vencimiento') != 'N/A':
            # Intentar normalizar fecha si viene mal
            v_date = policy['Vencimiento']
            summary = f"Renovación Póliza: {policy.get('Tipo', 'Seguros')}"
            desc = f"Recordatorio de renovación generado por Pactora para la póliza de {policy.get('Tipo')} con valor {policy.get('Valor', 'N/A')}."
            
            res = create_contract_event(summary, desc, v_date)
            results.append(res)
    return results
