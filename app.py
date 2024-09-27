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
        # Save email and password in session for further operations
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

    # Fetch emails here (you can use your existing fetch_emails function)
    emails = []  # Fetch emails based on your logic

    # Example email data:
    emails.append({'from': 'sender@example.com', 'subject': 'Test Email', 'date': '10/01/2024'})

    return render_template('email_display.html', emails=emails)

@app.route('/generate_report', methods=['POST'])
def generate_report():
    generate = request.form['generate']

    if generate == 'no':
        # Log out user and redirect to home
        session.clear()
        return redirect(url_for('home'))

    if generate == 'yes':
        # Generate report
        report_html = generate_html_report()  # Use your actual report generation logic

        # Store report in a temporary file
        report_file_path = os.path.join(REPORT_DIR, f"{session['email']}_report.html")
        with open(report_file_path, 'w') as f:
            f.write(report_html)

        # Redirect to report page
        return redirect(url_for('report', report_file=report_file_path))

@app.route('/report')
def report():
    report_file = request.args.get('report_file')

    # Read report content
    if os.path.exists(report_file):
        with open(report_file, 'r') as f:
            report_html = f.read()

        # After displaying, delete the report
        os.remove(report_file)
        return render_template('report.html', report=report_html)

    return "Report not found", 404

def generate_html_report():
    # Dummy HTML report content, replace with your logic
    return "<h1>Generated Email Report</h1><p>Emails content goes here.</p>"

if __name__ == '__main__':
    app.run(debug=True)
