# # 1. Connection setup : DONE
# # 2. Data Transmission (repeat until end of file)
# #   a. Receive PTP segment : DONE
# #   b. Send ACK segment : DONE
# #   c. Buffer data or write data into file
# # 3. Connection teardown : DONE

# import sys
# from socket import *
# import json
# import time

# # Actual receiver program
# if (len(sys.argv) != 3):
#     print("Usage: <receiver_port> <FileReceived.txt>")
#     sys.exit(1)
# # convert the provided arguments into local variables
# receiverPort = int(sys.argv[1])
# fileReceived = sys.argv[2]
# seqNumber = 2000
# receiverSocket = socket(AF_INET, SOCK_DGRAM)
# receiverAddress = ('127.0.0.1', receiverPort)
# receiverSocket.bind(receiverAddress)

# # 3-way handshake
# # receive the syn
# datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
# syn = json.loads(datagram)
# currentACK = syn.get('seq') + 1
# if syn.get('SYNbit'):
#     print("SYN received.")
#     d = {
#         'SYNbit': 1,
#         'FINbit': 0,
#         'seq': seqNumber,
#         'ACKbit': 1,
#         'ack': currentACK,
#         'DATAbit': 0,
#         'dataAmount': 0,
#         }
#     synAck = json.dumps(d)
#     # return syn+ack
#     print("ACK prepared")
#     receiverSocket.sendto(synAck, senderAddress)
#     print("synACK sent")
#     # receive the final ack
#     datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
#     finalAck = json.loads(datagram)
#     seqNumber += 1
#     if finalAck.get('ACKbit') != 1 or (finalAck.get('ack') != seqNumber):
#         # final ack does not have a flipped ACK bit or does not have the expected ackNumber
#         print("Here")
#         print(finalAck)
#         receiverSocket.close()
#         sys.exit(1)
# else:
#     # syn not received...
#     print("syn not received")
#     receiverSocket.close()
#     sys.exit(1)

# print(currentACK)
# print("Final ack received")
# print('The server is ready to receive')
# # open the file
# f = open(fileReceived, "wb")
# buffer = []

# mostRecentAck = currentACK
# # while there is still data to be received
# while True:
#     datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
#     segment = json.loads(datagram)
#     print("Segment received: ")
#     print(segment)
#     # add received segment to the buffer
#     buffer.append(segment)
#     if segment.get('seq') >= mostRecentAck:
#         mostRecentAck += segment.get('dataAmount')
#     if currentACK == segment.get('seq'):
#         # new currentACK to be delivered back
#         currentACK += segment.get('dataAmount')
#         print("The current ACK number")
#         print(currentACK)
#         # current segment was the next expected segment
#         for packet in buffer:
#             # go through the buffer and check if the next expected segment has already been received
#             if packet.get('seq') >= currentACK:
#                 # Since segments are appended in order ... get the currentACK of the next sequence number of packet in buffer
#                 currentACK = packet.get('seq') + packet.get('dataAmount')
#                 break
#         # currentACK = mostRecentAck
#         f.write(segment.get('data'))
#     #     if (segment.get('DATAbit')):
#     #         # write the data to the received file
#     #         f.write(segment.get('data'))
#     #     for packet in buffer:
#     #         # check the packets in the buffer
#     #         if currentACK == packet.get('seq'):
#     #             currentACK += packet.get('dataAmount')
#     #             # if a packet buffered is the next expected packet, write its data to the file
#     #             f.write(segment.get('data'))
#     # elif currentACK < segment.get('seq'):
#     #     # the segment just received has a bigger sequence number ... therefore packet has not been acknowledged
#     #     buffer.append(segment)
#     # create the ACK to be sent back to the sender
#     d = {
#         'SYNbit': 0,
#         'FINbit': 0,
#         'seq': seqNumber,
#         'ACKbit': 1,
#         'ack': currentACK,
#         'DATAbit': 0,
#         'dataAmount': 0,
#         }
#     print("ACK sent off: ")
#     print(d)
#     # a FIN segment has been received ... start initiating termination
#     if (segment.get('FINbit')):
#         # return a finACK
#         d['FINbit'] = 1
#         d['ack'] += 1
#         receiverSocket.sendto(json.dumps(d), senderAddress)
#         break
#     # return ACK for the segment
#     receiverSocket.sendto(json.dumps(d), senderAddress)

# f.close()
# datagram, senderAddress = receiverSocket.recvfrom(64 * 1024)
# finalACK = json.loads(datagram)
# if finalACK.get('ACKbit') and finalACK.get('ack') == (seqNumber + 1):
#     # received the final ACK ... close the socket
#     print(finalACK)
#     print("Ending.....")
#     receiverSocket.close()
# CODE ABOVE WORKS FOR SLIDING WINDOW (RECEIVER)

# CODE BELOW WORKS FOR SLIDING WINDOW (SENDER)
# from socket import *
# import sys
# import random
# import json
# import threading
# import time

