import smtplib
from config import Config
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to, subject, message_html):
    msg = MIMEMultipart()
    msg["From"] = "digital.blog.mail@ya.ru"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(message_html, "html"))
    mailserver = smtplib.SMTP("smtp.yandex.ru", 587)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(Config.SENDER_EMAIL, Config.SENDER_PASSWORD)
    mailserver.sendmail(Config.SENDER_EMAIL, to, msg.as_string())
    mailserver.quit()
