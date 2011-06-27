from PyQt4.Qt import *
from connection import *
import sys, signal, argparse
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

<<<<<<< HEAD
        def processRFileChangedRecieved(data):
            fileName=data.takeFirst()
            fileData=self.fileMonitor.getFileContents(fileName)
            if(fileData):
                dataPacket=QStringList()
                dataPacket.append ("d.FILE.CHANGED")
                dataPacket.append (fileName)
                dataPacket.append (QString(fileData.toBase64()))        
                clientConnection.writeOutgoing(dataPacket)

=======
>>>>>>> parent of ed9d4f1... new file interchange successful - modification unsuccessful
        clientConnection=ClientConnection(self.centralServer.nextPendingConnection())
        clientConnection.disconnected.connect(deleteConnection)
        self.fileMonitor.fileModified.connect(clientConnection.sendFileChangedMessage)
        self.connections.append(clientConnection)
        
        

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="FShSyServer")
    parser.add_argument("-home","--homeDir", type=QString)
    parser.add_argument("-oport","--serverPort", type=int)
    args = parser.parse_args()
    app = QCoreApplication(sys.argv)
    n=FssCentralServer(args.homeDir, args.serverPort)
    app.exec_()
