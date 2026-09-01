# CSCP-MIDI
# Provides two-way connection and communications between CSCP and MIDI devices.
# Copyright Peter Walker 2020.
# Feedback/Requests - peter.allan.walker@gmail.com

# See Readme.txt for info on how to use this app.
# See Project_Notes.txt for info on the implementation - how the app works.

import json
import threading

from SettingsWindow import SettingsWindow

import CSCP_connection
import CSCP_to_MIDI
import MIDI_connection
import MIDI_to_CSCP
import traceback

# mido uses rtmidi backend
# For some reason I have to ensure I have rtmidi installed in order for mido to work
#    'pip install python-rtmidi'
# Then it will work fine as a python script, but when run as an exe built by pyinstaller, it will fail when it
# attempts midi comms.
# The following import fixes this, this import is included purely for pyinstaller to build a functioning exe...
import mido.backends.rtmidi  # DO NOT DELETE THIS EVEN THOUGH PYCHARM THINKS IT IS NOT REQUIRED


class AppController:
    def __init__(self):
        self.cscp = None
        self.control_map = None
        self.midi_connections = []
        self.lock = threading.RLock()
        self.messages_available = threading.Event()
        self.strip_cuts = {
            "0" : False,
            "1" : False,
            "2" : False,
            "3" : False,
            "4" : False,
            "5" : False,
            "6" : False,
            "7" : False,
            "8" : False,
            "9" : False,
            "10" : False,
            "11" : False,
            "12" : False,
            "13" : False,
            "14" : False,
            "15" : False 
        }

    def start(self, settings):
        with self.lock:
            self.stop()
            try:
                with open(settings["Mode/Mapping"][1], "r") as control_map_file:
                    self.control_map = json.load(control_map_file)
                self.midi_connections = [
                    MIDI_connection.Connection(
                        device["MIDI -> CSCP port"],
                        device["CSCP -> MIDI port"],
                        self.messages_available,
                    )
                    for device in settings["MIDI Devices"]
                ]
                self.cscp = CSCP_connection.Connection(
                    settings["Mixer IP Address"],
                    settings["Mixer CSCP Port"],
                    self.messages_available,
                )
            except Exception:
                self.stop()
                raise

    def stop(self):
        with self.lock:
            for connection in self.midi_connections:
                connection.close()
            self.midi_connections = []
            if self.cscp is not None:
                self.cscp.close()
                self.cscp = None
            self.control_map = None

    def process_messages(self, settings):
        with self.lock:
            if self.cscp is None or self.control_map is None:
                return

            for index, midi_connection in enumerate(self.midi_connections):
                midi_message = midi_connection.get_message()
                while midi_message:

                    midi_message.channel += settings["MIDI Devices"][index]["Channel Offset"]

                    cscp_message = MIDI_to_CSCP.convert_message(midi_message, self.control_map, settings["MIDI Devices"][index]["Channel Offset"])

                    if cscp_message and self.cscp.status == "Connected":
                        self.cscp.send(cscp_message.encoded)
                    midi_message = midi_connection.get_message()

            cscp_message = self.cscp.get_message()
            while cscp_message:
                midi_message = CSCP_to_MIDI.convert_message(cscp_message, self.control_map)
                if midi_message:
                    
                    for i, midi_connection in enumerate(self.midi_connections):
                        if(midi_message.channel >= settings["MIDI Devices"][i]["Channel Offset"] and midi_message.channel < settings["MIDI Devices"][i]["Channel Offset"]+8):
                            midi_message.channel -= settings["MIDI Devices"][i]["Channel Offset"]
                            midi_connection.send_message(midi_message)
                cscp_message = self.cscp.get_message()


def main():
    controller = AppController()
    stop_event = threading.Event()

    def shutdown():
        stop_event.set()
        controller.messages_available.set()
        controller.stop()
        if worker.is_alive():
            worker.join()

    settings_window = SettingsWindow(controller, shutdown)

    def process_messages():
        while not stop_event.is_set():
            controller.messages_available.wait()
            controller.messages_available.clear()
            if stop_event.is_set():
                break
            try:
                controller.process_messages(settings_window.settings)
            except Exception as error:
                print("[APP] Message processing failed: {}".format(error))

    worker = threading.Thread(target=process_messages, name="CSCP-MIDI backend")
    worker.start()
    try:
        settings_window.run()
    finally:
        shutdown()


if __name__ == '__main__':
    main()
