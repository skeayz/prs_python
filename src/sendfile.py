import socket
import math
from utils import *
import threading
import datetime
import os
class sendfile:

    lastAck = 0
    duplicates = -1
    window_size = 30
    window_print = 1
    seq = 1
    transfer = True
    final_ack=0
    rtt = 0.0
    lock = threading.Lock()
    buffersize = 1494
    threshold = 30

    def __init__(self, socket: socket.socket, rtt: float):
        self.s = socket
        self.rtt = round(rtt * 1.3, 4)
        self.s.settimeout(round(rtt * 5, 4))

    def receive(self):
        ack = -1
        time_window: list(tuple) = []
        start = datetime.datetime.now().timestamp()
        while ack != self.final_ack:
            # flush the buffer
            time_window.append((datetime.datetime.now().timestamp() - start, self.window_print))
            try:
                data, addr = self.s.recvfrom(1024)
                print(f'\t[+] Reiceved : {custom_decode(data)} from {addr}')
                ack = int(custom_decode(data).replace("ACK", ""))
                
                if(ack > self.lastAck and self.threshold > self.window_size):
                    with self.lock:
                        self.window_size += (ack - self.lastAck) * 2
                        self.seq = ack + 1
                        self.window_print = self.window_size
                    self.lastAck = ack
                    self.duplicates = 0
                else:
                    with self.lock:
                        self.window_size += 1
                        self.seq = ack + 1
                        self.window_print = self.window_size
                    self.lastAck = ack
                    self.duplicates = 0
                    

                if (ack == self.lastAck and self.duplicates < 2):
                    self.duplicates += 1
                elif (ack == self.lastAck and self.duplicates >= 2):
                    print("DUPLICATES")
                    with self.lock:
                        self.seq = self.lastAck
                        self.window_size = self.window_size // 2 if self.window_size > 1 else 1
                        self.window_print = self.window_size
                    self.lastAck = self.lastAck-1
                    self.duplicates = 0
                
                
            except socket.error as err:
                print(f'[-] Timeout')
                with self.lock:
                    self.seq = self.seq - 1 if self.seq > 1 else 1
                    self.window_size = self.window_size // 2 if self.window_size > 1 else 1
                    self.window_print = self.window_size
                    
        ## When we receive the final ack we send end to the client
        self.s.sendto(custom_encode("FIN"), addr)
        print(f'\t[+] Sent : FIN to {addr}')
        self.window_size = 0
        self.transfer = False
        with open('time_window.txt', 'w') as f:
            for time, window_size in time_window:
                f.write(f'{time} {window_size}\n') 

    def run(self):
        print(f'\t\n{" Start of the file transfer ":=^80}\n')
        data, addr = self.s.recvfrom(1024)
        print(f'\t[+] Reiceved : {custom_decode(data)} from {addr}')
        try:
            f = open(custom_decode(data), 'rb')
        except FileNotFoundError:
            raise Exception("File not found")
        f.seek(0, os.SEEK_END)
        self.final_ack = math.ceil(f.tell()/self.buffersize)
        th1 = threading.Thread(target=self.receive)
        th1.start()
        # start timer
        # Send the file the client expects data messages that start with a sequence number, in string format, over 6 bytes, buffer is 1024 bytess
        while self.transfer:
            while self.window_size > 0:
                with self.lock:
                    f.seek((self.seq-1)*self.buffersize)
                    data = f.read(self.buffersize)
                if(data):
                    self.s.sendto(str(self.seq).zfill(6).encode() + data, addr)
                    self.s.settimeout(round(self.s.gettimeout(), 4))
                    print(
                        f'\t[+] Sent : {str(self.seq).zfill(6)} to {addr} with window size {self.window_size}')
                    with self.lock:
                        self.seq += 1
                    with self.lock:
                        self.window_size -= 1
        # print time_window into a file
        th1.join()
        print("coucou g join")   
        exit(0)   
