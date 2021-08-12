import mido
from lcd_7bit_font import lcd_7bit_render
from unidecode import unidecode
from typing import List
from enum import Enum


class Control(Enum):
    FADER = 70
    LED_RING = 80
    LED_METER = 90


class Note(Enum):
    LED_KNOB = 0
    PREVIOUS = 20
    NEXT = 21
    STOP = 22
    PLAY = 23
    BANK_LEFT = 25
    BANK_RIGHT = 26
    CH_LEFT = 27
    CH_RIGHT = 28
    LED_METER = 90    
    FADER = 110
    MUTE = 29
    VU_ENABLE = 24


class Color(Enum):
#    BLACK = 0
    RED = 1
    MAGENTA = 5
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    WHITE = 7
    CYAN = 6
    def __init__(self, value):
        if len(self.__class__):
            # make links
            all = list(self.__class__)
            first, previous = all[0], all[-1]
            previous.next = self
            self.previous = previous
            self.next = first

class Invert(Enum):
    NONE = 0
    TOP = 1
    BOTTOM = 2
    BOTH = 3


class MidiController:
    def __init__(self, in_name: str,out_name: str = None) -> None:
        self._name = self.find_midi_input(in_name)
        self._port_in = mido.open_input(self._name)
        if out_name is None:
            out_name = in_name
        self._port_out = mido.open_output(self.find_midi_output(out_name))

    def find_midi_input(self, name) -> str:
        for input_name in mido.get_input_names():
            if input_name.startswith(name):
                return input_name

        raise Exception('No input found with name %s' % name)
    
    def find_midi_output(self, name) -> str:
        for output_name in mido.get_output_names():
            if output_name.startswith(name):
                return output_name

        raise Exception('No output found with name %s' % name)
    
    def get_input(self):
        return self._port_in.iter_pending()

    def reset(self) -> None:
        for n in range(1, 35):
            self._send(mido.Message('note_on', note=n, velocity=0))

        self.control_change(Control.FADER, 0)
        #self.control_change(Control.LED_RING, 64)
        #self.note_on(Note.VU_ENABLE, 0)


        self.segment_display_update('')
        self.lcd_display_update('')

    def note_on(self, note: Note, velocity: int) -> None:
        self._send(mido.Message('note_on', note=note.value, velocity=velocity))

    def note_off(self, note: Note, velocity: int) -> None:
        self._send(mido.Message('note_off', note=note.value, velocity=velocity))

    def control_change(self, control: Control, value: int) -> None:
        self._send(mido.Message('control_change', control=control.value, value=value))

    def polytouch(self, note: int, value: int) -> None:
        self._send(mido.Message('polytouch', note=note, value=value))    
    
    def pitchwheel(self, channel: int, pitch: int) -> None:
        self._send(mido.Message('pitchwheel', channel=channel, pitch=pitch)) 

    def aftertouch(self, channel: 0, value: int) -> None:
        self._send(mido.Message('aftertouch', channel=channel, value=value))
    
    def sysex(self, data: List[int]) -> None:
        self._send(mido.Message('sysex', data=data))

    def _send(self, message: mido.Message) -> None:
        self._port_out.send(message)
    
    def lcd_display_update(self, characters: str, color: Color = Color.WHITE, invert: Invert = Invert.NONE):
        self.sysex(self._create_lcd_display_data(characters,color,invert))

    def _create_lcd_display_data(self, characters: str, color: Color, invert: Invert) -> List[int]:
        characters = unidecode(characters)
        character_data = self._pad_to(list(map(ord, characters[:14])), 14)
        color_code = color.value | (invert.value << 4)

        return [0x00, 0x20, 0x32, 0x41, 0x4c, 0x00, color_code] + character_data

    def segment_display_update(self,characters: str):
        self.sysex(self._create_segment_display_data(characters))
        
    def _create_segment_display_data(self, characters: str) -> List[int]:
        characters = unidecode(characters)
        character_data = self._pad_to(lcd_7bit_render(characters[:12]), 12)

        return [0x00, 0x20, 0x32, 0x41, 0x37] + character_data + [0x00, 0x00]

    @staticmethod
    def _pad_to(data: List[int], n: int) -> List[int]:
        trimmed = data[:n]
        return trimmed + [0] * (n - len(trimmed))
