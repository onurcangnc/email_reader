import sys
import os
import imaplib
import email
from email.header import decode_header
import webbrowser
import tempfile
import time
from rich.console import Console
from email.utils import parsedate_to_datetime
from getpass import getpass
import pyfiglet  # Import pyfiglet for dynamic ASCII art generation
import random  # Import random to select a random font
from datetime import datetime, timedelta, timezone

# Set the environment variable for the terminal to use UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Rich Console for colored output
console = Console()

# Define the file to store fetched UIDs
uid_file = "fetched_uids.txt"

def load_fetched_uids():
    """Load the list of UIDs that have already been fetched."""
    if os.path.exists(uid_file):
        with open(uid_file, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_fetched_uid(uid):
    """Save a UID to the file, marking it as fetched."""
    with open(uid_file, "a") as f:
        f.write(uid + "\n")

def get_email_body(msg):
    """Extract and return the body content of the email as text or HTML."""
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
                    try:
                        return part.get_payload(decode=True).decode("ISO-8859-9")
                    except UnicodeDecodeError:
                        return part.get_payload(decode=True).decode("Windows-1254")
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8")
        except UnicodeDecodeError:
            try:
                return msg.get_payload(decode=True).decode("ISO-8859-9")
            except UnicodeDecodeError:
                return msg.get_payload(decode=True).decode("Windows-1254")
    return None

def decode_mime_words(s):
    """Decode MIME encoded words to normal string."""
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

def safe_decode(value):
    """Attempt to decode bytes using multiple encodings."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("ISO-8859-9")  # Fallback for Turkish characters
    return value

def generate_html_file(email_data):
    """Generate a single HTML file with all email subjects, from details, and content."""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "emails.html")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('''<html><head><title>Email Summary</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; background-color: #f9f9f9; padding: 20px; }
            h1 { color: #333; }
            h2 { color: #4CAF50; }
            h3 { color: #FF5722; }
            .email-content { border-bottom: 2px solid #ddd; padding-bottom: 10px; margin-bottom: 10px; }
            .date { color: #999; }
        </style></head><body>''')
        f.write("<h1>Email Summary</h1>")
        
        for subject, from_, body, date in email_data:
            f.write(f'<div class="email-content">')
            f.write(f"<h2>From: {from_}</h2>")
            f.write(f"<h3>Subject: {subject}</h3>")
            formatted_date = date.strftime('%d.%m.%Y')
            f.write(f'<p class="date">Date: {formatted_date}</p>')
            f.write(f"<div>{body}</div><hr></div>")
        
        f.write("</body></html>")
    
    return file_path, temp_dir

def open_email_in_browser(file_path):
    """Open the temporary email file in the user's default web browser."""
    webbrowser.open(f"file://{file_path}")

def delete_temp_directory(temp_dir):
    """Delete the temporary directory and its contents."""
    try:
        if os.path.exists(temp_dir):
            os.remove(temp_dir + "/emails.html")
            os.rmdir(temp_dir)
    except Exception as e:
        print(f"Error deleting temporary files: {e}")

def get_week_date_range():
    """Get the date range for the current week (Monday to Sunday)."""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday  <-- Fix: Use 'days=6'
    return start_of_week, end_of_week

def get_current_month_date_range():
    """Get the date range for the current month."""
    today = datetime.now()
    start_of_month = today.replace(day=1)
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(days=1)
    return start_of_month, end_of_month

def normalize_datetime(dt):
    """Normalize datetime to handle offset-naive and offset-aware datetimes."""
    if dt.tzinfo is None:  # If the datetime is naive (no timezone info)
        return dt.replace(tzinfo=timezone.utc)  # Treat as UTC for consistency
    return dt

def fetch_emails(username, password):
    """Fetch emails from the Bilkent IMAP server and filter by the current week, then month if no results."""
    # Connect to the IMAP server
    mail = imaplib.IMAP4_SSL("mail.bilkent.edu.tr")
    
    # Log in with credentials
    mail.login(username, password)
    
    # Select the inbox
    mail.select("inbox")

    # Get the start and end dates of the current week
    start_of_week, end_of_week = get_week_date_range()
    start_of_week_str = start_of_week.strftime('%d-%b-%Y')
    end_of_week_str = end_of_week.strftime('%d-%b-%Y')

    # Search for emails from this week (Monday to Sunday) that have "DAIS" or "AIRS" in the subject
    search_query = f'(OR (SUBJECT "DAIS") (SUBJECT "AIRS")) SINCE {start_of_week_str} BEFORE {end_of_week_str}'
    status, messages = mail.search(None, search_query)
    
    message_ids = messages[0].split()

    if not message_ids:
        # If no emails are found, check for the whole month
        console.print("[bold red]No emails found this week. Checking for the whole month...[/bold red]")
        start_of_month, end_of_month = get_current_month_date_range()
        start_of_month_str = start_of_month.strftime('%d-%b-%Y')
        end_of_month_str = end_of_month.strftime('%d-%b-%Y')

        # Update search query for the current month
        search_query = f'(OR (SUBJECT "DAIS") (SUBJECT "AIRS")) SINCE {start_of_month_str} BEFORE {end_of_month_str}'
        status, messages = mail.search(None, search_query)
        message_ids = messages[0].split()

        if not message_ids:
            # If still no emails found, display a final message and exit
            console.print("[bold red]No matching emails found for this week or month.[/bold red]")
            return

    # Get the list of UIDs of already fetched emails
    fetched_uids = load_fetched_uids()

    email_data = []
    read_emails = []
    unread_emails = []

    for num in message_ids:
        status, msg_data = mail.fetch(num, "(UID RFC822 FLAGS INTERNALDATE)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                uid = msg_data[-1].decode().split()[-1]  # Get the UID
                
                if b'\\Seen' in response_part[0]:
                    flags = '\\Seen'
                else:
                    flags = ''
                
                subject = decode_header(msg["Subject"])[0][0]
                subject = safe_decode(subject)
                
                from_ = msg.get("From")
                from_ = decode_mime_words(from_)
                date = parsedate_to_datetime(msg["Date"])
                date = normalize_datetime(date)  # Normalize the datetime to be offset-aware
                email_body = get_email_body(msg) or "No body available"
                
                if '\\Seen' in flags:
                    read_emails.append((subject, from_, email_body, date))
                else:
                    unread_emails.append((subject, from_, email_body, date))

                if uid not in fetched_uids:
                    save_fetched_uid(uid)

        mail.store(num, '+FLAGS', '\\Seen')

    # Sort both read and unread emails by newest to oldest
    unread_emails.sort(key=lambda x: x[3], reverse=True)
    read_emails.sort(key=lambda x: x[3], reverse=True)

    total_emails = len(read_emails) + len(unread_emails)
    console.print(f"[bold]Total Emails Filtered: {total_emails}[/bold]")

    # Display unread emails first
    for subject, from_, _, date in unread_emails:
        formatted_date = date.strftime('%d.%m.%Y')
        console.print(f"[bold green]New Email![/bold green] ** {from_} | Subject: {subject} | {formatted_date}")
        console.print("-----")

    # Display read emails afterward
    for subject, from_, _, date in read_emails:
        formatted_date = date.strftime('%d.%m.%Y')
        console.print(f"[bold red]Old Email![/bold red] ** {from_} | Subject: {subject} | {formatted_date}")
        console.print("-----")

    choice = input("Do you want to generate an HTML file to view the emails? (y/n): ").strip().lower()
    
    if choice == 'y':
        all_emails = read_emails + unread_emails
        file_path, temp_dir = generate_html_file(all_emails)
        console.print(f"To view the emails, [link=file://{file_path}]Click here[/link]", style="blue")
        open_email_in_browser(file_path)
        time.sleep(10)
        delete_temp_directory(temp_dir)
    else:
        console.print("[bold]HTML file not generated.[/bold]")

    mail.logout()

# CLI interaction for login
if __name__ == "__main__":
    available_fonts = pyfiglet.FigletFont.getFonts()
    random_font = random.choice(available_fonts)
    ascii_header = pyfiglet.figlet_format("Bilkent Email Reader", font=random_font)
    console.print(ascii_header, style="bold red")

    username = input("Enter your Bilkent email: ")
    password = getpass("Enter your email password: ")
    console.print("[bold]Fetching all emails...[/bold]")
    fetch_emails(username, password)
    console.print("[bold]All emails fetched.[/bold]")
