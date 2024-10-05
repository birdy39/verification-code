from flask import Flask, render_template, jsonify
import imaplib2
import email
from email.header import decode_header
import re
import threading
import time
import logging
import os

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='email_fetch.log', level=logging.DEBUG)

# Global variable to store the latest verification code
verification_code = None

# Function to login to email account
def login_to_email(username, password):
    try:
        mail = imaplib2.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        logging.debug("Successfully logged in to email.")
        return mail
    except Exception as e:
        logging.error(f"Error logging into email: {e}")
        return None

# Function to fetch verification code from the email
def fetch_verification_code(mail):
    global verification_code
    while True:
        try:
            mail.select("inbox")
            status, messages = mail.search(None, 'FROM', '"yummybirdy396@gmail.com"')  # Replace with your email

            if status == "OK":
                message_list = messages[0].split(b' ')

                if not message_list or message_list[0] == b'':  # No emails found
                    logging.debug("No new emails found")
                    time.sleep(60)
                    continue

                latest_email_id = message_list[-1]
                status, msg_data = mail.fetch(latest_email_id, '(RFC822)')

                if status != "OK":
                    logging.error(f"Error fetching email: {status}")
                    time.sleep(60)
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Decode subject and look for verification code
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else 'utf-8')

                        subject_match = re.search(r"【(\d{6})】", subject)
                        if subject_match:
                            verification_code = subject_match.group(1)
                            logging.debug(f"Verification code found in subject: {verification_code}")
                            return

                        # Check body for the 6-digit code
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    body_match = re.search(r"\b\d{6}\b", body)
                                    if body_match:
                                        verification_code = body_match.group()
                                        logging.debug(f"Verification code found in body: {verification_code}")
                                        return
                        else:
                            body = msg.get_payload(decode=True).decode()
                            body_match = re.search(r"\b\d{6}\b", body)
                            if body_match:
                                verification_code = body_match.group()
                                logging.debug(f"Verification code found in body: {verification_code}")
                                return
            time.sleep(60)
        except Exception as e:
            logging.error(f"Error fetching verification code: {e}")
            time.sleep(60)

# Function to start email scanning in a background thread
def start_email_scanning(username, password):
    mail = login_to_email(username, password)
    if mail:
        email_thread = threading.Thread(target=fetch_verification_code, args=(mail,))
        email_thread.start()

# Route to display the verification code
@app.route('/get_code', methods=['GET'])
def get_code():
    global verification_code
    if verification_code:
        return jsonify({"verification_code": verification_code})
    else:
        return jsonify({"message": "No verification code found"}), 404

# Homepage
@app.route('/')
def index():
    return render_template('index.html')

# Run the app
if __name__ == "__main__":
    # Start email scanning in the background
    start_email_scanning("switchsport33@gmail.com", "unkh fven drai vtyx")
    # Set up port based on Render's environment
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
