import datetime
from utils.auth_helper import get_calendar_service

def create_calendar_event(summary: str, description: str, date_str: str) -> bool:
    """
    Creates an all-day event in Google Calendar on the specified date.
    Returns True if successful, False otherwise.
    """
    service = get_calendar_service()
    if not service:
        return False
        
    try:
        # Expected format YYYY-MM-DD
        # Let's cleanly parse just in case
        parsed_date = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        
        event = {
            'summary': f"Pactora Alerta: {summary}",
            'description': description,
            'start': {
                'date': parsed_date.isoformat(),
                'timeZone': 'America/Bogota',
            },
            'end': {
                'date': parsed_date.isoformat(),
                'timeZone': 'America/Bogota',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 24 * 60},
                    {'method': 'email', 'minutes': 30 * 24 * 60}, # 30 days before
                ],
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return True
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return False
