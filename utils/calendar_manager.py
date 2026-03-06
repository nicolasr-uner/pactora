# utils/calendar_manager.py
import datetime
import streamlit as st

def create_calendar_event(calendar_service, summary, description, date_str, days_before=30):
    """
    Crea un evento en Google Calendar `days_before` días antes de la fecha límite (date_str).
    """
    try:
        # Intento de parsear la fecha asumiendo YYYY-MM-DD para simplificar.
        # En un escenario real, se usaría un parser robusto de fecha extraída por IA.
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        event_date = target_date - datetime.timedelta(days=days_before)
        
        event = {
          'summary': f"🔴 Vencimiento Pactora: {summary}",
          'description': description,
          'start': {
            'date': event_date.strftime("%Y-%m-%d"),
            'timeZone': 'America/Bogota',
          },
          'end': {
            'date': event_date.strftime("%Y-%m-%d"),
            'timeZone': 'America/Bogota',
          },
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'email', 'minutes': 24 * 60},
              {'method': 'popup', 'minutes': 10},
            ],
          },
        }

        event_result = calendar_service.events().insert(calendarId='primary', body=event).execute()
        return event_result.get('htmlLink')
    except Exception as e:
        return f"Error al crear evento: {e}"
