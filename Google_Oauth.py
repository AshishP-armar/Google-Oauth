from flask import Flask, redirect, url_for, session, request
import os
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import WebApplicationClient
from dotenv import load_dotenv

load_dotenv()
# Set up Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Securely generate a secret key
# Google OAuth2 configuration
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")  # Replace with your Google Client ID
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SCREAT_KEY")  # Replace with your Google Client Secret

AUTHORIZATION_BASE_URL = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
USER_INFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'

# OAuth2 client
client = WebApplicationClient(CLIENT_ID)

# Route to start OAuth flow
@app.route('/')
def index():
    if 'oauth_token' in session:
        oauth_token = session['oauth_token']
        google = OAuth2Session(CLIENT_ID, token=oauth_token)
        user_info = google.get(USER_INFO_URL).json()
        print(oauth_token)
        return f'<h1>Hello, {user_info["name"]} <br>{user_info["email"]}!</h1> <a href="/calendar">calendar</a><br> <a href="/logout">Logout</a> <br> <a href="/add_event" > Add Event </a>'
    return redirect(url_for('login'))

# Route to redirect the user to Google's OAuth2 authorization page
@app.route('/login')
def login():
    print(url_for("callback"))
    google = OAuth2Session(CLIENT_ID, redirect_uri=url_for('callback', _external=True), scope=["email", "profile", "https://www.googleapis.com/auth/calendar.readonly", 'https://www.googleapis.com/auth/calendar'])  # Include scope here
    authorization_url, state = google.authorization_url(AUTHORIZATION_BASE_URL)
    # Save the state in the session for later verification
    session['oauth_state'] = state
    return redirect(authorization_url)

# Callback route after Google redirects
@app.route('/callback')
def callback():
    google = OAuth2Session(CLIENT_ID, state=session['oauth_state'], redirect_uri=url_for('callback', _external=True))
    token = google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
    
    # Save the token in the session
    session['oauth_token'] = token
    
    return redirect(url_for('index'))
@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("login"))

@app.route('/calendar')
def calendar():
    # print(session['oauth_token'])
    if 'oauth_token' not in session:
        return redirect(url_for('login'))

    google = OAuth2Session(CLIENT_ID, token=session['oauth_token'])
    calendar_url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
    response = google.get(calendar_url)
    # print(response.json())
    if response.status_code == 200:
        events = response.json().get('items', [])
        if not events:
            return "No upcoming events found."

        event_list = '<h1>Upcoming Events</h1>'
        for event in events:
            event_list += f"<p>{event['summary']} - {event['start']['dateTime']}</p>"
        return event_list
    else:
        return "Failed to fetch calendar events."

@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    # Check if the user is logged in
    if 'oauth_token' not in session:
        return redirect(url_for('login'))

    # OAuth session
    google = OAuth2Session(CLIENT_ID, token=session['oauth_token'])

    # Event details with Indian time zone
    event = {
        'summary': 'Meeting with Team',
        'location': 'Mumbai, India',
        'description': 'Discuss quarterly project updates.',
        'start': {
            'dateTime': '2025-01-15T17:30:00+05:30',  # Start time in IST (15:00 = 3:00 PM)
            'timeZone': 'Asia/Kolkata',               # Time zone for India
        },
        'end': {
            'dateTime': '2025-01-15T18:00:00+05:30',  # End time in IST (16:00 = 4:00 PM)
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': [
            {'email': 'attendee1@example.com'},
            {'email': 'attendee2@example.com'},
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # Reminder 1 day before
                {'method': 'popup', 'minutes': 10},      # Reminder 10 minutes before
            ],
        },
    }

    # Send the event creation request
    calendar_url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
    response = google.post(calendar_url, json=event)

    if response.status_code == 200:
        event_info = response.json()
        return f"Event created: {event_info['htmlLink']}"
    else:
        return f"Failed to create event: {response.status_code} {response.text}"


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
