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
import CSCP_MIDI_settings as config
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
                for index, device in enumerate(settings["MIDI Devices"]):
                    if not device.get("Enabled", True):
                        config.debug_log("[MIDI->CSCP] Device '{}' is disabled.".format(device.get("Name", index + 1)))
                        continue
                    config.debug_log("[MIDI->CSCP] Active device {} '{}': input='{}', channel mapping={}".format(
                        index + 1,
                        device.get("Name", "MIDI device {}".format(index + 1)),
                        device["MIDI -> CSCP port"],
                        device["Channel Mapping"],
                    ))
                self.midi_connections = [
                    MIDI_connection.Connection(
                        device["MIDI -> CSCP port"],
                        device["CSCP -> MIDI port"],
                        self.messages_available,
                    )
                    if device.get("Enabled", True) else None
                    for device in settings["MIDI Devices"]
                ]
                mixer = config.get_mixer(settings)
                self.cscp = CSCP_connection.Connection(
                    mixer["IP Address"],
                    int(mixer["Port"]),
                    self.messages_available,
                )
            except Exception:
                self.stop()
                raise

    def stop(self):
        with self.lock:
            for connection in self.midi_connections:
                if connection is not None:
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
                if midi_connection is None:
                    continue
                midi_message = midi_connection.get_message()
                while midi_message:
                    device = settings["MIDI Devices"][index]
                    device_name = device.get("Name", "MIDI device {}".format(index + 1))
                    config.debug_log("[MIDI->CSCP] Dispatching from '{}': type={}, channel={}, message={}.".format(
                        device_name,
                        midi_message.type,
                        getattr(midi_message, "channel", "n/a"),
                        midi_message,
                    ))
                    cscp_message = MIDI_to_CSCP.convert_message(
                        midi_message,
                        self.control_map,
                        device["Channel Mapping"],
                    )

                    if cscp_message:
                        if self.cscp.status == "Connected":
                            config.debug_log("[MIDI->CSCP] Device '{}' sending CSCP operation={}, strip={}, value={}, bytes={}.".format(
                                device_name,
                                cscp_message.operation,
                                cscp_message.strip,
                                cscp_message.value,
                                cscp_message.encoded.hex(" "),
                            ))
                            self.cscp.send(cscp_message.encoded)
                        else:
                            config.debug_log("[MIDI->CSCP] Device '{}' mapped the event to {}, but mixer status is '{}'; message not sent.".format(device_name, cscp_message, self.cscp.status))
                    else:
                        config.debug_log("[MIDI->CSCP] Device '{}' produced no CSCP message for {}.".format(device_name, midi_message))
                    midi_message = midi_connection.get_message()

            cscp_message = self.cscp.get_message()
            while cscp_message:
                for index, midi_connection in enumerate(self.midi_connections):
                    if midi_connection is None:
                        continue
                    midi_message = CSCP_to_MIDI.convert_message(
                        cscp_message,
                        self.control_map,
                        settings["MIDI Devices"][index]["Channel Mapping"],
                    )
                    if midi_message:
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