# def makeSegment(SYNbit, FINbit, seq, ACKbit, ack, DATAbit, dataAmount, data):
#     d = {
#         'SYNbit': SYNbit,
#         'FINbit': FINbit,
#         'seq': seq,
#         'ACKbit': ACKbit,
#         'ack': ack,
#         'DATAbit': DATAbit,
#         'dataAmount': dataAmount,
#         'data': data
#         }
#     return d

# # write the action to the log file
# def writeToLog(segmentInfo, packetType, action):
#     global log
#     global initialTime
#     log.write(action + "\t" + str("{0:.2f}".format(time.time() - initialTime)) + "\t" 
#     + packetType + "\t" + str(segmentInfo.get('seq')) + "\t" 
#     + str(segmentInfo.get('dataAmount')) + "\t" 
#     + str(segmentInfo.get('ack')) + "\n")

# # PL module 
# # arguments: probability of dropping the packet, the information of the segment to be sent
# def canSendDatagram(pdrop, segmentInfo):
#     global log
#     global initialTime
#     global numSegmentsDropped
#     # random function already initialised with seed in the main sender program
#     chance = random.random()
#     if (chance > pdrop):
#         # write to the log
#         writeToLog(segmentInfo, "D", "snd")
#         return True
#     numSegmentsDropped = numSegmentsDropped + 1
#     # write to the log
#     writeToLog(segmentInfo, "D", "drop")
#     return False

# ''' Returns the length of a file. '''
# def FileLength(f):
#     currentPosition = f.tell()
#     f.seek(0, 2)               # move to end of file
#     length = f.tell()          # get length of current position (i.e. the end of the file)
#     f.seek(currentPosition, 0) # go back to where we started
#     return length

# ''' Returns the number of bytes left to be read. '''
# def BytesLeft(currentPosition, fileLength):
#     return fileLength - currentPosition

# # 1. Connection setup : DONE
# # 2. Data Transmission (repeat until end of file)
# #     a. Read file 
# #     b. Create PTP segment
# #     c. Start Timer if required (retransmit oldest unacknowledged segment on expiry)
# #     d. Send PTP segment to PL module
# #     e. If PTP segment is not dropped, transmit to Receiver
# #     f. Process ACK if received
# # 3. Connection teardown : DONE

# def recvHandler():
#     global SYNnum
#     global DATAnum
#     global FINnum
#     global tLock
#     global senderSocket
#     global window
#     global currentACK # current ACK number received
#     global lastExpectedAck # final ACK expected before sending a FIN
#     global sendBase # the smallest unacknlowdged segment
#     global currentSeqNumber # current seq number of the sender
#     global receiverSeq # current seq number of the receiver
#     print('Ready to receive ACKs')
#     time.sleep(0.001) # let the sending thread run first
#     while True: 
#         tLock.acquire()
#         if (FINnum):
#             return
#         if DATAnum:
#             datagram, receiverAddress = senderSocket.recvfrom(64 * 1024)
#             receivedAck = json.loads(datagram)
#             print("Ack from receiver is: ")
#             print(receivedAck)
#             writeToLog(receivedAck, "A", "rcv")
#             receivedAckNumber = receivedAck.get('ack')
#             toRemovePackets = []
#             # receive an ack ... remove packets from the window where 
#             # the sequence number is smaller (i.e. it has been acknowledged)
#             for packet in window:
#                 # remove the packet from the window
#                 if (packet.get('seq') < receivedAck):
#                     window.remove(packet)
#                     break
#             sendBase = receivedAckNumber - initialSeqNumber
#             if (receivedAckNumber == lastExpectedAck):
#                 tLock.release()
#                 return
#         tLock.release()
#         time.sleep(0.001) # let the sending thread take control of lock


# def sendHandler():
#     global DATAnum
#     global FINnum
#     global tLock
#     global pdrop
#     global senderSocket
#     global sendBase
#     global nextByte
#     global maximumSize
#     global windowSize
#     global window
#     global timeout
#     global fileBuffer
#     global fileLength
#     global currentSeqNumber # current seq number of the sender
#     global currentACK # currentACK received
#     global receiverSeq # seq number of the receiver
#     global lastExpectedAck
#     print("HERE IN SENDING THREAD")
#     while True:
#         tLock.acquire() # take control of the lock
#         if  BytesLeft(nextByte, fileLength) == 0:
#             tLock.release()
#             return
#         if DATAnum:
#             print("Sending the data")
#             for i in range(windowSize):
#                 print("Adding packets to window")
#                 if (len(window) >= windowSize):
#                     # the window is full, cannot currently send more packets
#                     break
#                 if BytesLeft(nextByte, fileLength) < maximumSize:
#                     maximumSize = BytesLeft(nextByte, fileLength)
#                 data = fileBuffer[nextByte: nextByte + maximumSize]
#                 nextByte += maximumSize                              
#                 # create the PTP segment
#                 d = makeSegment(0, 0, currentSeqNumber, 1, currentACK, 1, maximumSize, data.decode('utf-8'))
#                 # send to the PL module
#                 window.append(d)
#                 print("Appended to the window")
#                 if canSendDatagram(pdrop, d):
#                     print("Sending it off")
#                     #PL module does NOT drop the packet ... it can be sent
#                     senderSocket.sendto(json.dumps(d), receiverAddress)
#                     # update sequence number after sending the packet
#                     currentSeqNumber += maximumSize
#                 if  BytesLeft(nextByte, fileLength) == 0:
#                     break
#             print("Packets that have been sent")
#             print(window)
#         tLock.release() # let the receiving thread take control of the lock
#         time.sleep(0.001)
            

