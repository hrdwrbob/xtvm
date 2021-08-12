from midi_controller import MidiController, Note, Control, Color, Invert
import mido
import rtmidi
import rtmidi.midiutil
import voicemeeter
import logging
import time
import random
import subprocess
import asyncio
import math
from itertools import chain

from scipy.interpolate import interp1d
from windows_rt_media import WindowsRuntimeMedia as wrm
from apscheduler.schedulers.asyncio import AsyncIOScheduler





class MidiToVoiceMeeter:
    volumelevel= [0  ,4  , 13, 21,29, 46, 62,  69, 79,96,111,127]
    volumefader= [-60,-60,-50,-40,-30,-20,-10,-7.9, -5, 0, +5,+12]
    get_volume = interp1d(volumelevel,volumefader)
    get_fader = interp1d(volumefader,volumelevel)
    _bus_names = ['','','','','','VM VAIO in','VM AUX in','VM VAIO 3 in','Speakers','Headphones','nothing','nothing','nothing','VM Vout 1','VM raw mic','virtual mic']
    
    def __init__(self, midiname: str,voicemeetertype: str = None) -> None:
      self._controller = MidiController(midiname)
      self._controller.reset()
      self._media = wrm()
      self._vmr = voicemeeter.remote(voicemeetertype, delay=0.0)
      self._vmr.login()
      self.lcd_color = Color.CYAN
      self._strips = self._vmr.inputs +self._vmr.outputs
      self._numstrips = len(self._strips)
      self._changestrip(8)
      self._controller.segment_display_update("  foobar2k")
      self.prev_level = 0
      self._volume_touching = False
      self._segment_lock = False
      self._display_lock_seconds = 0
      self._scheduler = AsyncIOScheduler()
      self._loops_brother = asyncio.new_event_loop()
      self._trackname = ''
      self._mediasource=''
      self._segment_text_position=0
      self._segment_text_direction=0
      
    def run(self):
      #logging.debug("Running main loop")
      self._scheduler.add_job(self.get_midi_input, 'interval', seconds=.001)
      self._scheduler.add_job(self.update_from_vmr, 'interval', seconds=.001)
      self._scheduler.add_job(self._update_levels, 'interval', seconds=.10)
      self._scheduler.add_job(self._get_media, 'interval', seconds=.30)
      self._scheduler.add_job(self._update_media_display, 'interval', seconds=.50)
      self._scheduler.add_job(self._unlock_display, 'interval', seconds=1)
      self._loops_brother.call_soon(self._scheduler.start)
      asyncio.run(self.welcome_ceremony())
      self._loops_brother.run_forever()

    async def _unlock_display(self):
      if self._display_lock_seconds > 0:
        self._display_lock_seconds = self._display_lock_seconds - 1
      else:
        self._display_lock_seconds = 0
        self._segment_lock = False
    
    async def _update_media_source(self):
      self._segment_lock = True
      self._display_lock_seconds = 2
      if self._media.get_source_name()[-4:] == ".exe":
        displayname = self._media.get_source_name()[:-4]
      else:
        displayname = self._media.get_source_name()
      self._controller.segment_display_update(displayname)
      await self._update_media_display()
    
    async def _get_media(self):
      if self._media.get_source_name() != self._mediasource:
        await self._update_media_source()
      newtrackname = await self._media.get_track_name()
      if self._trackname != newtrackname:
        self._segment_text_position = 0
        self._segment_text_direction = 0
      self._trackname = newtrackname
      self._mediasource = self._media.get_source_name()
      

    async def _update_media_display(self):
      if self._segment_lock:
        return
      self._controller.segment_display_update(self._trackname[self._segment_text_position:])
      if len(self._trackname) > 9:
        if (self._segment_text_direction == 0 and len(self._trackname)-self._segment_text_position > 9) or (self._segment_text_direction and self._segment_text_position == 0):
          self._segment_text_position = self._segment_text_position + 1
          self._segment_text_direction = 0
        else:
          self._segment_text_position = self._segment_text_position - 1
          self._segment_text_direction = 1

      
    async def welcome_ceremony(self):
      self._segment_lock = True
      self._display_lock_seconds = 100
      self._controller.segment_display_update("  Welcome")
      # Fader up and down.
      self._controller.control_change(Control.FADER,127)
      await asyncio.sleep(1)
      self._controller.control_change(Control.FADER,0)
      # VU meter up and down.
      for value in chain(range(1,9),range(8,0,-1)):
        self._controller.control_change(Control.LED_METER,value*14)
        await asyncio.sleep(0.08)
      # Make the keys come on
      for key in Note:
        self._controller.note_on(key,127)
        time.sleep(.05)
      self._segment_lock = False
      self._display_lock_seconds = 0
      await self._update_media_source()
      await self._get_media()
      await self._update_media_display()
        

      
    def get_midi_input(self):
      for msg in self._controller.get_input():
        self._handle_midi_input(msg)
    
    async def update_from_vmr(self):
      if (self._vmr.dirty):
        if (self._volume_touching is None):
          return
        if (self._volume_touching==False):
          if self._selectedstrip.gain == -60.0:
            self._controller.control_change(Control.FADER,0)
          else:
            self._controller.control_change(Control.FADER,int(self.get_fader(self._selectedstrip.gain)))
        else:
            self._volume_touching=False
            await asyncio.sleep(2)
    
    async def _update_levels(self):
      rawlevel = self._selectedstrip.get_level()
      level = 0
      if rawlevel != 0:
        level = math.log10(rawlevel)+6
      if level < 0:
        displaylevel=1
      else:
        displaylevel=min(8,int(level*1.3))
      self._controller.control_change(Control.LED_METER,displaylevel*14)

    def _get_strip_name(self):
      try:
        label = self._selectedstrip.label
      except:
        label = ''
      if label != '':
          self._bus_names[self._selectedstripnum] = label
          return label
      else:
        return self._bus_names[self._selectedstripnum]
    
    def _next_strip(self):
      if self._selectedstripnum == self._numstrips-1:
        return
      self._changestrip(self._selectedstripnum+1)

    
    def _prev_strip(self):
      if self._selectedstripnum == 0:
        return
      self._changestrip(self._selectedstripnum - 1)

    def _changestrip(self,stripnum):
      self._selectedstripnum = stripnum
      self._selectedstrip = self._strips[self._selectedstripnum]
      stripname = self._get_strip_name()
      self._controller.lcd_display_update(stripname,self.lcd_color)
      if self._selectedstrip.gain == -60.0:
        self._controller.control_change(Control.FADER,0)
      else:
        self._controller.control_change(Control.FADER,int(self.get_fader(self._selectedstrip.gain)))   
      self._highlightstrip()
      
    def _highlightstrip(self):
      #TODO: highlight the strip in the voicemeeter UI
      pass
           
    def _handle_midi_input(self,m):
      if hasattr(m, 'note'):
        if m.note==28 and m.velocity==127:
          self._next_strip()
        elif m.note==27 and m.velocity==127:
          self._prev_strip()
        elif m.note==13 and m.velocity==127:
          self._selectedstrip.gain = 0.0
        elif m.note==29 and m.velocity==127:
          if  self._strips[0].mute is True:
            self._strips[0].mute = False
            self._strips[2].mute = False
            self._strips[3].mute = False
            self._controller.note_on(Note.MUTE,0)
            return
          self._strips[0].mute = True
          self._strips[2].mute = True
          self._strips[3].mute = True
          self._controller.note_on(Note.MUTE,127)
        elif m.note==110 and m.velocity ==127:
          self._volume_touching=None
          self._controller.lcd_display_update(self._get_strip_name(),Color.RED)
        elif m.note==110 and m.velocity ==0:
          self._controller.lcd_display_update(self._get_strip_name(),self.lcd_color)
          self._volume_touching=True
        elif m.note==26 and m.velocity==127:
          self._media.next_source()
        elif m.note==25 and m.velocity==127:
          self._media.prev_source()
        elif m.note==23 and m.velocity==127:
          self._media.playpause()
        elif m.note==22 and m.velocity==127:
          self._media.stop()
        elif m.note==20 and m.velocity==127:
          self._media.prev()
        elif m.note==21 and m.velocity==127:
          self._media.next()
        else:
          print(m)
        
      elif hasattr(m, 'control'):
        if m.control==70:
          self._selectedstrip.gain = self.get_volume(m.value)
          print (str(m.value))
        elif m.control==88 and m.value ==65:
          self._media.jog_forward()
        elif m.control==88 and m.value ==1:
          self._media.jog_backward()
        else:
          print(m)
      else:
          print(m)
