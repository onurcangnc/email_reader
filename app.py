from flask import Flask, render_template, request, redirect, url_for
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta

app = Flask(__name__)

# Helper function to decode MIME encoded words
def decode_mime_words(s):
    decoded_words = decode_header(s)
    decoded_string = ""
    for word, encoding in decoded_words:
        if isinstance(word, bytes):
            decoded_string += word.decode(encoding) if encoding else word.decode('utf-8')
        else:
            decoded_string += word
    return decoded_string

# Function to get email body from message
def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition:
                try:
                    if content_type == "text/plain":
                        return part.get_payload(decode=True).decode("utf-8")
                    elif content_type == "text/html":
                        return part.get_payload(decode=True).decode("utf-8")
                except UnicodeDecodeError:
                    return part.get_payload(decode=True).decode("ISO-8859-9")
    else:
        return msg.get_payload(decode=True).decode("utf-8")
    return None

# Helper function to get the current week's date range
def get_week_date_range():
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    return start_of_week, end_of_week

# Main function to fetch emails
def fetch_emails(username, password):
    mail = imaplib.IMAP4_SSL("mail.bilkent.edu.tr")
    mail.login(username, password)
    mail.select("inbox")

    start_of_week, end_of_week = get_week_date_range()
    start_of_week_str = start_of_week.strftime('%d-%b-%Y')
    end_of_week_str = end_of_week.strftime('%d-%b-%Y')

    search_query = f'(OR (SUBJECT "DAIS") (SUBJECT "AIRS")) SINCE {start_of_week_str} BEFORE {end_of_week_str}'
    status, messages = mail.search(None, search_query)

    message_ids = messages[0].split()
    if not message_ids:
        return None

    email_data = []
    for num in message_ids:
        status, msg_data = mail.fetch(num, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                subject = subject.decode() if isinstance(subject, bytes) else subject
                from_ = decode_mime_words(msg.get("From"))
                date = parsedate_to_datetime(msg["Date"])
                email_body = get_email_body(msg) or "No body available"
                email_data.append({
                    "subject": subject,
                    "from": from_,
                    "date": date.strftime('%d.%m.%Y'),
                    "body": email_body
                })

    mail.logout()
    return email_data

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/fetch', methods=['POST'])
def fetch():
    username = request.form['email']
    password = request.form['password']

    # Fetch emails
    email_data = fetch_emails(username, password)
    if not email_data:
        return render_template('process.html', error="No emails found.")

    return render_template('process.html', email_data=email_data)

@app.route('/generate_report')
def generate_report():
    return render_template('output.html')

if __name__ == '__main__':
    app.run(debug=True)
