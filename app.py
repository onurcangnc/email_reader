from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_socketio import SocketIO, emit
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
import tempfile
import os
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'
socketio = SocketIO(app, async_mode='eventlet')

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
        return redirect(url_for('dashboard'))
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

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('home'))
    return render_template('dashboard.html')

# WebSocket event for starting email fetching and streaming
@socketio.on('start_fetching_emails')
def handle_email_fetching():
    email = session.get('email')
    password = session.get('password')

    if email and password:
        # Fetch emails and emit updates
        fetch_emails(email, password, emit_updates=True)
        emit('fetch_complete')  # Notify the client that fetching is complete

def fetch_emails(username, password, emit_updates=False):
    """Fetch emails from the Bilkent IMAP server."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(username, password)
    mail.select("inbox")

    start_of_week, end_of_week = get_week_date_range()
    search_query = f'(OR (SUBJECT "DAIS") (SUBJECT "AIRS")) SINCE {start_of_week.strftime("%d-%b-%Y")} BEFORE {end_of_week.strftime("%d-%b-%Y")}'
    status, messages = mail.search(None, search_query)
    message_ids = messages[0].split()

    email_data = []

    if not message_ids:
        if emit_updates:
            emit('email_update', {'data': 'No emails found this week.'})
        mail.logout()
        return email_data

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
                
                email_entry = {
                    'from': from_,
                    'subject': subject,
                    'body': body,
                    'date': date.strftime('%d.%m.%Y')
                }
                
                email_data.append(email_entry)

                if emit_updates:
                    emit('email_update', email_entry)  # Emit updates in real-time
                time.sleep(1)

    mail.logout()
    
    if not emit_updates:
        report_file_path, temp_dir = generate_html_file(email_data)
        return report_file_path  # Return path to the report file

    return email_data  # Return email data for real-time streaming

def generate_html_file(email_data):
    """Generate a report file for emails."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "emails_report.html")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<html><body><h1>Email Report</h1><hr>")
        for email_entry in email_data:
            f.write(f"<h3>From: {email_entry['from']}</h3>")
            f.write(f"<h3>Subject: {email_entry['subject']}</h3>")
            f.write(f"<p>Date: {email_entry['date']}</p>")
            f.write(f"<p>{email_entry['body']}</p>")
            f.write("<hr>")
        f.write("</body></html>")

    return file_path, temp_dir

@app.route('/download_report')
def download_report():
    # Fetch latest report without emitting updates
    report_file_path = fetch_emails(session['email'], session['password'], emit_updates=False)
    if report_file_path:
        return send_file(report_file_path, as_attachment=True)
    else:
        flash("No report found.", "error")
        return redirect(url_for('dashboard'))

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
    socketio.run(app, debug=True)
