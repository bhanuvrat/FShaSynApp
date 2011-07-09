from PyQt4.Qt import *
import traceback
class ClientConnection (QObject):
    
    dataRecieved=pyqtSignal(QStringList)
    disconnected=pyqtSignal()
    messageFileChangedRecieved=pyqtSignal(QStringList)
    messageFileDeletedRecieved=pyqtSignal(QStringList)
    requestFileChangedRecieved=pyqtSignal(QStringList)
    dataFileChangedRecieved=pyqtSignal(QStringList)
    
    messageDirectoryCreatedRecieved=pyqtSignal(QStringList)
    messageDirectoryDeletedRecieved=pyqtSignal(QStringList)

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

        elif (header == QString("m.DIR.CREATED")):
            self.messageDirectoryCreatedRecieved.emit(dataPacket)
        
        elif (header == QString("m.DIR.DELETED")):
            self.messageDirectoryDeletedRecieved.emit(dataPacket)
              
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
    directoryCreated=pyqtSignal(QString)
    directoryDeleted=pyqtSignal(QString)

    hashValue = QCryptographicHash(QCryptographicHash.Md5)
    
    fileBuffer={}
    
    def cacheRecursively(self, directory):
        """
        Recursively caches the whole diretory tree.
        """
        dirListing = list(QDir(directory).entryInfoList())
        dirListing.pop(0)
        dirListing.pop(0)
        for i in dirListing:
            self.watcher.addPath(i.absoluteFilePath())
            #self.watcher.addPath(self.directory.relativeFilePath(i.absoluteFilePath()))
            if (i.isDir()):
                self.cacheRecursively(i.absoluteFilePath())

    def uncacheRecursively(self, directory):
        """
        recursively removes the files and sub-directories of the passed path from watcher
        """
        dirListing = list(QDir(directory).entryInfoList())
        dirListing.pop(0)
        dirListing.pop(0)
        for i in dirListing:
            self.watcher.removePath(i.absoluteFilePath())
            if (i.isDir()):
                self.uncacheRecursively(i.absolutePath())
        
    def removeRecursively(self, directory):
        """
        Recursively deletes the files and sub-directories of passed directory
        """
        dirListing = list(QDir(directory).entryInfoList())
        dirListing.pop(0)
        dirListing.pop(0)
        for i in dirListing:
            self.watcher.removePath(i.absoluteFilePath())
            if (i.isFile()):
                self.unLoadFile(self.directory.relativeFilePath(i.absoluteFilePath()))
                self.directory.remove(i.absoluteFilePath())
            if (i.isDir()):
                self.removeRecursively(i.absoluteFilePath())
        
        self.directory.rmdir(QDir(directory).absolutePath())

    def relativeDirectoryPath(self, path):
        return path.split(self.directory.absolutePath() + '/',QString.SkipEmptyParts).takeFirst()

    def __init__(self, directory):
        QObject.__init__(self)
        self.directory= QDir(directory)
        self.watcher=QFileSystemWatcher()
        self.watcher.addPath(self.directory.absolutePath())
        self.cacheRecursively(self.directory.absolutePath())

        """Connections"""
        self.watcher.directoryChanged.connect(self.processDirChanged)
        self.watcher.fileChanged.connect(self.processFileChanged)
        """printing the initial watch queue"""
        for i in list(self.watcher.directories()):
            print i
        for i in list(self.watcher.files()):
            print i

    def processDirChanged(self, changed):
        changedDir = QDir(changed)
        print "Monitored directory changed: ", changed
        if(changedDir.exists() == False):
            """If the directory has been deleted then emit and return, no fooling around"""
            #self.uncacheRecursively(changed)
            self.directoryDeleted.emit(self.relativeDirectoryPath(changed))

            self.watcher.removePath(changed)
            if(changed in self.watcher.directories()): 
                print"removePath failed"

            print "Emitted Directory Deleted: ", self.relativeDirectoryPath(changed)
            return

        newlist = set()
        eil = changedDir.entryInfoList()
        eil.pop(0)
        eil.pop(0)
        for i in eil:
            newlist.add(i.absoluteFilePath())

        oldlist = set(self.watcher.files()).union(set(self.watcher.directories()))
        newFiles = newlist - oldlist

        for i in newFiles:
            self.watcher.addPath(i)
            print "Appending to watch list: ", i
            if(QFileInfo(i).isFile()):
                self.loadFile(self.directory.relativeFilePath(i))
                self.fileModified.emit(self.directory.relativeFilePath(i))
            elif(QFileInfo(i).isDir()):
                
                self.directoryCreated.emit(self.relativeDirectoryPath(i))
                print "Emitted Directory Created: ", self.relativeDirectoryPath(i)
                pass

    def processFileChanged(self, changed):
        """changed is a QString with Absolute File Path"""
        #changedFile = QFileInfo(changed)
        relFilePath=self.directory.relativeFilePath(changed)
        if (self.fileExists(relFilePath)):
            print "Alert: modified :", relFilePath
            #fileName=QFileInfo(changed).fileName()
            self.loadFile(relFilePath)
            self.fileModified.emit(relFilePath)
        else:
            """if the file is not there, it means it is deleted - hence the signal"""
            print "Alert: Deleted", relFilePath
            self.fileDeleted.emit(relFilePath)            

    def displayChange(self, change):
        print "changed ", change

    def writeRecievedModifications(self,dataPacket):
        relativeFilePath=dataPacket.takeFirst()
        fileData=dataPacket.takeFirst().toUtf8()
        print "Alert: About to Write to file: ", relativeFilePath
        f = QFile(self.directory.absolutePath() + '/' + relativeFilePath)
        if(f.open(QIODevice.WriteOnly)):
            print "Alert :writing Recieved Data ",relativeFilePath, fileData
            f.write(QByteArray.fromBase64(fileData))
        else:
            print "Error: couldn't open file: ", f.fileName()

    def getFileContents(self,relFilePath):
        if(relFilePath not in self.fileBuffer):
            print "Exception: ", relFilePath, " not in fileBuffer -> loading.."
            #error checking required here.
            self.loadFile(relFilePath)            
            print "Alert: loaded ", relFilePath
        return self.fileBuffer[relFilePath][0]

    def removeDeletedFile(self,relativeFilePath):
        print "About to delete file: ", relativeFilePath
        absoluteFilePath = self.directory.absolutePath() + '/'+ relativeFilePath
        if(self.fileExists(relativeFilePath)):
            self.unLoadFile(relativeFilePath)
            QFile.remove(absoluteFilePath);

    def unLoadFile(self,relFilePath):
        """
        assumes the parameter to be relative file path,
        indexing in fileBuffer is based on relative file path.
        """
        if(relFilePath in self.fileBuffer):
            del self.fileBuffer[relFilePath]

    def loadFile(self,relFilePath):
        self.unLoadFile(relFilePath)

        f = QFile(self.directory.absolutePath() + '/' + relFilePath)
        if(f.open(QIODevice.ReadOnly)):
            fileContents=QString(f.readAll().toBase64())
            self.hashValue.reset()
            self.hashValue.addData(fileContents)
            self.fileBuffer[relFilePath]=fileContents,QString(self.hashValue.result().toHex())
            #print "fileBuffer status: \n",self.fileBuffer
            #print "Alert: Loaded :", self.fileBuffer[fileName]
            return True
        else:
            print "Error: loadFile failed -> couldn't open: ", f.fileName()
            traceback.print_list(traceback.extract_stack())
            return False

    def getFileHash(self,relFilePath):
        if(relFilePath not in self.fileBuffer):
            self.loadFile(relFilePath)
        return self.fileBuffer[relFilePath][1]
        
    def fileExists(self, relFilePath):
        exists = QFile.exists(self.directory.absolutePath() + '/' + relFilePath)
        if (exists and  relFilePath in self.fileBuffer):
            return True
        elif (exists):
            return self.loadFile(relFilePath)
        else:
            return False

    def createDirectory(self, dataPacket):
        self.directory.mkdir(dataPacket.takeFirst())

    def removeDirectory(self,dataPacket):        
        dirToRemove=QDir(self.directory.absolutePath() + '/' + dataPacket.takeFirst())
        print "dirToRemove: ", dirToRemove.absolutePath()

        if(dirToRemove.exists()):
            print "Deleting directory "
            self.removeRecursively(dirToRemove)
            self.directory.rmdir(dirToRemove.absolutePath())
        else :
            print "directory did not exist"
        
    def getPeerName(self):
        return self.directory.absolutePath()
