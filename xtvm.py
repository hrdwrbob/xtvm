#import mido
#import signal
#import rtmidi
#import time
#import rtmidi.midiutil
#from midi_controller import MidiController
#import voicemeeter
import miditoall
import logging
import time
logging.basicConfig(format='%(asctime)s %(message)s', encoding='utf-8', level=logging.ERROR)
#import threading


midiname= 'X-Touch One'
voicemeetertype='potato'
#from event_handler import EventHandler

#mido.set_backend('mido.backends.rtmidi/LINUX_ALSA')
#devices = mido.get_output_names()
#midiout = rtmidi.MidiOut()
#mido.get_input_names()
#available_ports = rtmidi.midiutil.list_input_ports()
#available_ports = rtmidi.midiutil.list_output_ports()

logging.info("starting up")

def main():
  mything = miditoall.MidiToVoiceMeeter(midiname,voicemeetertype)
  mything.run()
  while not time.sleep(5):
    time.sleep(1)
  




#while (vmr.dirty
#controller.lcd_display_update('Testing')
#controller.segment_display_update('Testing')
main()
#signal.signal(signal.SIGINT, sigint_handler)


#handler.stop()


