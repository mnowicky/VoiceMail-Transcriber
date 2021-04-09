from __future__ import print_function
import json
from os.path import join, dirname
from watson_developer_cloud import SpeechToTextV1
#from ibm_watson import SpeechToTextV1
#from ibm_cloud_sdk_core.authenticators import BasicAuthenticator
from job import jobs
import time
import os.path
from Logger import Logger
import datetime
import traceback

class Transcriber(object):

    #Watson Vars
    watServiceFile="watsonCredential.json"

    #Local Vars
    idle=5
    running=True
    username = "none"
    password = "none"
    errorCount=0
    lastErrorTime=datetime.datetime.now()
    lastErrorMessage = None
    errorAcknowledged=True

    speech_to_text = None

    def __init__(self, watServiceFile, idle):
        self.watServiceFile=watServiceFile
        self.idle=idle
        self.parseServiceFile(self.watServiceFile)
        self.speech_to_text = SpeechToTextV1(username=self.username,password=self.password,
            x_watson_learning_opt_out=False)

    def parseServiceFile(self, watServiceFile):
        textFile=open(watServiceFile,'rb')
        fullText=textFile.read().decode("utf-8")
        textFile.close()
        parsedJson=json.loads(str(fullText))
        self.username=parsedJson['username']
        self.password=parsedJson['password']

    def run(self):
        try:
            while(self.running):
                for tempJob in jobs.jobList:
                    if(tempJob.phase=="DOWNLOADED"):
                        tempJob.transcript=self.transcribeAttachment(tempJob.attachFile)
                        if(not(tempJob.transcript==None or tempJob.transcript=="none")):
                            tempJob.phase="TRANSCRIBED"
                            Logger.writeAndPrintLine("Transcribed job: "+tempJob.print()+" transcript: "+tempJob.transcript, 1)
                time.sleep(self.idle)
        except:
            print("An unexpected error occurred in Transcriber, halting: "+traceback.format_exc())  
            Logger.writeAndPrintLine("An unexpected error occurred in Transcriber, halting: "+traceback.format_exc(),3)   
            self.lastErrorMessage=traceback.format_exc()
            self.lastErrorTime=datetime.datetime.now()
            self.errorCount+=1
            self.errorAcknowledged=False

    def transcribeAttachment(self, attachFilename):
        try:
            #jsonText=self.askFile(attachFilename)
            jsonText=self.askWatson(attachFilename)
        except Exception as e:
           Logger.writeAndPrintLine("An unexpected error occurred in Transcriber while asking watson. Continuing.",3)
           return traceback.format_exc(0);
        
        jsonText=str(jsonText)#.replace('\\r\\n','')
        parsedJson=json.loads(jsonText)
        transcript=""
        try:
            altList=parsedJson['results']
            for i in range(0, len(altList)):
                transcript+=parsedJson['results'][i]['alternatives'][0]['transcript']
        except:
            Logger.writeAndPrintLine("Watson did not return any proper results. "+str(parsedJson),3)
            return "No transcript could be produced."
        return transcript

    def askWatson(self, audioFilename):
        audio_file=open(audioFilename,'rb')
        jsonReply=self.speech_to_text.recognize(audio_file, content_type='audio/wav', timestamps=True, word_confidence=True, model='en-US_NarrowbandModel')
        reply=json.dumps(jsonReply,indent=2)
        audio_file.close()
        return reply

    def askFile(self, audioFilename):
        textFile=open('\\\\MattarFS01\\Users\\treusch\\Documents\\Visual Studio 2015\\Projects\\VoicemailTranscriber\\VoicemailTranscriber\\reply2.json','rb')
        fullText=textFile.read().decode("utf-8")
        textFile.close()
        return fullText