from PyQt4.Qt import *

class ClientConnection (QObject):
    
    dataRecieved=pyqtSignal(QStringList)
    disconnected=pyqtSignal()
    messageFileChangedRecieved=pyqtSignal(QStringList)
    messageFileDeletedRecieved=pyqtSignal(QStringList)
    requestFileChangedRecieved=pyqtSignal(QStringList)
    dataFileChangedRecieved=pyqtSignal(QStringList)

    def __init__(self,socket):
        QObject.__init__(self)
        self.socket = socket;
        print "Alert: Connected to ", str(self.socket.peerAddress())," ",self.socket.peerPort()
        self.socket.readyRead.connect(self.readIncoming)
        self.dataRecieved.connect(self.processHeader)

        self.messageFileChangedRecieved.connect(self.processMFileChangedRecieved)
        #self.requestFileChangedRecieved.connect(self.processRFileChangedRecieved)
        #self.dataFileChangedRecieved.connect(self.processDFileChangedRecieved)
        self.socket.disconnected.connect(self.emitDisconnected)

    def emitDisconnected(self):
        self.disconnected.emit()

    def readIncoming(self):
        print "Alert: Data Avaiable for Reading"
        readStream=QDataStream(self.socket)
        if (self.socket.bytesAvailable() < 2):
            return
        size=readStream.readUInt16()
        for i in range(0,10):
            if(self.socket.bytesAvailable() == size):
                print 'Alert: got it'
                break
            else:
                print "Alert: Waiting for data. Available=", self.socket.bytesAvailable(), "< should be", size
                self.socket.waitForReadyRead()

        data = readStream.readQStringList()
        self.dataRecieved.emit(data)

    def processHeader(self, dataPacket):
        """
        Reads first QStringList (header) from the dataPacket and fires appropriate signal depending 
        upon the value of the header
        """
        header = dataPacket.takeFirst()
        print header
        if (header == QString("m.FILE.CHANGED")):
            self.messageFileChangedRecieved.emit(dataPacket)
            #LATER: this should be connected to a slot which locks the file allowing no further get requests.

        elif(header == QString("m.FILE.DELETED")):
            self.messageFileDeletedRecieved.emit(dataPacket)
        
        elif (header == QString("r.FILE.CHANGED")):
            self.requestFileChangedRecieved.emit(dataPacket)

        elif (header == QString("d.FILE.CHANGED")):
            self.dataFileChangedRecieved.emit(dataPacket)
              
        else:
            pass

    def sendFileChangedMessage(self, fileName):
        dataPacket = QStringList()
        dataPacket.append("m.FILE.CHANGED")
        dataPacket.append(fileName)

        self.writeOutgoing(dataPacket)

    def processMFileChangedRecieved(self, data):
        #TO-DO:check if the file exists already
        #compare oldHash and newHash
        print data.first()
        fileExists=True;
        if(fileExists):
            dataPacket=QStringList()
            dataPacket.append("r.FILE.CHANGED");
            dataPacket.append(data.takeFirst())
            self.writeOutgoing(dataPacket)

    
    def writeOutgoing(self,data):
        
        byteArray=QByteArray()
        writeStream=QDataStream (byteArray, QIODevice.WriteOnly)
        writeStream.setVersion(QDataStream.Qt_4_0)
        writeStream.writeUInt16(0)
        writeStream.writeQStringList(data)
        writeStream.device().seek(0)
        writeStream.writeUInt16(byteArray.size() - 2)
        self.socket.write(byteArray)

class FssDirectoryManager(QObject):
    fileModified=pyqtSignal(QString)
    fileDeleted=pyqtSignal(QString)
    
    fileHash={}
    
    def __init__(self, directory):
        QObject.__init__(self)
        self.directory= directory

        self.watcher=QFileSystemWatcher()
        self.dirfiles =list( QDir(self.directory))

        for i in list(QDir(self.directory).entryInfoList()):
            if(i.isFile()):
                self.watcher.addPath(i.absoluteFilePath())
                
        self.watcher.addPath(directory)
        self.watcher.directoryChanged.connect(self.processDirChanged)

        self.watcher.fileChanged.connect(self.processFileChanged)
        print list(self.watcher.directories())
        print list(self.watcher.files())

    def processDirChanged(self, changed):
        newlist = set(list(QDir(self.directory)))
        oldlist = set(self.dirfiles)
        newFiles = newlist - oldlist
        removedFiles = oldlist - newlist
        for i in removedFiles:
            self.fileDeleted.emit(i)
            self.dirfiles.remove(i);
            print "removing: ", i
 
        for i in newFiles:
            self.fileModified.emit(i)
            self.dirfiles.append(i)
            #self.watcher.addPath(i.fileName())
            print "appending: ", i

    def processFileChanged(self, changed):
        print "Alert: File Changed :", changed
        self.fileModified.emit(changed)
                
    def displayChange(self, change):
        print "changed ", change

    def writeRecievedModifications(self,dataPacket):
        fileName=dataPacket.takeFirst()
        fileData=dataPacket.takeFirst().toUtf8()
        print "writing Recieved Data", fileName, fileData        
        f = QFile(self.directory + '/'+ fileName)
        if(f.open(QIODevice.WriteOnly)):
            f.write(QByteArray.fromBase64(fileData))
        else:
            print "couldn't open file: ", f.fileName()

    
    def getFileContents(self,fileName):
        f = QFile(self.directory + '/' + fileName)
        if(f.open(QIODevice.ReadOnly)):
            return(f.readAll())
        else:
            print "Error: couldn't open file: ", f.fileName()
        return None
