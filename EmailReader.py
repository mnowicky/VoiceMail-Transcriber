import poplib
import quopri
import email
import os
import re
from job import job
from job import jobs
import time
from ioLib import ioLib
import sys
from Logger import Logger
import datetime
import traceback

class EmailReader(object):
   #Implements a pop3 client to read voicemail emails and parse them to XML jobs.

    #email params
    emailAddr = None
    emailPassword = None
    emailServer = None
    emailServerPort = 110
    emailSSL = False
    emailDelete = False
    initialized = False
    attachDir = os.getcwd()
    jobDir = os.getcwd()

    #local vars
    popServer = None
    running = True
    idle = 1
    errorCount=0
    lastErrorTime=datetime.datetime.now()
    lastErrorMessage = None
    errorAcknowledged=True
    
    def __init__(self, addr, password, server, port, ssl, delete, workingDir, idle):
       self.emailAddr=addr
       self.emailPassword=password
       self.emailServer=server
       self.emailServerPort=port
       self.emailSSL=ssl
       self.emailDelete=delete
       self.attachDir=workingDir+"\\attachments"
       #self.idle=idle

       #create folders if they do not exist.
       if(not os.path.exists(self.attachDir)):
            os.makedirs(self.attachDir)
       if(not os.path.exists(self.jobDir)):
            os.makedirs(self.jobDir)
       if(not self.connect()):
           Logger.writeAndPrintLine("Could not connect POP3 account. Program exiting.", 4)
           sys.exit()

    def connect(self):

        try:
            if(self.emailSSL):
                print(self.emailServer)
                self.popServer=poplib.POP3_SSL(self.emailServer)
            else:
                self.popServer=poplib.POP3(self.emailServer)
                self.popServer.port=self.emailServerPort
                self.popServer.user(self.emailAddr)
                self.popServer.pass_(self.emailPassword)
        except:
            return False
        return True
        

    def run(self):
        try:
            while self.running:
                time.sleep(self.idle)
                try:
                    print("Connecting to pop mailbox...")
                    #self.connect()
                    server = 'outlook.office365.com'
                    username = 'voicemail@williammattar.com'
                    password = 'Matt@r2019!'
                    self.popServer = poplib.POP3_SSL(server)
                    print(self.popServer.getwelcome())
                    self.popServer.user(username)
                    self.popServer.pass_(password)
                    popinfo = self.popServer.stat()
                    numMessages = popinfo[0]
                    print('Total number of emails: ' + str(numMessages))
                except:
                    Logger.writeAndPrintLine("Error connecting to POP3 email account.", 3)
                    continue
                #print("Number of emails: "+str(numMessages))
                for msgNum in range(numMessages):
                    try:
                        tempJob=self.tryMessage(msgNum+1)
                    except Exception as e:
                        print(e)
                        continue
                    if(tempJob==None):
                        try:
                            self.popServer.dele(msgNum+1)
                        except:
                            pass
                    elif(tempJob=="EXISTS"):
                        None
                    else:
                        tempJob.phase="DOWNLOADED"
                        jobs.jobList.append(tempJob)
                try:
                    self.popServer.quit()#We're done with emails. Closes the connection and triggers message deletion.
                except:
                    Logger.writeAndPrintLine("Error quitting POP3 connection.",3)

        except Exception as e: 
            print("An unexpected error occurred in EmailReader, halting: "+traceback.format_exc())  
            Logger.writeAndPrintLine("An unexpected error occurred in EmailReader, halting: "+traceback.format_exc(),3)   
            self.lastErrorMessage=traceback.format_exc()
            self.lastErrorTime=datetime.datetime.now()
            self.errorCount+=1
            self.errorAcknowledged=False
        Logger.writeAndPrintLine("Email reader exiting gracefully???",3) 


    def tryMessage(self, messageNum):
        #assemble message contents
        #print('assembling message contents...')
        raw_message = self.popServer.retr(messageNum)[1]
        str_message = email.message_from_bytes(b'\n'.join(raw_message))
        body = str(str_message.get_payload()[0])# GETS BODY
        messageUID=str(self.popServer.uidl(messageNum))
        messageUID=re.findall(r'\d+',messageUID,0)[1]
        #messageUID=re.findall('UID\d+-\d+',messageUID,0)[0] # <<<< PROBLEM LINE!
        
        #first, ignore duplicates. 
        for thisJob in jobs.jobList:
            if(thisJob.uid==messageUID):
                return "EXISTS"
        for completeUID in jobs.completedUIDList:
            if(completeUID==messageUID):
                return "EXISTS"

        #try parsing body into fields. 
        try:
            print('parsing body into fields...')
            phonenum=str(re.search('phonenum=(.+?)($|\W)',body, re.IGNORECASE).group(1))
            numCalled=str(re.search('num_called=(.+?)($|\W)',body, re.IGNORECASE).group(1))
            Logger.writeAndPrintLine("Successfully parsed email "+str(messageNum), 1)
        except:
            Logger.writeAndPrintLine("Failed to parse email "+str(messageNum)+": Email body parsing error.", 2)
            return None

        #get and check attachment, provided body is correct. 
        print('Body correct, check attachment')
        attachName=self.saveAttachment(str_message, self.attachDir, messageUID+".wav")# GETS ATTACHMENT AS FILENAME
        if(attachName==None):
            return None

        #if file is less than 150 bytes, it's not a real voicemail. 
        if(os.path.getsize(attachName)<=150):
            Logger.writeAndPrintLine("Attachment is too small to contain real voicemail, deleting "+str(messageNum)+'.', 2)
            return None

        tempJob=job(phonenum, numCalled, messageUID, attachName)
        tempJob.callTime=str(re.search('Date:\W(\w\w\w,\W\d{1,2}\W\w\w\w\W\d\d\d\d\W\d\d:\d\d:\d\d?)', str(str_message), re.IGNORECASE).group(1))
        return tempJob

    @staticmethod
    def saveAttachment(str_message, directory, idealFileName):
        for part in str_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                #print("no content dispo")
                continue

            filename=ioLib.getOriginalFileName(directory, idealFileName)
            print(filename)
            ##TODO: name file after email identifier. All email attaches will otherwise be named "voice.wav"
            fp = open(os.path.join(directory, filename), 'wb')
            fp.write(part.get_payload(decode=1))
            fp.close

            return directory+'\\'+filename
                