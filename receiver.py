# CODE BELOW IS WHAT IS CURRENTLY DEVELOPED FOR PACKET LOSS
import sys
from socket import *
import json
import time

def writeToLog(segmentInfo, packetType, action):
    global log
    global initialTime
    log.write(action + " \t" + str("{0:.2f}".format(time.time() - initialTime)) + "\t" 
    + packetType + "\t" + str(segmentInfo.get('seq')) + "\t" 
    + str(segmentInfo.get('dataAmount')) + "\t" 
    + str(segmentInfo.get('ack')) + "\n")

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

def get_seq(packet):
    return packet.get('seq')

def FileLength(f):
    currentPosition = f.tell()
    f.seek(0, 2)               # move to end of file
    length = f.tell()          # get length of current position (i.e. the end of the file)
    f.seek(currentPosition, 0) # go back to where we started
    return length

# Actual receiver program
if (len(sys.argv) != 3):
    print("Usage: <receiver_port> <FileReceived.txt>")
    sys.exit(1)
# convert the provided arguments into local variables
receiverPort = int(sys.argv[1])
fileReceived = sys.argv[2]
seqNumber = 2000
receiverSocket = socket(AF_INET, SOCK_DGRAM)
receiverAddress = ('127.0.0.1', receiverPort)
receiverSocket.bind(receiverAddress)

# open the receiver log
log = open("Receiver_log.txt", "w")
initialTime = time.time()

# 3-way handshake
# receive the syn
datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
syn = json.loads(datagram)
currentACK = syn.get('seq') + 1
if syn.get('SYNbit'):
    writeToLog(syn, "S", "rcv")
    d = makeSegment(1, 0, seqNumber, 1, currentACK, 0, 0, "")
    writeToLog(d, "SA", "snd")
    synAck = json.dumps(d)
    # return syn+ack
    receiverSocket.sendto(synAck, senderAddress)
    # receive the final ack
    datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
    finalAck = json.loads(datagram)
    writeToLog(finalAck, "A", "rcv")
    seqNumber += 1
    if finalAck.get('ACKbit') != 1 or (finalAck.get('ack') != seqNumber):
        # final ack does not have a flipped ACK bit or does not have the expected ackNumber
        receiverSocket.close()
        sys.exit(1)
else:
    # syn not received...
    receiverSocket.close()
    sys.exit(1)

# open the file
f = open(fileReceived, "wb")
buffer = []

originalSegmentCounter = 0
duplicateSegmentCounter = 0
mostRecentAck = currentACK
# while there is still data to be received
print("Started")
while True:
    datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
    segment = json.loads(datagram)
    # write to the log the segment it receives
    if segment.get('FINbit'):
        writeToLog(segment, "F", "rcv")
    else:
        writeToLog(segment, "D", "rcv")
    if currentACK == segment.get('seq') and segment.get('DATAbit'):
        originalSegmentCounter += 1
        # next expected segment has been received, write its contents to the file
        f.write(segment.get('data').encode("utf-8"))
        # remove the segment from the buffer, NOT NEEDED BECAUSE IT HASNT BEEN RECEIVED???
        # buffer.remove(segment)
        # update current ACK with the payload of this segment
        currentACK += segment.get('dataAmount')
        # sort the buffer in order so we can iterate through it
        buffer.sort(key = get_seq)
        toRemovePackets = []
        for packet in buffer:
            # go through the buffer and check if the next expected segment has already been received
            # next expected packet has sequence number of the current ACK
            if packet.get('seq') == currentACK:
                # remove this packet later
                toRemovePackets.append(packet)
                # update the currentACK number with the payload of this segment
                currentACK = packet.get('seq') + packet.get('dataAmount')
                # write the data of this segment to the file
                f.write(packet.get('data').encode("utf-8"))
        for packet in toRemovePackets:
            # remove packets that have been acknowledged
            buffer.remove(packet)
    elif segment.get('seq') >= mostRecentAck  and segment.get('DATAbit'):
        # a new segment has been acquired (but it is not the segment we are currently expecting)
        originalSegmentCounter += 1
        mostRecentAck += segment.get('dataAmount')
        buffer.append(segment)
    elif segment.get('FINbit') == 0:
        # segment received is a FIN ... not part of the duplicate counter
        duplicateSegmentCounter += 1
    # create the ACK to be sent back
    d = makeSegment(0, 0, seqNumber, 1, currentACK, 0, 0, "")
    prevAckPacket = d
    # a FIN segment has been received ... start initiating termination
    if (segment.get('FINbit')):
        # return a finACK
        d['FINbit'] = 1
        d['ack'] += 1
        # write to the log the ACK that the receiver returns
        writeToLog(d, "FA", "snd")
        receiverSocket.sendto(json.dumps(d), senderAddress)
        break
    # write to the log the ACK that the receiver returns
    writeToLog(d, "A", "snd")
    # return ACK for the segment
    receiverSocket.sendto(json.dumps(d), senderAddress)
    print("ACK sent")

f.close()
# get the length of the file we wrote to
f = open(fileReceived, "rb")
fileLength = FileLength(f)
f.close()
datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
# write to the log the final ACK received
finalACK = json.loads(datagram)
writeToLog(finalACK, "A", "rcv")
if finalACK.get('ACKbit') and finalACK.get('ack') == (seqNumber + 1):
    # received the final ACK ... add remaining things to the log file
    log.write("\nAmount of original data received (in bytes): " + str(fileLength))
    log.write("\nNumber of original data segments received: " + str(originalSegmentCounter))
    log.write("\nNumber of duplicate segments received: " + str(duplicateSegmentCounter))
    log.close()
    receiverSocket.close()
    print("ended")

