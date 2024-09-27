from flask import Flask, render_template, request, redirect, url_for, session, flash
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import tempfile
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# IMAP server details
IMAP_SERVER = "mail.bilkent.edu.tr"
IMAP_PORT = 993

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # Authenticate with IMAP
    if authenticate_user(email, password):
        session['email'] = email
        session['password'] = password
        return redirect(url_for('fetch_emails'))
    else:
        flash("Login failed. Please check your credentials.", "error")
        return redirect(url_for('home'))

def authenticate_user(username, password):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(username, password)
        mail.logout()
        return True
    except imaplib.IMAP4.error:
        return False

@app.route('/fetch_emails')
def fetch_emails():
    username = session.get('email')
    password = session.get('password')

    if not username or not password:
        return redirect(url_for('home'))

    # Fetch emails (ensure this function is working)
    emails = fetch_emails_from_server(username, password)
    
    # Debugging: Ensure emails are being fetched properly
    print(emails)

    # Pass the emails to the template for rendering
    return render_template('email_display.html', emails=emails)

def fetch_emails_from_server(username, password):
    """Fetch and filter emails from Bilkent IMAP server."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(username, password)
    mail.select("inbox")

    # Define the search query for the week
    start_of_week, end_of_week = get_week_date_range()
    search_query = f'(OR (SUBJECT "DAIS") (SUBJECT "AIRS")) SINCE {start_of_week.strftime("%d-%b-%Y")} BEFORE {end_of_week.strftime("%d-%b-%Y")}'
    status, messages = mail.search(None, search_query)
    message_ids = messages[0].split()

    emails = []
    for num in message_ids:
        status, msg_data = mail.fetch(num, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                subject = safe_decode(subject)
                from_ = decode_mime_words(msg.get("From"))
                date = parsedate_to_datetime(msg["Date"])
                body = get_email_body(msg) or "No body available"
                
                emails.append({
                    'from': from_,
                    'subject': subject,
                    'body': body,
                    'date': date.strftime('%d.%m.%Y')
                })

    mail.logout()
    return emails

def safe_decode(value):
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.decode('ISO-8859-9')
    return value

def decode_mime_words(s):
    decoded_words = decode_header(s)
    decoded_string = ""
    for word, encoding in decoded_words:
        if isinstance(word, bytes):
            if encoding:
                decoded_string += word.decode(encoding)
            else:
                decoded_string += word.decode("utf-8")
        else:
            decoded_string += word
    return decoded_string

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8")
    return msg.get_payload(decode=True).decode("utf-8")

def get_week_date_range():
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    return start_of_week, end_of_week

if __name__ == '__main__':
    app.run(debug=True)
