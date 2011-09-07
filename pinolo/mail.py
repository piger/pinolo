import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import traceback
import StringIO

MAIL_SERVER = ""

def sendmail(sender, to, subject, message):
    mail = MIMEText(message)
    mail['Subject'] = subject
    mail['From'] = sender
    mail['To'] = to

    try:
        s = smtplib.SMTP(MAIL_SERVER)
        s.sendmail(sender, [to], mail.as_string())
        s.quit()
    except Exception, e:
        print "ERROR:"
        print e

def mail_exception(sender, to, subject):
    fp = StringIO.StringIO()
    traceback.print_exc(file=fp)
    message = fp.getvalue()

    sendmail(sender, to, subject, message)

try:
    1 / 0
except Exception, e:
    mail_exception("bug@", "me@me", "test bug")
