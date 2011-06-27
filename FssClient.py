from PyQt4.Qt import *
from connection import *
import sys, signal, argparse
signal.signal(signal.SIGINT, signal.SIG_DFL)

class FssClient (QObject):
    
    def __init__(self, homeDir, serverAddr, serverPort=55441):
        QObject.__init__(self)

        def processRFileChangedRecieved(data):
            fileName=data.takeFirst()
            print "Requested File :", fileName
            fileData=self.fileMonitor.getFileContents(fileName)
            dataPacket=QStringList()
            dataPacket.append ("d.FILE.CHANGED")
            dataPacket.append (fileName)
            dataPacket.append (QString(fileData.toBase64()))        
            self.connection.writeOutgoing(dataPacket)


        self.fileMonitor = FssDirectoryManager(homeDir);
        self.clientSocket = QTcpSocket()
        self.clientSocket.connectToHost(QHostAddress(serverAddr), serverPort)
        self.connection = ClientConnection(self.clientSocket)
        self.fileMonitor.fileModified.connect(self.connection.sendFileChangedMessage)
        self.connection.requestFileChangedRecieved.connect(processRFileChangedRecieved)
        
        self.connection.dataFileChangedRecieved.connect( self.fileMonitor.writeRecievedModifications)



if __name__=="__main__":
    parser = argparse.ArgumentParser(description="FShSyServer")
    parser.add_argument("-home","--homeDir", type=QString)
    parser.add_argument("-saddr","--serverAddr", type=QString)
    parser.add_argument("-sport","--serverPort", type=int)
    args = parser.parse_args()
    app = QCoreApplication(sys.argv)
    n=FssClient(args.homeDir, args.serverAddr, args.serverPort)
    app.exec_()
