#######################################################################################################
# CODE BELOW IS BEING DEVELOPED FOR PACKET LOSS
from socket import *
import sys
import random
import json
import threading
import time

def makeSegment(SYNbit, FINbit, seq, ACKbit, ack, DATAbit, dataAmount, data):
    d = {
        'SYNbit': SYNbit,
        'FINbit': FINbit,
        'seq': seq,
        'ACKbit': ACKbit,
        'ack': ack,
        'DATAbit': DATAbit,
        'dataAmount': dataAmount,
        'data': data
        }
    return d

# write the action to the log file
def writeToLog(segmentInfo, packetType, action):
    global log
    global initialTime
    log.write(action + " \t" + str("{0:.2f}".format(time.time() - initialTime)) + "\t" 
    + packetType + "\t" + str(segmentInfo.get('seq')) + "\t" 
    + str(segmentInfo.get('dataAmount')) + "\t" 
    + str(segmentInfo.get('ack')) + "\n")

# PL module 
# arguments: probability of dropping the packet, the information of the segment to be sent
def canSendDatagram(pdrop, segmentInfo, window):
    global log
    global initialTime
    global numSegmentsDropped
    # random function already initialised with seed in the main sender program
    chance = random.random()
    if (chance >= pdrop):
        # write to the log
        writeToLog(segmentInfo, "D", "snd")
        return True
    numSegmentsDropped = numSegmentsDropped + 1
    # write to the log
    writeToLog(segmentInfo, "D", "drop")
    return False

''' Returns the length of a file. '''
def FileLength(f):
    currentPosition = f.tell()
    f.seek(0, 2)               # move to end of file
    length = f.tell()          # get length of current position (i.e. the end of the file)
    f.seek(currentPosition, 0) # go back to where we started
    return length

''' Returns the number of bytes left to be read. '''
def BytesLeft(currentPosition, fileLength):
    return fileLength - currentPosition

def get_seq(packet):
    return packet.get('seq')

def getOldestPacket(window):
    window.sort(key = get_seq)
    if len(window) > 0:
        return window[0]
    return None

def retransmitPacket(window):
    global tLock
    global numRetransmissions
    global t
    # start a new timer for the retransmit
    if t is not None:
        t.cancel()
    t = threading.Timer(timeout, retransmitPacket, [window])
    t.daemon=True
    t.start()
    packet = getOldestPacket(window)
    if packet is None:
        t.cancel()
        return
    numRetransmissions += 1
    if packet and canSendDatagram(pdrop, packet, window):
        senderSocket.sendto(json.dumps(packet), receiverAddress)

def recvHandler():
    global t # timeout thread
    global tLock
    global senderSocket
    global window
    global currentACK # current ACK number received
    global lastExpectedAck # final ACK expected before sending a FIN
    global currentSeqNumber # current seq number of the sender
    global receiverSeq # current seq number of the receiver
    global duplicateCounter
    global numDuplicates
    while True: 
        datagram, receiverAddress = senderSocket.recvfrom(64 * 1024)
        # received an ack ... lock the thread so I can operate on the variables also shared with the sending thread
        tLock.acquire()
        t.cancel() # ACK received ... cancel the timer
        receivedAck = json.loads(datagram)
        # write to the log that an ACK has been received
        writeToLog(receivedAck, "A", "rcv")
        receivedAckNumber = receivedAck.get('ack')
        if (receivedAckNumber == currentACK):
            # received a duplicate ACK
            duplicateCounter += 1
            numDuplicates += 1
            if (duplicateCounter == 3):
                duplicateCounter = 0
                # fast transmit the oldest packet in the window
                retransmitPacket(window)
        else:
            # received a new ACK
            duplicateCounter = 0
            currentACK = receivedAckNumber
        toRemovePackets = []
        # receive an ack ... remove packets from the window where 
        # the sequence number is smaller (i.e. it has been acknowledged)
        for packet in window:
            # remove the packet from the window that have now been acknowledged
            if (packet.get('seq') < currentACK):
                toRemovePackets.append(packet)
        for packet in toRemovePackets:
            window.remove(packet)
        if len(window) > 0:
            # ensure t is not alive since a timer may have already been started for a fast retransmit
            # packets remaining in the window ... start a timer for the oldest packet
            t.cancel()
            t = threading.Timer(timeout, retransmitPacket, [window])
            t.daemon=True
            t.start()
        if (currentACK == lastExpectedAck):
            tLock.release()
            return
        tLock.release()


def sendHandler():
    global t # the timeout thread
    global tLock
    global pdrop
    global senderSocket
    global nextByte
    global maximumSize
    global windowSize
    global window
    global timeout
    global fileBuffer
    global fileLength
    global currentSeqNumber # current seq number of the sender
    global currentACK # currentACK received
    global receiverSeq # seq number of the receiver
    while True:
        tLock.acquire() # take control of the lock to modify variables shared between the threads
        for i in range(windowSize):
            if (len(window) == windowSize):
                # the window is full, cannot add more packets to the window ... break from the loop
                break
            if BytesLeft(nextByte, fileLength) < maximumSize:
                # read the remaining contents of the file
                maximumSize = BytesLeft(nextByte, fileLength)
            data = fileBuffer[nextByte: nextByte + maximumSize]
            nextByte += maximumSize          
            # create the PTP segment
            d = makeSegment(0, 0, currentSeqNumber, 1, receiverSeq, 1, maximumSize, data.decode("utf-8"))
            # increment sequence number by the payload of the packet
            currentSeqNumber += maximumSize 
            # add the new packet to the window
            window.append(d)
            if (len(window) == 1):
                # first segment in an empty ... start a timer for the first packet we populate the window with
                t = threading.Timer(timeout, retransmitPacket, [window])
                t.daemon=True
                t.start()
            # send packet to the PL module
            if canSendDatagram(pdrop, d, window):
                #PL module does NOT drop the packet ... it can be sent
                senderSocket.sendto(json.dumps(d), receiverAddress)
                # update sequence number after sending the packet
            
            if  BytesLeft(nextByte, fileLength) == 0:
                # if there are no bytes left to read from the file ... stop the thread
                # since we do not need to transmit anymore packets (retransmissions handled by threading timer)
                tLock.release()
                return
        # release the lock once we have populated the entire window (until its appropiate window size)
        print("segments sent")
        tLock.release() 
            
