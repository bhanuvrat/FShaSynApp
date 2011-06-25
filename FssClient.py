from PyQt4.Qt import *
from connection import *
import sys, signal, argparse
signal.signal(signal.SIGINT, signal.SIG_DFL)

class FssClient (QObject):
    
    def __init__(self, homeDir, serverAddr, serverPort=55441):
        QObject.__init__(self)

        self.fileMonitor = FssDirectoryManager(homeDir);
        self.clientSocket = QTcpSocket()
        self.clientSocket.connectToHost(QHostAddress(serverAddr), serverPort)
        self.connection = ClientConnection(self.clientSocket)
        self.fileMonitor.fileModified.connect(self.connection.sendFileChangedMessage);

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="FShSyServer")
    parser.add_argument("-home","--homeDir", type=QString)
    parser.add_argument("-saddr","--serverAddr", type=QString)
    parser.add_argument("-sport","--serverPort", type=int)
    args = parser.parse_args()
    app = QCoreApplication(sys.argv)
    n=FssClient(args.homeDir, args.serverAddr, args.serverPort)
    app.exec_()
