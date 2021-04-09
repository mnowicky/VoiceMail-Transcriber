import os.path

class ioLib(object):
    """description of class"""

    @staticmethod
    def getOriginalFileName(directory, idealFileName):
        #filename is good, out of the box. 
        if(not os.path.isfile(directory+'\\'+idealFileName)):
           return idealFileName

        #else file exists
        filename, extension = os.path.splitext(idealFileName)
        extender = 1
        while(True):
            newFileName=filename+'_'+str(extender)+extension
            tryFile=directory+'\\'+newFileName
            if(not os.path.isfile(tryFile)):
                return newFileName
            extender+=1