# Actual sender program
if (len(sys.argv) != 9):
    print("Usage: <receiver_host_ip> <receiver_port> <FileToSend.txt> <MWS> <MSS> <timeout> <pdrop> <seed>")
    sys.exit(1)
# convert the provided arguments into local variables
receiverIP = sys.argv[1]
receiverPort = int(sys.argv[2])
receiverAddress = (receiverIP, receiverPort)
fileToSend = sys.argv[3]
maxmimumWindowSize = int(sys.argv[4])
maximumSize = int(sys.argv[5])
timeout = float(sys.argv[6]) / 1000.0 # convert into seconds for the threading timer
pdrop = float(sys.argv[7])
seed = int(sys.argv[8])
# the random function used in function canSendDatagram
random.seed(seed)
# to store packets the sender has sent
window = []
windowSize = maxmimumWindowSize / maximumSize
# for the log 
numSegmentsDropped = 0
numRetransmissions = 0
numDuplicates = 0
# keep a record of the receiver's sequence number
duplicateCounter = 0
currentACK = 0
receivedAckNumber = 0
receiverSeq = 0
# open the log file
log = open("Sender_log.txt", "w")
# exit()
senderSocket = socket(AF_INET, SOCK_DGRAM)
##### 3-way handshake
initialTime = time.time()
initialSeqNumber = 1000
currentSeqNumber = initialSeqNumber
# send the syn
d = makeSegment(1, 0, currentSeqNumber, 0, currentACK, 0, 0, "")
writeToLog(d, "S", "snd")
syn = json.dumps(d)
senderSocket.sendto(syn, receiverAddress)
# receive the syn+ack
datagram, receiverAddress = senderSocket.recvfrom(64 * 1024)
synAck = json.loads(datagram)
writeToLog(synAck, "SA", "rcv")
currentSeqNumber += 1
receivedAckNumber = synAck.get('ack') + 1
receiverSeq = synAck.get('seq') + 1
if synAck.get('ACKbit') and (synAck.get('ack') == currentSeqNumber) and synAck.get('SYNbit'):
    d = makeSegment(0, 0, currentSeqNumber, 1, receiverSeq, 0, 0, "")
    writeToLog(d, "A", "snd")
    finalAck = json.dumps(d)
    # send the final ack
    senderSocket.sendto(finalAck, receiverAddress)

##### Connection has been established: Start sending the datagrams
# open the file to send
f = open(fileToSend, "rb")
fileLength = FileLength(f)
fileBuffer = f.read(fileLength)
# used for the log file
numTransmissions = fileLength / maximumSize
if fileLength % maximumSize != 0:
    numTransmissions += 1
lastExpectedAck = currentSeqNumber + fileLength
nextByte = 0

t = None
tLock = threading.Lock()
# Start the sending thread
print("Started")
sendThread=threading.Thread(name="SendHandler",target=sendHandler)
sendThread.daemon=True
sendThread.start()
recvThread=threading.Thread(name="RecvHandler", target=recvHandler)
recvThread.daemon=True
# the receiving thread runs after the sending thread has started
if sendThread.is_alive():
    recvThread.start()

#this is the main thread
sendThread.join()
recvThread.join()


# Once the threads are finished, end the connection
##### Peform 4-way termination
f.close()
d = makeSegment(0, 1, currentSeqNumber, 0, receiverSeq, 0, 0, "")
writeToLog(d, "F", "snd")
# send FIN: initiate termination
senderSocket.sendto(json.dumps(d), receiverAddress)
datagram, receiverAddress = senderSocket.recvfrom(64 * 1024)
finACK = json.loads(datagram)
writeToLog(finACK, "FA", "rcv")
if finACK.get('FINbit') and finACK.get('ACKbit') and (finACK.get('ack') == currentSeqNumber + 1):
    currentSeqNumber += 1
    # finACK has been received, send a final ack then close the socket
    d = makeSegment(0, 0, currentSeqNumber, 1, receiverSeq + 1, 0, 0, "")
    writeToLog(d, "A", "snd")
    senderSocket.sendto(json.dumps(d), receiverAddress)

# print final stats to the log file
log.write("\nAmount of original data: " + str(fileLength))
log.write("\nNumber of data segments (excluding retransmissions): " + str(numTransmissions))
log.write("\nNumber of packets dropped: " + str(numSegmentsDropped))
log.write("\nNumber of retransmitted packets: " + str(numRetransmissions))
log.write("\nNumber of duplicate acknowledgements: " + str(numDuplicates))
log.close()
senderSocket.close()
print("ended")







