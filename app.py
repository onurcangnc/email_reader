from flask import Flask, render_template, request, redirect, url_for, session, flash
import imaplib

app = Flask(__name__)
app.secret_key = "your-secret-key"

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

    # Authenticate against Bilkent IMAP server
    if authenticate_user(email, password):
        session['email'] = email
        session['password'] = password
        return redirect(url_for('fetch_emails'))
    else:
        flash("Login failed. Please check your credentials and try again.", "error")
        return redirect(url_for('home'))

def authenticate_user(email, password):
    """Authenticate user against Bilkent IMAP server."""
    try:
        # Connect to Bilkent IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        # Try to log in with the provided credentials
        mail.login(email, password)
        mail.logout()
        return True  # If login succeeds, return True
    except imaplib.IMAP4.error:
        return False  # If login fails, return False

@app.route('/fetch_emails')
def fetch_emails():
    email = session.get('email')
    password = session.get('password')

    if not email or not password:
        return redirect(url_for('home'))

    # Here you can fetch emails and pass them to the template
    emails = []  # Replace with actual fetching logic

    # Example email data:
    emails.append({'from': 'sender@example.com', 'subject': 'Test Email', 'date': '10/01/2024'})

    return render_template('email_display.html', emails=emails)

if __name__ == '__main__':
    app.run(debug=True)
