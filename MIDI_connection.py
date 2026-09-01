# MIDI_connection
# Used by the CSCP-MIDI application.
# Handles MIDI input and output using the mido library
# Runs a thread receiving MIDI messages
# Provides public methods to send messages and to get received messages
# Copyright Peter Walker 2020.
# Feedback - peter.allan.walker@gmail.com

import threading
from collections import deque

import mido


class Connection:

    def __init__(self, midi_input, midi_output, messages_available=None):
        self.input = midi_input
        self.output = midi_output
        self.messages = deque()
        self.messages_available = messages_available
        self.stopped = threading.Event()
        self.input_port = None
        self.transmitter = mido.open_output(self.output)

        self.receiver = threading.Thread(target=self._run)  # target is the method called when thread starts
        self.receiver.daemon = True  # Important - without this, cannot kill with control+c
        self.receiver.start()  # calls target - self.run()

    def _run(self):
        """
        Start listening for messages on the MIDI input
        """
        input_port = mido.open_input(self.input)
        self.input_port = input_port
        try:
            print("{} - MIDI input port is listening for control messages".format(input_port))
            for msg in input_port:
                if self.stopped.is_set():
                    break
                self.messages.append(msg)
                if self.messages_available is not None:
                    self.messages_available.set()
        finally:
            self.input_port = None
            input_port.close()

    # The following are intended to be externally accessed/public methods
    def get_message(self):
        """
        Returns and removes first message from self.messages
        :return:
        """
        try:
            return self.messages.popleft()
        except IndexError:
            return False

    def send_message(self, msg):
        # print("DEBUG CSCP SEND", msg)
        self.transmitter.send(msg)

    def close(self):
        self.stopped.set()
        if self.input_port is not None:
            self.input_port.close()
        self.transmitter.close()


if __name__ == '__main__':

    print(20*'#'+' MIDI_connection ' + 20*'#')

    # Check what MIDI inputs are available
    inputs = mido.get_input_names()
    print('\nMIDI inputs available:')
    for i, source in enumerate(inputs):
        print('\t', source[:-2], '\t:', i)

    chosen_input = int(input("Select MIDI input: "))

    outputs = mido.get_output_names()
    print('\nMIDI outputs available:')
    for i, source in enumerate(outputs):
        print('\t', source[:-2], '\t:', i)

    chosen_output = int(input("Select MIDI output: "))
    midi_connection = Connection(inputs[chosen_input], outputs[chosen_output])

    # params for outgoing test message:
    strip = 1
    value = -8000

    count = 0
    button_strip = 8
    button_state = True

    midi_msg = mido.Message('note_on', channel=0, note=0, velocity=127)
    midi_connection.send_message(midi_msg)

    """
    while True:
        # Check for received midi message
        message = midi_connection.get_message()
        #if message and message.type != "control_change":
        if message:
            #print("RECEIVED", message, ", messages remaining: ", len(midi_connection.messages))
            pass
        
        
        if count % 100 == 0:
            # Send test fader move message
            midi_msg = mido.Message('pitchwheel', channel=0, pitch=value)
            # print("SENDING", midi_msg)
            midi_connection.send_message(midi_msg)
            value += 1
            if value > 8000:
                value = -8000
        
        
        # Send test button press messages - toggle button on and off:
        if count % 10000 == 0:
            if button_state:
                button_value = 127
                button_state = False
            else:
                button_value = 0
                button_state = True

            midi_msg = mido.Message('note_on', channel=0, note=button_strip, velocity=button_value)
            midi_connection.send_message(midi_msg)

        count += 1
    """