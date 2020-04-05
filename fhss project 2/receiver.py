from scipy.signal import butter, lfilter
import numpy as np
import time
import pickle
import random
from threading import Thread, Lock
import socket
import math
from scipy.io import wavfile as wav

data_mutex = Lock()
count_mutex = Lock()
pn_lock = Lock()
ip_lock = Lock()
end_lock = Lock()
channels_lock = Lock()

class receiver:

    def __init__(self, channels, chunks, ts, tc, ip, fname):
        self.channels = channels
        self.chunks = chunks
        self.ts = ts
        self.tc = tc
        self.all_data = []
        self.curr_pn = 0
        self.eof = True
        self.ip = ip
        self.fname = fname

    def listen_burst(self):
        burst_end = 1000
        count_burst = 0
        while self.eof:
            if math.fabs(time.time() - burst_end) >= self.ts:
                burst_end = time.time()
                time.sleep(0.5)
                server_thread = Thread(target=self.server, args=(self.curr_pn, count_burst))
                server_thread.daemon = True
                server_thread.start()
                count_burst += 1

    def server(self, pn, count):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        channels_lock.acquire()
        channel = self.channels[pn]
        channels_lock.release()
        min_freq = channel.get_start_freq()
        max_freq = channel.get_end_freq()
        local_freq = np.rint((min_freq + max_freq) / 2.)
        ip_lock.acquire()
        server_address = (self.ip, 8000 + pn)
        print('listening on channel ' + str(8000 + pn) + ' for chunk ' + str(count))
        ip_lock.release()
        sock.settimeout(6)
        try:
            sock.bind(server_address)
            data, address = sock.recvfrom(4096)
            if data:
                data = pickle.loads(data)
                (msg, msg_meta) = data

                if type(msg_meta) is not tuple and count > msg_meta:
                    print('msg from prev hop')
                    sock.close()
                    return

                print('receiving data chunk ' + str(count) + ' on channel ' + str(8000 + pn))
                message = pickle.dumps(count)
                print('sending confirmation for chunk ' + str(count))
                sock.sendto(message, address)

                if '*' in msg:
                    print('reached end of data')
                    fs, total = msg_meta
                    self.write_wav(fs, total)

                else:
                    self.costas_loop(msg, local_freq)

        except socket.timeout:
            print('timeout')
        except socket.error:
            print('socket error: addr in use')
            return
        finally:
            sock.close()

    # first multiply by the fc term, assuming fc is correct (by setting the error to 0)
    # filter out the high frequency term
    # then multiply the fc by the negative exp of the accumulated error, if there is some error, it will drive the fc lower to the signal frequnecy,
    # if there is no error, then the fc will be multiplied by 1 because it is correct and should remain the same
    # keep incrementing the error by the loop filter output
    # because I update the frequency as I go along in the loop, it will be slightly less accurate towards the beginning

    def costas(self, sig, fc):
        #sig = np.float64(sig)
        phase_offset = 0
        N = len(sig)
        bb = np.zeros(N)
        error = np.zeros(N)

        for i in range(0, N):
            # Downconverting to Baseband
            if i == 0:
                bb[i] = sig[i] * float(np.cos(2. * np.pi * fc * i + float(phase_offset))) * np.exp(0)
            else:
                try:
                    err = np.exp(-error[i - 1])
                except:
                    err = 1

                bb[i] = sig[i] * float(np.cos(2. * np.pi * fc * i + float(phase_offset))) * float(err)

            bb_f = self.lowpass_filter(bb[0:i + 1])
            error[i] = np.real(bb_f[i]) + float(error[i - 1])

        bb = np.absolute(np.int8(bb))

        bb[bb <= 0] = 1
        bb[bb > 1] = 0

        return bb

    def write_wav(self, fs, total):
        data_mutex.acquire()
        if len(self.all_data) < total:
            self.all_data = np.pad(self.all_data, (0, total - len(self.all_data)), 'constant', constant_values=(0))
        res_array = np.array(self.all_data).reshape(int(len(self.all_data) / 8), 8)
        int_array = np.packbits(res_array, axis=1).flatten(order='C')
        print(int_array)
        wav.write(self.fname, fs, int_array)
        data_mutex.release()
        end_lock.acquire()
        self.eof = False
        end_lock.release()

    def lowpass_filter(self, signal, order=5):
        cut_off = 0.5
        b, a = butter(order, cut_off, btype='low', analog=False)
        y = lfilter(b, a, signal)
        return y

    def pn_sequence_generator(self):
        random.seed(1)
        pn_end = 1000
        while self.eof:
            if math.fabs(time.time() - pn_end) >= self.tc:
                self.curr_pn = random.randint(0, len(self.channels) - 1)
                pn_end = time.time()

    def start(self):
        update_pn = Thread(target=self.pn_sequence_generator)
        update_pn.daemon = True
        update_pn.start()
        listen_burst = Thread(target=self.listen_burst)
        listen_burst.daemon = True
        listen_burst.start()

        while self.eof:
            continue