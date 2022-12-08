'''
Name: Recording 
Author: Chase Carthen
Description: A webservice that records any lsl streams coming. It is intended to be used for emotivs eeg headsets.
    This webservice will also allow the user to add "events" that could represent different phases of eeg recording.
    These events can be tracked against the lsl streams by mapping the time recorded in the streams and time in the events csv.
How to Use:
    first put a get request to: localhost:5000/start/<yourfilename>
    -- now some files will be created for any lsl stream that is streaming the system locally --
    second to add events send a get request to: localhost:5000/addevent/<your integer id>
    third to stop send a get request to localhost:5000/stop
Cite: https://github.com/chkothe/pylsl 
'''

import datetime
from pylsl import StreamInlet, resolve_stream
import xmltodict
import json
import pprint
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

    # OpenBCI EEG electrode cap
    for stream in streams:
        inlet = StreamInlet(stream)
        convertedDictionary = xmltodict.parse(inlet.info().as_xml())
        # OpenBCI EEG stream
        if (convertedDictionary['info']['name'] == 'openbci_eeg'):
            threads.append(threading.Thread(target=writeStream, args=(splitext(filename)[0] + stream.name() + '.csv', stream)))
        # OpenBCI Aux stream
        elif (convertedDictionary['info']['name'] == 'openbci_aux'):
            pass
    # EMOTIV EPOC X
        else:
            print(convertedDictionary['info']['name']) # I want to know the stream name for the epoc x but I can't test it on my pc
            threads.append(threading.Thread(target=writeStream, args=(splitext(filename)[0] + stream.name() + '.csv', stream)))
            # pp = pprint.PrettyPrinter(compact=True)
            # pp.pprint(convertedDictionary)
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
    #pp = pprint.PrettyPrinter(compact=True)
    #pp.pprint(convertedDictionary)
    #return
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