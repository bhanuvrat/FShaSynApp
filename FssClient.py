from PyQt4.Qt import *
from connection import *
import sys, signal, argparse, datetime
signal.signal(signal.SIGINT, signal.SIG_DFL)

class FssClient (QObject):
    
    def __init__(self, homeDir, serverAddr, serverPort=55441):
        QObject.__init__(self)

        def processRFileChangedRecieved(data):
            fileName=data.takeFirst()
            fileHash=data.takeFirst()
            if(self.fileMonitor.fileExists(fileName) and (self.fileMonitor.getFileHash(fileName)==fileHash)):
                print "Requested File :", fileName
                print "fileHash Comparison","\nIncoming\t", fileHash, "\nLocal\t\t",self.fileMonitor.getFileHash(fileName)
                fileData=self.fileMonitor.getFileContents(fileName)
                dataPacket=QStringList()
                dataPacket.append ("d.FILE.CHANGED")
                dataPacket.append (fileName)
                dataPacket.append (fileData)        
                self.connection.writeOutgoing(dataPacket)

        def sendFileChangedMessage(fileName):
            dataPacket = QStringList()
            dataPacket.append("m.FILE.CHANGED")            
            timeStamp = str(datetime.datetime.now().time()) + " " + self.fileMonitor.getPeerName() 
            print timeStamp
            dataPacket.append(timeStamp)
            dataPacket.append(fileName)
            dataPacket.append(self.fileMonitor.getFileHash(fileName))
            print "Hash: ", self.fileMonitor.getFileHash(fileName)
            self.connection.writeOutgoing(dataPacket)
            
        def sendFileDeletedMessage(fileName):
            dataPacket = QStringList()
            dataPacket.append("m.FILE.DELETED")
            dataPacket.append(fileName)
            self.connection.writeOutgoing(dataPacket)
            
        def processMFileChangedRecieved(data):
            #TO-DO:check if the file exists already
            #compare oldHash and newHash
            print data.first()
            print "Peer Name: ", data.takeFirst()
            fileName=data.takeFirst()
            fileHash=data.takeFirst()
            if(self.fileMonitor.fileExists(fileName)):
                print "Comparing hash \nIncoming\t", fileHash, "\nLocal\t",self.fileMonitor.getFileHash(fileName)
                if (self.fileMonitor.getFileHash(fileName)==fileHash):
                    print "Alert: ", fileName, " upto date - not sending r.FILE.CHANGED"
                    return

            dataPacket=QStringList()
            dataPacket.append("r.FILE.CHANGED");
            dataPacket.append(fileName)
            dataPacket.append(fileHash)
            self.connection.writeOutgoing(dataPacket)
                
        def processMFileDeletedRecieved(data):
            self.fileMonitor.removeDeletedFile(data.takeFirst())
            
        self.fileMonitor = FssDirectoryManager(homeDir);
        self.clientSocket = QTcpSocket()
        self.clientSocket.connectToHost(QHostAddress(serverAddr), serverPort)
        self.connection = ClientConnection(self.clientSocket)
        self.fileMonitor.fileModified.connect(sendFileChangedMessage)
        self.fileMonitor.fileDeleted.connect(sendFileDeletedMessage)
        self.connection.requestFileChangedRecieved.connect(processRFileChangedRecieved)
        
        self.connection.dataFileChangedRecieved.connect( self.fileMonitor.writeRecievedModifications)
        self.connection.messageFileChangedRecieved.connect(processMFileChangedRecieved)
        self.connection.messageFileDeletedRecieved.connect(processMFileDeletedRecieved)
        
        

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="FShSyServer")
    parser.add_argument("-home","--homeDir", type=QString)
    parser.add_argument("-saddr","--serverAddr", type=QString)
    parser.add_argument("-sport","--serverPort", type=int)
    args = parser.parse_args()
    app = QCoreApplication(sys.argv)
    n=FssClient(args.homeDir, args.serverAddr, args.serverPort)
    app.exec_()
