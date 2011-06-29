from PyQt4.Qt import *
import traceback
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

        #self.messageFileChangedRecieved.connect(self.processMFileChangedRecieved)
        #self.requestFileChangedRecieved.connect(self.processRFileChangedRecieved)
        #self.dataFileChangedRecieved.connect(self.processDFileChangedRecieved)
        self.socket.disconnected.connect(self.emitDisconnected)

    def emitDisconnected(self):
        self.disconnected.emit()

    def readIncoming(self):
        #print "Alert: Data Avaiable for Reading"
        readStream=QDataStream(self.socket)
        if (self.socket.bytesAvailable() < 2):
            return
        size=readStream.readUInt16()
        for i in range(0,10):
            if(self.socket.bytesAvailable() >= size):
                #print 'Alert: got it'
                break
            else:
                #print "Alert: Waiting for data. Available=", self.socket.bytesAvailable(), "< should be", size
                self.socket.waitForReadyRead()

        data = readStream.readQStringList()
        self.dataRecieved.emit(data)

    def processHeader(self, dataPacket):
        """
        Reads first QStringList (header) from the dataPacket and fires appropriate signal depending 
        upon the value of the header
        """
        header = dataPacket.takeFirst()
        print "Alert: Just Recieved : ", header
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

    
    def writeOutgoing(self,data):
        print "Alert: Sending :", data.first()
        byteArray=QByteArray()
        writeStream=QDataStream (byteArray, QIODevice.WriteOnly)
        writeStream.setVersion(QDataStream.Qt_4_0)
        writeStream.writeUInt16(0)
        writeStream.writeQStringList(data)
        writeStream.device().seek(0)
        writeStream.writeUInt16(byteArray.size() - 2)
        print "Alert: writing to socket :", byteArray.size() ," bytes"
        self.socket.write(byteArray)
        self.socket.flush()  

class FssDirectoryManager(QObject):
    fileModified=pyqtSignal(QString)
    fileDeleted=pyqtSignal(QString)
    hashValue = QCryptographicHash(QCryptographicHash.Md5)
    
    fileBuffer={}
    
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
            print "removing: ", i
            self.dirfiles.remove(i)
            self.unLoadFile(i)
            self.fileDeleted.emit(i)
  
        for i in newFiles:
            self.loadFile(i)
            self.fileModified.emit(i)
            self.dirfiles.append(i)
            self.watcher.addPath(self.directory + '/' + i)
            print "appending: ", i

    def processFileChanged(self, changed):
        fileName = QFileInfo(changed).fileName()
        if (self.fileExists(fileName)):
            
            print "Alert: File Changed :", changed
            fileName=QFileInfo(changed).fileName()
            self.loadFile(fileName)
            self.fileModified.emit(fileName)
                
    def displayChange(self, change):
        print "changed ", change

    def writeRecievedModifications(self,dataPacket):
        fileName=dataPacket.takeFirst()
        fileData=dataPacket.takeFirst().toUtf8()
        print "Alert: About to Write to file: ", fileName
        f = QFile(self.directory + '/'+ fileName)
        if(f.open(QIODevice.WriteOnly)):
            print "Alert :writing Recieved Data ", fileName, fileData
            f.write(QByteArray.fromBase64(fileData))
        else:
            print "Error: couldn't open file: ", f.fileName()

    def getFileContents(self,fileName):
        if(fileName not in self.fileBuffer):
            print "Exception: ", fileName, " not in fileBuffer -> loading.."
            self.loadFile(fileName)
            print "Alert: loaded ", fileName
        return self.fileBuffer[fileName][0]

    def removeDeletedFile(self,fileName):
        if(self.fileExists(fileName)):
               QFile.remove(self.directory+ '/' + fileName);

    def unLoadFile(self,fileName):
        if(fileName in self.fileBuffer):
            del self.fileBuffer[fileName]

    def loadFile(self,fileName):
        self.unLoadFile(fileName)

        f = QFile(self.directory + '/' + fileName)
        if(f.open(QIODevice.ReadOnly)):
            fileContents=QString(f.readAll().toBase64())
            self.hashValue.reset()
            self.hashValue.addData(fileContents)
            self.fileBuffer[fileName]=fileContents,QString(self.hashValue.result().toHex())
            #print "fileBuffer status: \n",self.fileBuffer
            #print "Alert: Loaded :", self.fileBuffer[fileName]
            return True
        else:
            print "Error: loadFile failed -> couldn't open  ", f.fileName()
            traceback.print_list(traceback.extract_stack())
            return False

    
    def getFileHash(self,fileName):
        if(fileName not in self.fileBuffer):
            self.loadFile(fileName)
        return self.fileBuffer[fileName][1]
        
    def fileExists(self, fileName):
        if (fileName in self.fileBuffer):
            return True
        elif (QFile.exists(self.directory + '/' + fileName)):
            return self.loadFile(fileName)
        else:
            return False

    def getPeerName(self):
        return self.directory
