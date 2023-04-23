import email
import mimetypes
import os
import smtplib as smtp
from email import encoders
from email.message import EmailMessage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import SMTPHandler

import dotenv

dotenv.load_dotenv()


def send_email(email, subject, text, attachments=None):
    login = os.getenv('YAN_LOGIN')
    password = os.getenv('YAN_PASSWORD')
    server = 'smtp.yandex.com'
    port = 465

    msg = MIMEMultipart()
    msg['From'] = login
    msg['To'] = email
    msg['Subject'] = subject

    body = text
    msg.attach(MIMEText(body, 'plain'))

    process_attachments(msg, attachments)

    if login.endswith('gmail.com'):
        server = smtp.SMTP(server, port)
        server.starttls()
    elif login.endswith('yandex.com'):
        server = smtp.SMTP_SSL(server, port)
    else:
        print(login)
    server.login(login, password)

    server.send_message(msg)
    server.quit()


def process_attachments(msg, attachments):
    for f in attachments:
        if os.path.isfile(f):
            attach_file(msg, f)
        elif os.path.exists(f):
            process_attachments(msg, list(map(lambda x: os.path.join(f, x), os.listdir(f))))


def attach_file(msg, f):
    attach_types = {
        'text': MIMEText,
        'image': MIMEImage, 
        'audio': MIMEAudio
    }

    filename = os.path.basename(f)
    ctype, encoding = mimetypes.guess_type(f)
    if ctype is None or encoding is not None:
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    with open(f, mode='r' if maintype == 'text' else 'rb') as fp:
        if maintype in attach_types:
            file = attach_types[maintype](fp.read(), _subtype=subtype)
        else:
            file = MIMEBase(maintype, subtype)
            file.set_payload(fp.read())
            encoders.encode_base64(file)
    file.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(file)


class SSLSMTPHandler(SMTPHandler):
    def emit(self, record):
        try:
            port = self.mailport
            if not port:
                port = smtp.SMTP_PORT
            smtp = smtp.SMTP_SSL(self.mailhost, port)
            msg = EmailMessage()
            msg['From'] = self.fromaddr
            msg['To'] = ','.join(self.toaddrs)
            msg['Subject'] = self.getSubject(record)
            msg['Date'] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(msg, self.fromaddr, self.toaddrs)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)