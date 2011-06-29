from PyQt4.Qt import *
from connection import *
import sys, signal, argparse, datetime
signal.signal(signal.SIGINT, signal.SIG_DFL)


class FssCentralServer (QObject):
    connections=[]
    def __init__(self, homeDir, serverPort=55441):
        QObject.__init__(self)
        
        self.centralServer = QTcpServer()
        self.centralServer.listen(QHostAddress.Any, serverPort)
        self.centralServer.newConnection.connect(self.processNewConnection)
        self.fileMonitor = FssDirectoryManager(homeDir);

    def processNewConnection(self):
        def deleteConnection():
            self.connections.remove(clientConnection)

        def processRFileChangedRecieved(data):
            fileName=data.takeFirst()
            fileHash=data.takeFirst()
            if(self.fileMonitor.fileExists(fileName) and (self.fileMonitor.getFileHash(fileName)==fileHash)):
                print "Requested File= ", fileName
                print "fileHash Comparison","\nIncoming\t", fileHash, "\nLocal\t\t",self.fileMonitor.getFileHash(fileName)
                fileData=self.fileMonitor.getFileContents(fileName)
                dataPacket=QStringList()
                dataPacket.append ("d.FILE.CHANGED")
                dataPacket.append (fileName)
                dataPacket.append (fileData)        
                clientConnection.writeOutgoing(dataPacket)

        def sendFileChangedMessage(fileName):
            dataPacket = QStringList()
            dataPacket.append("m.FILE.CHANGED")
            timeStamp=str(datetime.datetime.now().time()) + " " + self.fileMonitor.getPeerName()
            print timeStamp
            dataPacket.append(timeStamp)
            dataPacket.append(fileName)
            dataPacket.append(self.fileMonitor.getFileHash(fileName))
            print "Hash: ", self.fileMonitor.getFileHash(fileName)
            clientConnection.writeOutgoing(dataPacket)

        def processMFileChangedRecieved(data):
            #TO-DO:check if the file exists already
            #compare oldHash and newHash
            print data.first()
            print "Peer Name: ",data.takeFirst()
            fileName=data.takeFirst()

            fileHash=data.takeFirst()
            if(self.fileMonitor.fileExists(fileName)):
                print "Comparing hash \n", self.fileMonitor.getFileHash(fileName), "\n", fileHash
                if (self.fileMonitor.getFileHash(fileName)==fileHash):
                    print "Alert: ", fileName, " upto date - not sending r.FILE.CHANGED"
                    return

            dataPacket=QStringList()
            dataPacket.append("r.FILE.CHANGED");
            dataPacket.append(fileName)
            dataPacket.append(fileHash)
            clientConnection.writeOutgoing(dataPacket)

        clientConnection=ClientConnection(self.centralServer.nextPendingConnection())
        clientConnection.disconnected.connect(deleteConnection)
        self.fileMonitor.fileModified.connect(sendFileChangedMessage)
        self.connections.append(clientConnection)
        clientConnection.dataFileChangedRecieved.connect( self.fileMonitor.writeRecievedModifications)
        clientConnection.requestFileChangedRecieved.connect(processRFileChangedRecieved)
        clientConnection.messageFileChangedRecieved.connect(processMFileChangedRecieved)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="FShSyServer")
    parser.add_argument("-home","--homeDir", type=QString)
    parser.add_argument("-oport","--serverPort", type=int)
    args = parser.parse_args()
    app = QCoreApplication(sys.argv) 
    n=FssCentralServer(args.homeDir, args.serverPort)
    app.exec_()
