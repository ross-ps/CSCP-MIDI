# CSCP_connection
# Used by the CSCP-MIDI application.
# Provides a class/object to Handle IP connection with mixer using socket library
# Runs a thread receiving data checking for valid CSCP messages
# Provides public methods to send messages and to get received messages
# Copyright Peter Walker 2020.
# Feedback - peter.allan.walker@gmail.com

# See Readme.txt for info on how to use this app.
# See Project_Notes.txt for info on the implementation - how the app works.


import socket
import threading
import time

import CSCP_unpack as unpack
import CSCP_decode as parse
import CSCP_encode as encode

import traceback

TIMEOUT = 3  # how long to wait when starting connection and receiving data.
RECEIVE_TIMEOUT = 10


class Connection:
    """
    A CSCP Connection object
    Forms an IP connection
    Runs a thread monitoring the connection,
    periodically attempting reconnect when not connected or connection is lost
    When connected, validates received messages and stores them as CSCP Message objects
    Provides methods to get received messages and to send CSCP Message objects
    """
    def __init__(self, ip_address, tcp_port, messages_available=None):

        self.address = ip_address
        self.port = tcp_port
        self.sock = False
        self.status = 'Starting'
        self.messages = []
        self.messages_available = messages_available
        self.stopped = threading.Event()

        # Potentially, there may be residual data at the end of chunk of received data
        # that cannot be parsed but might be the beginning of a message
        # whose remainder is in the next chunk data to be received
        # So will save any such residual data and prepend to the next chunk received
        self.residual_data = False

        # Set up to run in thread
        self.receiver = threading.Thread(target=self._run)
        # I believe the following line causes the thread to stop when the main application stops
        # ... means e.g. control+c will release the terminal
        # (before adding this I had to keep closing terminal each time I wanted to stop the program)
        self.receiver.daemon = True
        self.receiver.start()

    def _connect(self):
        """ Called by _run on initialisation of Connection class """

        if self.stopped.is_set():
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(TIMEOUT)
            self.sock.connect((self.address, self.port))
            #print('CSCP_connection: Socket connection established with address {} on port {}'.format(self.address, self.port))

            # Send a message to get some data back
            ping = encode.read_back('read_console_info')
            self.send(ping)
            self.status = "Connected"

        except (socket.timeout, OSError):
            print('CSCP_connection: Failed to create connection with IP address {} on port {}'.format(self.address, self.port))
            if self.sock:
                self.sock.close()
            self.sock = False

    def _run(self):
        """
        Called by init's self.receiver thread
        Make and monitor a connection and listen for incoming CSCP messages
        """
        # if not connected, try to create a socket connection every 5s.
        while not self.sock and not self.stopped.is_set():
            if not self.status == 'Connection Lost!':
                self.status = 'Not Connected'
            self._connect()
            self.stopped.wait(5)  # Wait before trying to connect again

        if self.stopped.is_set():
            return

        # TODO - Check the following if I'm missing messages or getting jittery fader control
        self.sock.settimeout(RECEIVE_TIMEOUT)

        self.pinged = False

        # Listen for incoming messages
        while not self.stopped.is_set():
            try:
                data = self.sock.recv(1024)
            except socket.timeout:
                data = False
            except OSError:
                break

            # print('CSCP_connection run: data received', data, 'pinged', self.pinged)

            if data:
                self.pinged = False
                # Unpack messages from received bytes, checking residual data from previous call
                # to check if a message spanned 2 received chunks
                messages, self.residual_data = unpack.unpack_data(data, self.residual_data)
                if messages:
                    for msg in messages:
                        self.messages.append(parse.Message(msg))
                    if self.messages_available is not None:
                        self.messages_available.set()

            elif self.pinged:
                # No data received even after mixer being pinged
                self.status = "Connection Lost!"
                #print("DEBUG CSCP_connect, dropping connection!")
                self.close()
                break

            else:
                # No data received, send a message to see if the mixer is still there
                # TODO - Check this, I'm not pinging all the time? thought I had set a timeout to trigger this
                self.pinged = True
                #print('CSCP_connection_2_1>run: no messages received for {}s, pinging mixer'.format(RECEIVE_TIMEOUT))
                ping = encode.read_back('read_console_name')
                self.send(ping)

    def close(self):
        self.stopped.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = False

    # PUBLIC METHODS
    def send(self, msg):
        """
        Public method to send a message to the mixer
        :param msg: CSCP_encode.Message object
        """
        try:
            # TODO - take message object so dont have to pass msg.encoded in main
            # Will need to fix the ping read console info message from encode.
            self.sock.sendall(msg)
        except (socket.timeout, OSError, AttributeError):
            pass

    def get_message(self):
        """
        public / called externally
        - removes and returns the oldest message in the buffer
        :return: CSCP Message object
        """
        r = False
        if self.messages:
            r = self.messages[0]
            self.messages = self.messages[1:]
        return r

    # TODO - CHECK I NO LONGER NEED THIS
    """ 
    def _receive(self):
        #Check Receive Buffer
        self.sock.settimeout(None)
        data = self.sock.recv(1024)
        return data
    """


if __name__ == '__main__':

    address = "192.169.1.200"
    #address = "127.0.0.1"  # Localhost for testing with virtual mixer running on this machine
    port = 12345

    print(20*'#'+' CSCP_connection ' + 20*'#')
    connection = Connection(address, port)

    test_message = b'\xf1\x06\x00\x80\x00\x00\x03\x02\xe8\x93'
    #decoded = parse.Message(test_message)
    #print("DEBUG test message", decoded)

    i = 0
    strip = 0
    while True:
        print('\n', i, 'qty:', len(connection.messages), 'residual data', connection.residual_data)
        for message in connection.messages:
            print("Controller received:", message)
        if connection.status == "Connected" and i % 1 == 0:
            #connection.send(test_message)
            msg = encode.Message('fader_move', strip, 744, recipient='mixer')
            print("Controller sending", msg)
            connection.send(msg.encoded)

        i += 1
        strip += 1

        time.sleep(2)
