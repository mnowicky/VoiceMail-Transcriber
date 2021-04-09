from job import jobs
from job import job
import pyodbc
import re
import time
import smtplib
import poplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from Logger import Logger
import sys
import datetime
import traceback

class Messenger(object):

    #email params
    emailAddr = None
    emailPassword = None
    emailServer = None
    emailServerPort = 995
    emailSSL = False
    emailSMTPServer = None
    emailSMTPPort = 587

    #database params
    dbHost = None
    dbPort = 2638
    dbUser = "dba"
    dbPassword = "sql"
    dbDatabase = None

    #general params
    idle=1
    doEmail=True
    doMessage=True
    doNote = True

    #local vars
    dbConnection = None
    running = True
    emailConnection = None
    popServer = None
    errorCount=0
    lastErrorTime=datetime.datetime.now()
    lastErrorMessage = None
    errorAcknowledged=True

    def __init__(self, emailAddr, emailPassword, emailServer, emailServerPort, ssl, idle, doEmail, 
                 doMessage, doNote, dbHost, dbPort, dbUser, dbPassword, dbDatabase, smtpServer, smtpPort):
        self.emailAddr = emailAddr
        self.emailPassword = emailPassword
        self.emailServer = emailServer
        self.emailServerPort = emailServerPort
        self.emailSSL=ssl
        self.idle=idle
        self.doEmail = doEmail
        self.doMessage = doMessage
        self.doNote=doNote
        self.dbHost=dbHost
        self.dbPort=dbPort
        self.dbUser=dbUser
        self.dbPassword=dbPassword
        self.dbDatabase=dbDatabase
        self.emailSMTPServer = smtpServer
        self.emailSMTPPort = smtpPort

        if(not self.connectDB()):
            Logger.writeAndPrintLine("Could not connect to DB, please correct configuration. Program exiting.", 4)
            sys.exit()
        else:
            self.disconnectDB()

        if(not self.connectSMTP()):
            Logger.writeAndPrintLine("Could not connect to SMTP, please correct configuration. Program exiting.", 4)
            sys.exit()
        else:
            self.disconnectSMTP()

        if(not self.connectPOP()):
            Logger.writeAndPrintLine("Could not connect to POP, please correct configuration. Program exiting.", 4)
            sys.exit()
        else:
            self.disconnectPOP()

    def connectDB(self):
        try:
            self.dbConnection = pyodbc.connect('UID='+self.dbUser+';PWD='+self.dbPassword+';DSN='+self.dbHost)
        except: 
            Logger.writeAndPrintLine("Could not connect specified database.", 3)    
            return False
        return True

    def disconnectDB(self):
        self.dbConnection.close()

    def connectSMTP(self):
        try:
            if(self.emailSSL):
                #first line is old code, used for rackspace email acct
                #self.emailConnection = smtplib.SMTP_SSL(self.emailSMTPServer, self.emailSMTPPort)
                #Logger.writeAndPrintLine("=====MESSENGER=====", 1)
                self.emailConnection = smtplib.SMTP(self.emailServer, self.emailSMTPPort)
                self.emailConnection.ehlo()
                self.emailConnection.starttls()
                self.emailConnection.login(self.emailAddr, self.emailPassword)
                #Logger.writeAndPrintLine("...SUCCESS", 1)
				
            else:
                self.emailConnection = smtplib.SMTP(self.emailSMTPServer, self.emailSMTPPort)
            self.emailConnection.login(self.emailAddr, self.emailPassword)
        except: 
            Logger.writeAndPrintLine("Could not connect specified SMTP email account.", 3)
            return False
        return True

    def connectPOP(self):
        try:
            if(self.emailSSL):
                self.popServer=poplib.POP3_SSL(self.emailServer)
            else:
                self.popServer=poplib.POP3(self.emailServer)
            self.popServer.port=self.emailServerPort
            self.popServer.user(self.emailAddr)
            self.popServer.pass_(self.emailPassword)
        except:
            return False
        return True

    def disconnectSMTP(self):
        self.emailConnection.quit();

    def disconnectPOP(self):
        self.popServer.quit()

    def run(self):
        try:
            while(self.running):
                if(self.connectDB()):
                    for tempJob in jobs.jobList:
                        if(tempJob.phase=="TRANSCRIBED"):
                            self.message(tempJob)
                            #return
                    self.disconnectDB()
                self.handleDeletions()
                time.sleep(self.idle)
        except Exception as e:
            print("An unexpected error occurred in Messenger, halting: "+traceback.format_exc())
            Logger.writeAndPrintLine("An unexpected error occurred in Messenger, halting: "+traceback.format_exc(),3)    
            self.lastErrorMessage=traceback.format_exc()
            self.lastErrorTime=datetime.datetime.now()
            self.errorCount+=1
            self.errorAcknowledged=False

    def message(self, tempJob):
        self.matchStaff(tempJob)

        if(self.doEmail):
            tempJob.emailSent=self.sendEmail(tempJob)
        if(self.doMessage):
            tempJob.messageSent=self.sendMessage(tempJob)
        if(self.doNote):
            tempJob.caseNoted=self.noteCase(tempJob)

        if(self.doEmail==tempJob.emailSent and self.doMessage==tempJob.messageSent
           and self.doMessage==tempJob.messageSent):
            tempJob.phase="SENT"
        else:
            Logger.writeAndPrintLine("Not all messages delivered, sleeping 60 seconds and retrying.", 3)
            time.sleep(60)

    def matchStaff(self, tempJob):

        if('7168171035' in tempJob.numCalled):
            tempJob.party_id=None
            tempJob.casenum=0
            tempJob.staffcode='CMW'
            tempJob.staffcode2='CPER'
            tempJob.eAddr='referrals@williammattar.com'
            return
			
        print('phone number is: ')			
        print(str(tempJob.phonenum))
        #party_id
        sql="select top 1 id from WKM_party_phone_numbers where phonenum='"+str(tempJob.phonenum)+"' order by phonenum, case when type='car' then 1 when type='home' then 2 when type='work' then 3 else 4 end"
        cursor=self.dbConnection.cursor()
        cursor.execute(sql)
        rowset=cursor.fetchone()
        print("rowset is: ")
        print(str(rowset))
        if(rowset==None):
            tempJob.party_id=None
        else:
            tempJob.party_id=rowset[0]
        
        #party name
        sql="select sp_name('"+str(tempJob.party_id)+"',1)"
        cursor=self.dbConnection.cursor()
        cursor.execute(sql)
        rowset=cursor.fetchone()
        tempJob.party=rowset[0]

        #casenum
        sql="select top 1 cases.casenum from cases inner join party on cases.casenum=party.case_id where party_id='"+str(tempJob.party_id)+"' and cases.matcode NOT IN ('REF','REJ','RRF','XGN','XMT','XMV','XSF','XSS','XWC','RCY','TST') order by cases.open_status desc"
        cursor=self.dbConnection.cursor()
        cursor.execute(sql)
        rowset=cursor.fetchone()
        if(rowset==None):
            tempJob.casenum=0
        else:
            tempJob.casenum=rowset[0]
        
        if(tempJob.casenum!=0):
            #staff_1
            sql="select top 1 (CASE WHEN MATCODE IN ('IMV','IGP','ISF') THEN 'ZAJH' WHEN staff.active='Y' then staff.staff_code else 'INACTIVE' END) from cases left join staff on cases.staff_1=staff.staff_code where casenum='"+str(tempJob.casenum)+"'"
            cursor=self.dbConnection.cursor()
            cursor.execute(sql)
            rowset=cursor.fetchone()
            try:
                tempJob.staffcode=rowset[0]
            except:
                tempJob.staffcode="INACTIVE"
            #staff_2
            sql="select top 1 (CASE WHEN MATCODE IN ('IMV','IGP','ISF') THEN 'SL' ELSE staff_2 end) from cases where casenum='"+str(tempJob.casenum)+"'"
            cursor=self.dbConnection.cursor()
            cursor.execute(sql)
            rowset=cursor.fetchone()
            try:
                tempJob.staffcode2=rowset[0]
            except:
                tempJob.staffcode2="INACTIVE";
                Logger.writeAndPrintLine("Failed to find email address for staff "+tempJob.staffcode+", defaulting to reception.", 2)
        else:
            #this is a caseless provider. We will use "inactive" to sink notifications to reception.
            tempJob.staffcode="INACTIVE"
            tempJob.staffcode2="INACTIVE"

        if(tempJob.staffcode=='INACTIVE'):
            tempJob.eAddr='reception@williammattar.com'
        else:
            #staff_1 email
            sql="SELECT top 1 email from staff where staff_code='"+tempJob.staffcode+"'"
            cursor=self.dbConnection.cursor()
            cursor.execute(sql)
            rowset=cursor.fetchone()
            try:
                tempJob.eAddr=rowset[0]
            except:
                tempJob.eAddr='reception@williammattar.com'
                Logger.writeAndPrintLine("Failed to find email address for staff "+tempJob.staffcode+", defaulting to reception.", 2)

        #print(str(tempJob.casenum)+'='+tempJob.staffcode+'='+tempJob.eAddr)
        if((tempJob.staffcode!="none" and tempJob.staffcode!=None and tempJob.staffcode!="") and
           (tempJob.eAddr!=None and tempJob.eAddr!="" and tempJob.eAddr!="none")):
           tempJob.phase="MATCHED"

    def sendEmail(self, tempJob):
        subject = self.constructSubject(tempJob)
        body = self.constructBody(tempJob)

        email = MIMEMultipart()
        email['From']=self.emailAddr
        email['To']=tempJob.eAddr
        email['Subject']=subject
        email.attach(MIMEText(body, 'plain'))

        #handle attachment
        filename="voicemail.wav"
        attachment=open(tempJob.attachFile, 'rb')
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
        email.attach(part)
        attachment.close()
        try:
            self.connectSMTP()
            self.emailConnection.sendmail(self.emailAddr, tempJob.eAddr, email.as_string())
            self.emailConnection.sendmail(self.emailAddr, "oluwadare@williammattar.com", email.as_string())
            self.emailConnection.sendmail(self.emailAddr, "mgrant@williammattar.com", email.as_string())
            self.disconnectSMTP()
        except:
            Logger.writeAndPrintLine("Could not send email."+traceback.format_exc(), 3)
            return False

        Logger.writeAndPrintLine("Email SENT for job "+tempJob.print()+" to "+tempJob.eAddr, 1)
        return True

    def sendMessage(self, tempJob):
        subject = self.constructSubject(tempJob)
        if(tempJob.party_id==None): 
            tempJob.party_id='null'
        if(tempJob.staffcode=="INACTIVE" and tempJob.staffcode2=="INACTIVE"):
            body = subject+':\n'+self.constructBodyAdjuster(tempJob)
        else:
            body = subject+':\n'+self.constructBody(tempJob)
        recipients=tempJob.staffcode+'; '+tempJob.staffcode2
        body=body.replace("'", "''")
        body=body.replace('\n', "'+CHAR(13)+CHAR(10)+'")

        # Commit statements are REQUIRED. DB will hang if they are not used. 
        # INACTIVE staff1+2=Reception. We don't do anything special for single inactive scenarios. 
        if(tempJob.staffcode=="INACTIVE" and tempJob.staffcode2=="INACTIVE"):
            #Message group reception
            sql=("exec WKM_InsertMessageGroup "+"'RECEPTION','"+body+"','"+str(tempJob.casenum)
                 +"',"+str(tempJob.party_id)+",'"+str(tempJob.phonenum)+"','SYSTEM','N' commit")
            Logger.writeAndPrintLine("Sending message to reception: "+sql, 1)
            try:
                cursor=self.dbConnection.cursor()
                cursor.execute(sql)
                cursor.close()
            except:
                return False
        else:
            #message staff_1
            sql=("exec WKM_InsertMessage '"+tempJob.staffcode+"','"+recipients+"','"+body+"','"
                +str(tempJob.casenum)+"',"+str(tempJob.party_id)+",'"+str(tempJob.phonenum)+"' commit")
            Logger.writeAndPrintLine("Sending message: "+sql, 1)
            try:
                cursor=self.dbConnection.cursor()
                cursor.execute(sql)
                cursor.close()
            except:
                return False

            #message staff_2
            sql=("exec WKM_InsertMessage '"+tempJob.staffcode2+"','"+recipients+"','"+body+"','"
                +str(tempJob.casenum)+"',"+str(tempJob.party_id)+",'"+str(tempJob.phonenum)+"' commit")
            try:
                cursor=self.dbConnection.cursor()
                cursor.execute(sql)
                cursor.close()
            except:
                return False

        Logger.writeAndPrintLine("Needles message SENT: "+sql, 1)
        return True

    def noteCase(self, tempJob):
        subject = self.constructSubject(tempJob)
        body = subject+':\n'+self.constructBody(tempJob)
        body=body.replace("'", "''")
        body=body.replace('\n', "'+CHAR(13)+CHAR(10)+'")

        # Commit statements are REQUIRED. DB will hang if they are not used. 
        sql=("exec WKM_InsertCaseNote '"+"Voicemail"+"','"+body+"','"+"SYSTEM"+"','"
            +str(tempJob.casenum)+"' commit")
        try:
            cursor=self.dbConnection.cursor()
            cursor.execute(sql)
            cursor.close()
        except:
            return False
        Logger.writeAndPrintLine("Case noted: "+sql, 1)
        return True

    def constructBody(self, tempJob):
        body="Please return a call to client, as soon as possible."+'\n'+'\n'
        body+="Message: "+tempJob.transcript+'\n'
        body+="Party: "+tempJob.party+'\n'
        body+="Case: "+str(tempJob.casenum)+'\n'
        body+="Time: "+tempJob.callTime+'\n'
        body+="CallerID: "+str(tempJob.phonenum)+'\n'
        return body

    def constructBodyAdjuster(self, tempJob):
        body="Adjuster left the following voicemail:"+'\n'+'\n'
        body+="Message: "+tempJob.transcript+'\n'
        body+="Party: "+tempJob.party+'\n'
        body+="Time: "+tempJob.callTime+'\n'
        body+="CallerID: "+str(tempJob.phonenum)+'\n'
        return body

    def constructSubject(self, tempJob):
        subject = "Voicemail from "+tempJob.party
        return subject
    
    def handleDeletions(self):
        deleteList = []

        if(jobs.jobList.count==0):
            return None

        for i in range(len(jobs.jobList)):
            tempJob=jobs.jobList[i-1]
            if(tempJob.phase=="SENT"):
                if(self.deleteEmail(tempJob.uid)):
                    tempJob.phase="DELETED"
            if(tempJob.phase=="DELETED"):
                Logger.writeAndPrintLine("Job complete! Deleting: "+tempJob.print(), 1)
                deleteList.append(i-1)

        if(deleteList.count==0):
            return None
        for deleteJob in reversed(deleteList):
            del jobs.jobList[deleteJob]

    def deleteEmail(self, emailUID):
       if(not self.connectPOP()):
           Logger.writeAndPrintLine("Could not connect to POP server for email deletion.", 3)
           return False

       allUIDs=self.popServer.uidl()
       allUIDs=str(allUIDs[1])
       regex="(\d+?)\W"+emailUID
       #I'm going to assume that if this errors, than the UID did not exist in the list,
       #soo we can consider that email already deleted.  
       try:
           indexNum=int(str(re.search(regex,allUIDs, re.IGNORECASE).group(1)))
       except:
           return True
       try:
           jobs.completedUIDList.append(emailUID)
           if(len(jobs.completedUIDList)>=10):
               del jobs.completedUIDList[0]
           self.popServer.dele(indexNum)
       except: 
           return False
       finally: 
           self.popServer.quit()
       return True