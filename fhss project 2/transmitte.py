import numpy as np
import random
import pickle
import socket
from threading import Thread, Lock
import math
import time

pn_lock = Lock()
ip_lock = Lock()
fs_lock = Lock()


class transmitter:

    def __init__(self, channels, data, ts, tc, t, chunks, ip, fs):
        self.channels = channels
        self.data = data
        self.ts = ts
        self.tc = tc
        self.t = t
        self.chunks = chunks
        self.curr_pn = 0
        self.eof = True
        self.ip = ip
        self.fs = fs

    def pn_sequence_generator(self):
        random.seed(1)
        pn_end = 1000
        while self.eof:
            if math.fabs(time.time() - pn_end) >= self.tc:
                self.curr_pn = random.randint(0, len(self.channels) - 1)
                pn_end = time.time()

    def burst_transmit(self):
        burst_data = np.array_split(self.data, self.chunks)
        burst_time = np.array_split(self.t, self.chunks)
        burst_end = 1000
        count_burst = 0
        while True:
            if math.fabs(time.time() - burst_end) >= self.ts:
                burst_end = time.time()
                if burst_data:
                    print('transmit burst')
                    time.sleep(0.5)
                    burst = burst_data.pop(0)
                    burst_t = burst_time.pop(0)
                    burst_thread = Thread(target=self.mod_transmit, args=(burst, self.curr_pn, count_burst, burst_t))
                    burst_thread.daemon = True
                    burst_thread.start()
                else:
                    time.sleep(0.5)
                    self.mod_transmit([], self.curr_pn, count_burst, [])
                    self.eof = False
                    break
                count_burst += 1

    #bpsk modulation
    def mod_transmit(self, data, pn, count, t):
        if len(data):
            pn_lock.acquire()
            channel = self.channels[pn]
            pn_lock.release()
            min_freq = channel.get_start_freq()
            max_freq = channel.get_end_freq()
            carrier_freq = min_freq
            pdata = np.subtract(np.multiply(2, data), 1)
            signal = np.cos(2 * np.pi * carrier_freq * t)
            mod_signal = np.multiply(pdata, signal)
            message = pickle.dumps((mod_signal, count))
        else:
            fs_lock.acquire()
            end_signal = ('*', (self.fs, len(self.data)))
            fs_lock.release()
            message = pickle.dumps(end_signal)
            print('reached end of data')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pn_lock.acquire()
        ip_lock.acquire()
        server_address = (self.ip, 8000 + pn)
        ip_lock.release()
        pn_lock.release()
        pn_lock.acquire()
        print('sending data chunk ' + str(count) + ' on channel ' + str(8000 + pn))
        pn_lock.release()
        while True:
            try:
                sock.sendto(message, server_address)
                print('waiting for confirmation for chunk ' + str(count))
                sock.settimeout(2)
                data, server = sock.recvfrom(4096)
                if data:
                    recv_count = pickle.loads(data)
                    if recv_count == count:
                        print('received confirmation for chunk ' + str(count))
                        sock.close()
                        break
            except socket.timeout:
                # print('timeout so send again')
                continue

    def start(self):
        update_pn = Thread(target=self.pn_sequence_generator)
        update_pn.daemon = True
        update_pn.start()
        send_burst = Thread(target=self.burst_transmit)
        send_burst.daemon = True
        send_burst.start()

        while True:
            continue
