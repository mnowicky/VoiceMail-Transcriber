import threading

class job(object):

    staffcode="none"
    staffcode2="none"
    casenum=0
    phonenum=0
    numCalled=""
    uid="none"
    attachFile="none"
    transcript="none"
    eAddr=None
    eBody=None
    eSubj=None
    party="Not found"
    party_id=0
    callTime=None
    emailSent=False
    messageSent=False
    caseNoted=False
    phase="NEW"
    #phase = NEW right after creation. 
    #phase = DOWNLOADED when EmailReader has saved attachment and completed parsing email to job. 
    #phase = TRANSCRIBED when the transcription has been received back from Watson. 
    #phase = MATCHED when staff email and staffcode have ben populated. 
    #phase = SENT when email, and or message is sent successfully, if configured to do so. 
    #phase = DELETED when email is deleted from server. This flags the job for deletion. 

    def __init__(self, phonenum, numCalled, uid, attachFile):
         self.phonenum=phonenum
         self.numCalled=numCalled
         self.uid=uid
         self.attachFile=attachFile

    def print(self):
        assembled=""
        assembled=assembled+"Email UID: "+self.uid+" | "
        assembled=assembled+"Casenum: "+str(self.casenum)+" | "
        assembled=assembled+"Phonenum: "+str(self.phonenum)
        return assembled
        
class jobs(object):
    jobList = []
    completedUIDList = []
    waitEvent = threading.Event()

