from flask import Flask, render_template, jsonify
import imaplib
import email
from email.header import decode_header
import re
import threading
import time
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='/home/ggswitch/mysite/email_fetch.log', level=logging.DEBUG)

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
            status, messages = mail.search(None, 'FROM', '"yummybirdy396@gmail.com"')

            if status == "OK":
                message_list = messages[0].split(b' ')
                
                if len(message_list) == 0 or message_list[0] == b'':
                    logging.info("No new emails found")
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
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else 'utf-8')

                        subject_match = re.search(r"【(\d{6})】", subject)
                        if subject_match:
                            verification_code = subject_match.group(1)
                            logging.debug(f"Verification code found in subject: {verification_code}")
                            return

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

            time.sleep(60)

        except Exception as e:
            logging.error(f"Error: {str(e)}")
            time.sleep(60)

# Run email scanning on a background thread
def start_email_scanning(username, password):
    mail = login_to_email(username, password)
    email_thread = threading.Thread(target=fetch_verification_code, args=(mail,))
    email_thread.start()

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
    # Directly pass your email and password here
    start_email_scanning("switchsport33@gmail.com", "unkh fven drai vtyx")
    app.run(host="0.0.0.0", port=5000)
