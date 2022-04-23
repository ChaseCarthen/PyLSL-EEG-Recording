"""Example program to demonstrate how to read a multi-channel time-series
from LSL in a chunk-by-chunk manner (which is more efficient)."""

import datetime
from pylsl import StreamInlet, resolve_stream
import xmltodict
import json
from flask import Flask
import threading
from time import sleep
from multiprocessing import Queue as queue
from os.path import splitext
import time
import sys
import signal
def handler(signal, frame):
  global recording 
  recording = False
  print('CTRL-C pressed! haha')
  sleep(2)
  sys.exit(0)
signal.signal(signal.SIGINT, handler)
#signal.pause()



app = Flask(__name__)

recording = False
currentFilename = ''

events = queue()
thread = None


def recordFile(filename):
    #writeThread = threading.Thread(target=handleWriting, args=(filename,))
    #writeThread.start()

    print('saving to ' + filename)
    global recording
    

    # first resolve an EEG stream on the lab network
    streams = resolve_stream()#'type', 'EEG')
    
    # create a new inlet to read from the stream
    #print(len(streams))
    inlets = []
    channelNames = []
    
    threads = []

    for stream in streams:
        threads.append(threading.Thread(target=writeStream, args=(splitext(filename)[0] + stream.name() + '.csv', stream)))
        #inlet = StreamInlet(stream)
        #inlets.append(inlet)
        #convertedDictionary = xmltodict.parse(inlet.info().as_xml())
        #names = [channel['label'] for channel in convertedDictionary['info']['desc']['channels']['channel'] ] 
        #channelNames += names
    threads.append(threading.Thread(target=writeEvents, args=(splitext(filename)[0] + 'Events' + '.csv',)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
 

def writeStream(filename, stream):
    global recording

    inlet = StreamInlet(stream)
    fileHandle = open(filename,'w')

    convertedDictionary = xmltodict.parse(inlet.info().as_xml())
    names = [channel['label'] for channel in convertedDictionary['info']['desc']['channels']['channel'] ] + ['Written Timestamp']
    fileHandle.write(str(names)[1:-1].replace(' ','')+'\n')

    while recording:
        past = datetime.datetime.now()
        line = ''
        sample, timestamps = inlet.pull_sample()
        if timestamps:
            line += str(sample)[1:-1].replace(' ','')
        line += ',' + str(time.time())
        line += '\n'
        fileHandle.write(line)
        #print((datetime.datetime.now() - past).total_seconds())

def writeEvents(eventFilename):
    print('here')
    eventFileHandle = open(eventFilename, 'w')
    eventFileHandle.write('timestamp,event_id\n')
    while recording or not events.empty():
        if not events.empty():
            eventFileHandle.write(str(time.time()) + ',' + str(events.get())+'\n')


@app.route('/start/<filename>')
def startRecording(filename):
    global thread
    global recording
    if recording:
        return 'already recording', 400

    recording = True
    currentFilename = filename
    thread = threading.Thread(target=recordFile, args=(currentFilename,))
    thread.start()
    return 'Started Recording'

@app.route('/stop')
def stopRecording():
    global recording
    recording = False
    return 'Stopped Recording'

@app.route('/addevent/<id>')
def event(id):
    events.put(id)
    return 'Okay',200

if __name__ == '__main__':
    app.run()
    #recording = True
    #recordFile('test.csv')