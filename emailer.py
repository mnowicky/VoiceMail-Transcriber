import sys
import smtplib
from Logger import Logger
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

class emailer(object):
    """description of class"""

    #email params
    emailAddr = None
    emailPassword = None
    emailServer = None
    emailServerPort = 995
    emailSSL = False
    emailConnection = None
    emailSMTPPort = 587

    def __init__(self, emailAddr, emailPassword, emailServer, emailSMTPPort, ssl):
        self.emailAddr = emailAddr
        self.emailPassword = emailPassword
        self.emailServer = emailServer
        self.emailSMTPPort = emailSMTPPort
        self.emailSSL=ssl
        print("emailer initialized.")

    def connectSMTP(self):
        try:
            if(self.emailSSL):
                #self.emailConnection = smtplib.SMTP_SSL(self.emailServer, self.emailServerPort)

                self.emailConnection = smtplib.SMTP(self.emailServer, self.emailSMTPPort)
                self.emailConnection.ehlo()
                self.emailConnection.starttls()
                self.emailConnection.login(self.emailAddr, self.emailPassword)
            else:
                self.emailConnection = smtplib.SMTP(self.emailServer, self.emailSMTPPort)
                self.emailConnection.ehlo()
                self.emailConnection.starttls()
                self.emailConnection.login(self.emailAddr, self.emailPassword)
        except: 
            Logger.writeAndPrintLine("Could not connect specified SMTP email account."+traceback.format_exc(), 3)
            return False
        return True

    def disconnectSMTP(self):
        self.emailConnection.quit();

    def sendEMail(self, fromName, toAddr, subject,  body):
        try:
            self.connectSMTP()
            
            email = MIMEMultipart()
            email['From']=fromName
            email['To']=toAddr
            email['Subject']=subject
            email.attach(MIMEText(body, 'plain'))
            self.emailConnection.sendmail(self.emailAddr, toAddr, email.as_string())
            self.disconnectSMTP()
            return True
        except:
            Logger.writeAndPrintLine("Failed to send email: "+traceback.format_exc(),3)
            return False  

    def sendErrorEmail(self, message):
        self.sendEMail("Voicemail", "matthewn@williammattar.com", "VMT Error", message)

