#!/usr/local/bin/env python
# Copyright 2016 Jose Berengueres. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ubertable v1.2 a conversation visualizer
#
# j.b Nov 4th 2016 postop  -- added service pool to allow simultaneous processing
#
# sources	https://gist.github.com/mabdrabo/8678538
# 			https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/speech/api-client/transcribe_async.py
#
# cc AT BY Jose Berengueres
#

# [START import_libraries]
import sys
import time
import string
import urllib
from subprocess import call
import re
from collections import defaultdict
import pyaudio
import wave
import base64
import json
import argparse
from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials
# [END import_libraries]


FORMAT = pyaudio.paInt16    # not sure it makes sense to sample at 16kHz at 8kBs
CHANNELS = 1
RATE = 8000   # Byte/s
CHUNK = 2048  # if you get IOError: [Errno -9981] Input overflowed increase this as per http://stackoverflow.com/questions/10733903/pyaudio-input-overflowed
RECORD_SECONDS = 4  # recording length
WAVE_OUTPUT_FILENAME = "file.wav"  # intermediate file
MIN_LENGTH = RECORD_SECONDS *RATE / CHUNK  # length of speech we will send over google in ticks, see t var


# [START authenticating]
DISCOVERY_URL = ('https://{api}.googleapis.com/$discovery/rest?'
                 'version={apiVersion}')

# Application default credentials provided by env variable
# GOOGLE_APPLICATION_CREDENTIALS
def get_speech_service():
    credentials = GoogleCredentials.get_application_default().create_scoped(
        ['https://www.googleapis.com/auth/cloud-platform'])
    http = httplib2.Http()
    credentials.authorize(http)

    return discovery.build('speech', 'v1beta1', http=http)
# [END authenticating]

def transcribe_async(speech_sound):
    # [START construct_request]
    speech_content = base64.b64encode(speech_sound)
    service_request = service.speech().asyncrecognize(

        body={
            'config': {
                # There are a bunch of config options you can specify. See
                # https://goo.gl/KPZn97 for the full list.
                'encoding': 'LINEAR16',  # raw 16-bit signed LE samples
                'sampleRate': 8000,  # 16 khz
                # See https://goo.gl/A9KJ1A for a list of supported languages.
                'languageCode': 'en-US',  # a BCP-47 language tag
            },
            'audio': {
                'content': speech_content.decode('UTF-8')
                }
            })
    # [END construct_request]

    # [START send_request]
    response = service_request.execute()
    # [END send_request]

    # Construct a GetOperation request.
    name = response['name']
    service_request = service.operations().get(name=name)
    return (service_request)


def rec3secs():
	stream = audio.open(format=FORMAT, channels=CHANNELS,
					rate=RATE, input=True,
					frames_per_buffer=CHUNK)
	print "recording..."	 
	for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
		data = stream.read(CHUNK)
		frames.append(data)
	#print "finished recording"


def loadWordFreq():
	d = defaultdict(lambda: 0)
	with open("5000words.csv") as f:
		for line in f:
			(key, val) = line.split(",")
			d[key] = int(val)
			print "" + key + " - " + str(d[key])
	return(d)


def visualize(response):
	txt = json.dumps(response['response'])
	# print(txt)
	j = json.loads(txt)
	if len(txt) >4 and 'results' in j:
		s = j["results"][0]["alternatives"][0]["transcript"] # maybe check if two responses came at the same time ?
		print(s)
		# to do: be smart about what we search, optimal search 2,3 keywords max with 
		# optimal entropy, prioritize: places, locations, products, verbs and colors.
		# but sometimes.. a popular sentence, refranyo is better! entropy vs. popularity  -->  a job for deep learning
		s = string.replace(s, ' ', '+')
		#print(s)
		imgurl = "https://www.google.co.jp/search?site=&tbm=isch&source=hp&biw=922&bih=953&q="+s+"&oq="+s+"&gs_l=img.3..0i19k1j0i8i30i19k1.1120.4510.0.9854.17.9.3.4.3.0.341.1308.0j4j1j1.6.0....0...1ac.1.64.img..5.8.772...0j0i4k1j0i30k1.5FGGhQxkjl4"
		#print(imgurl)
		call(["open",imgurl])
	else:
		# print ("no words returned by Google. . . no updating screen ")
		print (" . . . ")


def main():
	#freq   = loadWordFreq()
	global freq
	global audio 
	global stream 
	global frames
	global service
	global service_pool

	#init variables
	frames = []
	service_pool = []
	audio  = pyaudio.PyAudio()
	stream = audio.open(format=FORMAT, channels=CHANNELS,rate=RATE, input=True,frames_per_buffer=CHUNK)
	service = get_speech_service()

	rec3secs()
	transcribe_request = transcribe_async( b''.join(frames) )
	service_pool.append( transcribe_request )
	frames[:] = []
	stream = audio.open(format=FORMAT, channels=CHANNELS,
			rate=RATE, input=True,
			frames_per_buffer=CHUNK)
	t =0
	while True:
		t = t + 1
		sys.stdout.write('.')
		sys.stdout.flush()
		data = stream.read(CHUNK)
		frames.append(data)

		# jobs to do every 5s
		if ( t % MIN_LENGTH == 0) :
			transcribe_request = transcribe_async( b''.join(frames) )
			service_pool.append( transcribe_request )
			frames[:] = []
			stream = audio.open(format=FORMAT, channels=CHANNELS,
					rate=RATE, input=True,
					frames_per_buffer=CHUNK)

		# jobs to do every 2s
		if (t % 5 == 0):
			for req in service_pool:
				response = req.execute() #check if transcription is ready 
				if 'done' in response and response['done'] :
					service_pool.remove(req)
					visualize(response)

	# close audio				
	stream.stop_stream()
	stream.close()
	audio.terminate()


if __name__ == "__main__": 
	main()



