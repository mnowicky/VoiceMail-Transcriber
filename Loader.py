import configparser
from EmailReader import EmailReader
from Transcriber import Transcriber
from Messenger import Messenger
import os
from threading import Thread
from Logger import Logger
import sys
import datetime
import time
from emailer import emailer
import traceback

class Loader(object):
	
	#config obj
    config = None
    configFileName="VoicemailTranscriber.config"

	#etc params
    runOnce = False
    idle = 5
    workingDir = os.getcwd()

	#email params
    emailAddr = None
    emailPassword = None
    emailServer = None
    emailServerPort = 995
    emailSSL = True
    emailDelete = False
    emailSMTPServer = None
    emailSMTPPort = 587
    emailPOPPort = 903

	#database params
    dbHost = None
    dbPort = 2638
    dbUser = "dba"
    dbPassword = "sql"
    dbDatabase = None

    #messaging params
    doEmail = True
    doMessage = True
    doNote = True

    mailer = None

	#Watson params
    watServiceFile =  "watsonCredential.json"

    #local vars
    reader = None
    transcriber = None
    messenger = None
    readerThread = None
    transcriberThread = None
    messengerThread = None

    def __init__(self):
        self.config = configparser.ConfigParser()

    def loadConfig(self):
        self.config.read(self.configFileName)

		#Etc configuration
        self.runOnce = self.config['DEFAULT']['runOnce']
        self.idle = int(self.config['DEFAULT']['idle'])

		#Email configuration
        self.emailAddr = self.config['EMAIL']['emailAddr']
        self.emailPassword = self.config['EMAIL']['password']
        self.emailServer = self.config['EMAIL']['server']
        self.emailPort = self.config['EMAIL']['port']
        self.emailSSL = self.config['EMAIL']['SSL']
        self.emailDelete = self.config['EMAIL']['deleteEmails']
        self.emailSMTPServer = self.config['EMAIL']['smtpServer']
        self.emailSMTPPort = self.config['EMAIL']['smtpPort']

		#Database configuration
        self.dbHost = self.config['DATABASE']['host']
        self.dbPort = self.config['DATABASE']['port']
        self.dbUser = self.config['DATABASE']['user']
        self.dbPassword = self.config['DATABASE']['password']
        self.dbDatabase = self.config['DATABASE']['database']

		#Watson configuration
        self.watServiceFile = self.config['WATSON']['serviceFile']

        #Messenger configuration
        self.doEmail = self.config['MESSENGER']['doEmail']
        self.doMessage = self.config['MESSENGER']['doMessage']
        self.doNote = self.config['MESSENGER']['doNote']

        #parse strings
        if(self.runOnce.upper()=="TRUE"):
            self.runOnce=True;
        else:
            self.runOnce=False;
        if(self.emailSSL.upper()=="TRUE"):
            self.emailSSL=True;
        else:
            self.emailSSL=False;
        if(self.emailDelete.upper()=="TRUE"):
            self.emailDelete=True;
        else:
            self.emailDelete=False;
        if(self.doEmail.upper()=="TRUE"):
            self.doEmail=True;
        else:
            self.doEmail=False;
        if(self.doMessage.upper()=="TRUE"):
            self.doMessage=True;
        else:
            self.doMessage=False;

    def printConfig(self):
        print("DEFAULT: ")
        print("runOnce: "+str(self.runOnce))
        print("idle: "+str(self.idle))
        print("")
        print("EMAIL: ")
        print("emailAddr: "+self.emailAddr)
        print("emailPassword: "+self.emailPassword)
        print("emailServer: "+self.emailServer)
        print("emailPort: "+self.emailPort)
        print("emailSSL: "+str(self.emailSSL))
        print("emailDelete: "+str(self.emailDelete))
        print("emailSMTPServer: "+str(self.emailSMTPServer))
        print("emailSMTPPort: "+str(self.emailSMTPPort))
        print("")
        print("DATABASE: ")
        print("dbHost: "+self.dbHost)
        print("dbPort: "+self.dbPort)
        print("dbUser: "+self.dbUser)
        print("dbPassword: "+self.dbPassword)
        print("dbDatabase: "+self.dbDatabase)
        print("")
        print("WATSON: ")
        print("watServiceFile: "+self.dbDatabase)
        print("")
        print("MESSENGER: ")
        print("doEmail: ", self.doEmail)
        print("doMessage: ", self.doMessage)
        print("")

    def run(self):
        Logger.writeAndPrintLine("Program started.", 0)
        self.loadConfig()
        print("Launching VoicemailTranscriber with the following parameters! :")
        self.printConfig()
		
        print("Loading email reader...")
        self.reader = EmailReader(self.emailAddr, self.emailPassword, self.emailServer, self.emailPOPPort, self.emailSSL, self.emailDelete, self.workingDir, self.idle)
        self.readerThread = Thread(target = self.reader.run)
        self.readerThread.start()
        print("email reader loaded, loading transcriber...")
        self.transcriber = Transcriber(self.watServiceFile, self.idle)
        self.transcriberThread = Thread(target = self.transcriber.run)
        self.transcriberThread.start()
        print("Transcriber loaded, loading messenger...")
        self.messenger = Messenger(self.emailAddr, self.emailPassword, self.emailServer, self.emailServerPort, self.emailSSL,
                              self.idle, self.doEmail, self.doMessage, self.doNote, self.dbHost, self.dbPort, self.dbUser, self.dbPassword, 
                              self.dbDatabase, self.emailSMTPServer, self.emailSMTPPort)
        self.messengerThread = Thread(target = self.messenger.run)
        self.messengerThread.start()
        print("Messenger loaded, loading emailer...")
        self.mailer = emailer(self.emailAddr, self.emailPassword, self.emailSMTPServer, self.emailSMTPPort, self.emailSSL)
        print("Loading complete.")
        self.monitor()

    def monitor(self):
        while(True):
            try:
                time.sleep(self.idle)
                currentTime=datetime.datetime.now()

                #first, check for new errors. 
                if(self.reader.errorAcknowledged==False):
                    if(self.reader.errorCount>=5):
                        Logger.writeAndPrintLine("Error in VMT emailReader experienced over 5 errors in past 10 minutes, terminating.",3)
                        self.mailer.sendErrorEmail("Error in VMT emailReader experienced over 5 errors in past 10 minutes, terminating.")
                        sys.exit(1)
                    else:
                        Logger.writeAndPrintLine("Error in VMT emailReader "+str(self.reader.lastErrorMessage),3)
                        self.mailer.sendErrorEmail("Error in VMT emailReader "+str(self.reader.lastErrorMessage))
                        self.reader.errorCount+=1
                    self.reader.errorAcknowledged=True

                if(self.transcriber.errorAcknowledged==False):
                    if(self.transcriber.errorCount>=5):
                        Logger.writeAndPrintLine("Error in VMT transcriber experienced over 5 errors in past 10 minutes, terminating.",3)
                        self.mailer.sendErrorEmail("Error in VMT transcriber experienced over 5 errors in past 10 minutes, terminating.")
                        sys.exit(1)
                    else:
                        Logger.writeAndPrintLine("Error in VMT transcriber"+str(self.transcriber.lastErrorMessage),3)
                        self.mailer.sendErrorEmail("Error in VMT transcriber"+str(self.transcriber.lastErrorMessage))
                        self.transcriber.errorCount+=1
                    self.transcriber.errorAcknowledged=True

                if(self.messenger.errorAcknowledged==False):
                    if(self.messenger.errorCount>=5):
                        Logger.writeAndPrintLine("Error in VMT messenger experienced over 5 errors in past 10 minutes, terminating.",3)
                        self.mailer.sendErrorEmail("Error in VMT messenger experienced over 5 errors in past 10 minutes, terminating.")
                        sys.exit(1)
                    else:
                        Logger.writeAndPrintLine("Error in VMT messenger "+str(self.messenger.lastErrorMessage),3)
                        self.mailer.sendErrorEmail("Error in VMT messenger "+str(self.messenger.lastErrorMessage))
                        self.messenger.errorCount+=1
                    self.messenger.errorAcknowledged=True

                #if last error was over 10 minutes ago, clear error counter. 
                if(currentTime-datetime.timedelta(minutes=10)>self.reader.lastErrorTime):
                    self.reader.errorCount=0
                if(currentTime-datetime.timedelta(minutes=10)>self.transcriber.lastErrorTime):
                    self.transcriber.errorCount=0
                if(currentTime-datetime.timedelta(minutes=10)>self.reader.lastErrorTime):
                    self.transcriber.errorCount=0

                if(self.readerThread.is_alive()==False):
                    Logger.writeAndPrintLine("readerThread terminated unexpectedly, restarting after 60 seconds. "+str(self.messenger.lastErrorMessage),3)
                    self.mailer.sendErrorEmail("readerThread terminated unexpectedly, restarting after 60 seconds. "+str(self.messenger.lastErrorMessage))
                    time.sleep(60)
                    self.readerThread = Thread(target = self.reader.run)
                    self.readerThread.start()
                if(self.transcriberThread.is_alive()==False):
                    Logger.writeAndPrintLine("readerThread terminated unexpectedly, restarting after 60 seconds. "+str(self.messenger.lastErrorMessage),3)
                    self.mailer.sendErrorEmail("readerThread terminated unexpectedly, restarting after 60 seconds. "+str(self.messenger.lastErrorMessage))
                    time.sleep(60)
                    self.transcriberThread = Thread(target = self.transcriber.run)
                    self.transcriberThread.start()
                if(self.messengerThread.is_alive()==False):
                    Logger.writeAndPrintLine("readerThread terminated unexpectedly, restarting after 60 seconds. "+str(self.messenger.lastErrorMessage),3)
                    self.mailer.sendErrorEmail("readerThread terminated unexpectedly, restarting after 60 seconds. "+str(self.messenger.lastErrorMessage))
                    time.sleep(60)
                    self.messengerThread = Thread(target = self.messenger.run)
                    self.messengerThread.start()
            except Exception as ex:
                Logger.writeAndPrintLine("Monitor crashed with error "+traceback.format_exc(),3)
                self.mailer.sendErrorEmail("Monitor crashed with error, VMT likely broken."+traceback.format_exc())
                break;

