# utils/calendar_manager.py
from googleapiclient.errors import HttpError
from utils.auth_helper import get_calendar_service
from datetime import datetime, timedelta

def create_calendar_event(summary: str, description: str, date_str: str, days_before: int = 30):
    """
    Crea un evento en el calendario (ej. vencimiento de póliza o hito COD)
    con una alerta N días antes.
    date_str: Formato 'YYYY-MM-DD'
    """
    try:
        service = get_calendar_service()
        # Parsear la fecha objetivo
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # El evento inicia y termina el mismo día (All-day event)
        start_date = target_date.strftime("%Y-%m-%d")
        end_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")

        event = {
            'summary': f"[PACTORA] Hito: {summary}",
            'description': description,
            'start': {
                'date': start_date,
                'timeZone': 'America/Bogota',
            },
            'end': {
                'date': end_date,
                'timeZone': 'America/Bogota',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': days_before * 24 * 60},
                    {'method': 'popup', 'minutes': days_before * 24 * 60},
                ],
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return created_event.get('htmlLink')

    except HttpError as error:
        print(f"Ocurrió un error al crear el evento en Calendar: {error}")
        return None
    except ValueError as val_err:
        print(f"Error parseando fecha. Formato esperado YYYY-MM-DD: {val_err}")
        return None
