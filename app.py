from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
import tempfile
import os
import time
import subprocess
import shlex


app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key'
socketio = SocketIO(app, async_mode='eventlet')

IMAP_SERVER = "mail.bilkent.edu.tr"
IMAP_PORT = 993

# Global variable to store the report file path and running CLI process
report_file_path = None
running_process = None  # Store the running process globally

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate the user
        if authenticate_user(email, password):
            session['email'] = email
            session['password'] = password
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Please check your credentials.", "error")
            return redirect(url_for('home'))
    else:
        return render_template('login.html')

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

@app.route('/download_report')
def download_report():
    # Fetch emails without emitting real-time updates
    email_data = fetch_emails(session['email'], session['password'], emit_updates=False)

    # Generate the report and get the file path
    report_file_path, temp_dir = generate_html_file(email_data)
    
    # Ensure the report file exists and trigger the download
    if report_file_path and os.path.exists(report_file_path):
        return send_file(report_file_path, as_attachment=True, download_name="emails_report.html")
    else:
        flash("No report found.", "error")
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    # Clear session and redirect to home (login) page
    session.clear()
    return redirect(url_for('home'))

# WebSocket event for starting email fetching and streaming
@socketio.on('start_fetching_emails')
def handle_email_fetching():
    email = session.get('email')
    password = session.get('password')

    if email and password:
        # Fetch emails and generate report
        global report_file_path
        report_file_path = fetch_emails(email, password, emit_updates=True)
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

    for num in message_ids:
        # Fetch the message with FLAGS
        status, msg_data = mail.fetch(num, "(FLAGS RFC822)")

        # Initialize variables for message content
        msg = None
        flags = None
        
        # Loop through the parts of the fetched message
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                if b"FLAGS" in response_part[0]:  # Extract flags from the message data
                    flags = response_part[0]
                if response_part[1]:  # Extract the email content
                    msg = email.message_from_bytes(response_part[1])
        
        if msg is None or flags is None:
            continue  # Skip if there's an issue fetching the message or flags

        # Process the email
        subject = decode_header(msg["Subject"])[0][0]
        subject = safe_decode(subject)
        from_ = decode_mime_words(msg.get("From"))
        date = parsedate_to_datetime(msg["Date"])
        date_str = date.strftime('%d.%m.%Y')
        time_str = date.strftime('%H:%M')

        # Determine if the email is read or unread based on the flags
        if b'\\Seen' in flags:
            status = 'Read'
        else:
            status = 'Unread'

        body = get_email_body(msg) or "No body available"
        
        email_entry = {
            'from': from_,
            'subject': subject,
            'body': body,
            'date': date_str,
            'time': time_str,
            'status': status
        }

        email_data.append(email_entry)

        if emit_updates:
            emit('email_update', email_entry)  # Emit updates in real-time
        time.sleep(1)  # Simulate a delay for real-time effect

    mail.logout()

    return email_data  # Return email data for real-time streaming

@app.route('/cli')
def cli_interface():
    # Directly serve the CLI interface without session or credential checks
    return render_template('cli.html')

# WebSocket event for handling CLI commands for email_reader.py
@socketio.on('start_cli')
def start_cli():
    try:
        process = subprocess.Popen(
            ['python', 'email_reader.py'], 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # Read process output line by line and emit via WebSocket
        for line in iter(process.stdout.readline, ''):
            socketio.emit('cli_output', {'output': line.strip()})
        process.stdout.close()
        process.wait()
    except Exception as e:
        socketio.emit('cli_output', {'output': str(e)})

# WebSocket event for sending input to the subprocess
@socketio.on('cli_input')
def cli_input(data):
    user_input = data.get('input') + '\n'  # Append newline to simulate terminal input
    if running_process:
        running_process.stdin.write(user_input)
        running_process.stdin.flush()

def generate_html_file(email_data):
    """Generate a report file for emails with enhanced design."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "emails_report.html")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write('''<html><head><title>Email Summary</title>
        <style>
            body { 
                font-family: 'Poppins', Arial, sans-serif; 
                line-height: 1.8; 
                background-color: #f4f4f4; 
                padding: 30px; 
                color: #333;
            }
            h1 { 
                color: #333; 
                text-align: center; 
                margin-bottom: 30px;
            }
            .email-container {
                max-width: 800px;
                margin: 20px auto;
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                border-left: 6px solid #4CAF50;
            }
            .email-content {
                border-bottom: 1px solid #ddd;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }
            .email-content:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }
            h2 {
                font-size: 1.4rem;
                color: #4CAF50;
                margin-bottom: 10px;
            }
            h3 {
                font-size: 1.2rem;
                color: #FF5722;
                margin-bottom: 10px;
            }
            p {
                font-size: 1rem;
                color: #555;
            }
            .date, .time, .status {
                color: #888;
                font-style: italic;
            }
            .status {
                color: #4CAF50;
                font-weight: bold;
            }
            a {
                color: #4CAF50;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style></head><body>''')

        f.write("<h1>Email Summary</h1>")
        
        for email in email_data:
            subject = email['subject']
            from_ = email['from']
            body = email['body']
            date = email['date']
            time = email.get('time', '')  # Ensure there's a time field
            status = email.get('status', 'Unread')  # Example of adding status (read/unread)

            f.write(f'<div class="email-container">')
            f.write(f'<div class="email-content">')
            f.write(f"<h2>From: {from_}</h2>")
            f.write(f"<h3>Subject: {subject}</h3>")
            f.write(f'<p class="date">Date: {date} <span class="time">(Time: {time})</span></p>')
            f.write(f'<p class="status">Status: {status}</p>')
            f.write(f"<p>{body}</p>")
            f.write("</div></div>")
        
        f.write("</body></html>")

    return file_path, temp_dir  # Return the path to the generated report

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
