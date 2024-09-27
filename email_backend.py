import imaplib
import email
from email.header import decode_header
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import os
import awsgi  # Import AWS WSGI for Lambda compatibility

app = Flask(__name__)

# Helper function to decode MIME encoded words
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

# Helper function to generate an HTML report
def generate_html_report(email_data):
    html_content = '''<html><head><title>Email Summary</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; background-color: #f9f9f9; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #4CAF50; }
        h3 { color: #FF5722; }
        .email-content { border-bottom: 2px solid #ddd; padding-bottom: 10px; margin-bottom: 10px; }
        .date { color: #999; }
    </style></head><body><h1>Email Summary</h1>'''

    for subject, from_, body, date in email_data:
        html_content += f'<div class="email-content">'
        html_content += f"<h2>From: {from_}</h2>"
        html_content += f"<h3>Subject: {subject}</h3>"
        formatted_date = date.strftime('%d.%m.%Y')
        html_content += f'<p class="date">Date: {formatted_date}</p>'
        html_content += f"<div>{body}</div><hr></div>"

    html_content += "</body></html>"
    return html_content

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
                email_data.append((subject, from_, email_body, date))

    mail.logout()
    return email_data

# Flask route for email fetching and rendering
@app.route('/fetch-emails', methods=['POST'])
def fetch_emails_endpoint():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Fetch emails
    email_data = fetch_emails(email, password)

    if not email_data:
        return jsonify({'message': 'No emails found for this week.'}), 404

    # Generate the HTML report
    html_report = generate_html_report(email_data)
    
    # Render the HTML report
    return render_template_string(html_report)

# Lambda handler using AWS WSGI adapter for Flask
def lambda_handler(event, context):
    return awsgi.response(app, event, context)
