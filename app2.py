from flask import Flask, render_template, jsonify
import imaplib
import email
from email.header import decode_header
import re
import threading
import time
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='email_fetch.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variable to store the latest verification code
verification_code = None

# Function to login to email account
def login_to_email(username, password):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        logging.debug("Successfully logged in to email.")
        return mail
    except Exception as e:
        logging.error(f"Error logging into email: {e}")
        return None

def fetch_verification_code(mail):
    global verification_code
    while True:
        try:
            mail.select("inbox")
            status, messages = mail.search(None, 'FROM', '"yummybirdy396@gmail.com"')  # Change this email if needed

            # Check if we got any messages
            if status == "OK":
                message_list = messages[0].split(b' ')
                
                if len(message_list) == 0 or message_list[0] == b'':  # If no messages found
                    logging.debug("No new emails found.")
                    time.sleep(60)  # Wait 60 seconds before checking again
                    continue

                latest_email_id = message_list[-1]  # Get the latest email ID
                
                # Fetch the latest email
                status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
                if status != "OK":
                    logging.debug(f"Error fetching email: {status}")
                    time.sleep(60)
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject and look for verification code
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else 'utf-8')

                        # Check subject for the 6-digit code
                        subject_match = re.search(r"【(\d{6})】", subject)
                        if subject_match:
                            verification_code = subject_match.group(1)
                            logging.debug(f"Verification code found in subject: {verification_code}")
                            return

                        # Check body for the 6-digit code
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if "plain" in content_type:
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

            time.sleep(60)  # Wait before checking for the next email

        except Exception as e:
            logging.error(f"Error: {str(e)}")
            time.sleep(60)  # Wait and retry after 60 seconds in case of an error

# Run email scanning on a background thread
def start_email_scanning(username, password):
    mail = login_to_email(username, password)
    if mail:
        email_thread = threading.Thread(target=fetch_verification_code, args=(mail,))
        email_thread.start()
    else:
        logging.error("Failed to start email scanning due to login error.")

# Route for the buyer to view the verification code
@app.route('/get_code', methods=['GET'])
def get_code():
    global verification_code
    if verification_code:
        return jsonify({"verification_code": verification_code})
    else:
        return jsonify({"message": "No verification code found"}), 404

# Homepage to display the verification code
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    # Get email credentials from environment variables
    email_username = os.environ.get('EMAIL_USERNAME')
    email_password = os.environ.get('EMAIL_PASSWORD')

    if not email_username or not email_password:
        logging.error("Missing email credentials in environment variables.")
    else:
        # Start the email scanning thread
        start_email_scanning(email_username, email_password)

    # For deployment on Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