# # Actual sender program
# if (len(sys.argv) != 9):
#     print("Usage: <receiver_host_ip> <receiver_port> <FileToSend.txt> <MWS> <MSS> <timeout> <pdrop> <seed>")
#     sys.exit(1)
# # convert the provided arguments into local variables
# receiverIP = sys.argv[1]
# receiverPort = int(sys.argv[2])
# receiverAddress = (receiverIP, receiverPort)
# fileToSend = sys.argv[3]
# windowSize = int(sys.argv[4])
# maximumSize = int(sys.argv[5])
# timeout = int(sys.argv[6])
# pdrop = float(sys.argv[7])
# seed = int(sys.argv[8])
# # the random function used in function canSendDatagram
# random.seed(seed)
# # to store packets the sender has sent
# window = []
# # for the log 
# numSegments = 0
# numSegmentsDropped = 0
# numRetransmissions = 0
# numDuplicates = 0
# # keep a record of the receiver's sequence number
# currentACK = 0
# receivedAckNumber = 0
# nextExpectedAck = 0
# receiverSeq = 0
# # open the log file
# log = open("Sender_log.txt", "w")

# senderSocket = socket(AF_INET, SOCK_DGRAM)
# ##### 3-way handshake
# initialTime = time.time()
# initialSeqNumber = 1000
# currentSeqNumber = initialSeqNumber
# # send the syn
# d = makeSegment(1, 0, currentSeqNumber, 0, currentACK, 0, 0, "")
# writeToLog(d, "S", "snd")
# syn = json.dumps(d)
# senderSocket.sendto(syn, receiverAddress)
# # receive the syn+ack
# datagram, receiverAddress = senderSocket.recvfrom(64 * 1024)
# synAck = json.loads(datagram)
# writeToLog(synAck, "SA", "rcv")
# currentSeqNumber += 1
# receivedAckNumber = synAck.get('ack')
# if synAck.get('ACKbit') and (synAck.get('ack') == currentSeqNumber) and synAck.get('SYNbit'):
#     currentACK = synAck.get('seq') + 1
#     d = makeSegment(0, 0, currentSeqNumber, 1, currentACK, 0, 0, "")
#     writeToLog(d, "A", "snd")
#     finalAck = json.dumps(d)
#     # send the final ack
#     senderSocket.sendto(finalAck, receiverAddress)
# nextExpectedAck = receivedAckNumber

# ##### Connection has been established: Start sending the datagrams
# DATAnum = 1
# FINnum = 0
# # open the file to send
# f = open(fileToSend, "rb")
# fileLength = FileLength(f)
# fileBuffer = f.read(fileLength)
# # used for the log file
# lastExpectedAck = currentSeqNumber + fileLength
# print("Last expected Ack number is: " + str(lastExpectedAck))
# sendBase = 0
# nextByte = 0

# tLock = threading.Condition()
# # Start the sending thread
# sendThread=threading.Thread(name="SendHandler",target=sendHandler)
# sendThread.daemon=True
# sendThread.start()
# # Start the receiving thread
# recvThread=threading.Thread(name="RecvHandler", target=recvHandler)
# recvThread.daemon=True
# recvThread.start()


# #this is the main thread
# sendThread.join()
# print("After sending thread")
# recvThread.join()
# print("After receiving thread")


# # Once the threads are finished, end the connection
# ##### Peform 4-way termination
# f.close()
# d = makeSegment(0, 1, currentSeqNumber, 0, currentACK, 0, 0, "")
# writeToLog(d, "F", "snd")
# # send FIN: initiate termination
# senderSocket.sendto(json.dumps(d), receiverAddress)
# datagram, receiverAddress = senderSocket.recvfrom(64 * 1024)
# finACK = json.loads(datagram)
# writeToLog(finACK, "FA", "rcv")
# if finACK.get('FINbit') and finACK.get('ACKbit') and (finACK.get('ack') == currentSeqNumber + 1):
#     currentSeqNumber += 1
#     # finACK has been received, send a final ack then close the socket
#     d = makeSegment(0, 0, currentSeqNumber, 1, currentACK + 1, 0, 0, "")
#     writeToLog(d, "A", "snd")
#     senderSocket.sendto(json.dumps(d), receiverAddress)
# log.close()
# senderSocket.close()



### CODE ABOVE WORKS FOR SLIDING WINDOW (SENDER)