from channel import channel
from transmitte import transmitter
import numpy as np
from scipy.io import wavfile as wav


channels = []

def build_channel_map():
    bw = 50
    bw_len = np.arange(bw)
    num_channels = 5
    data_chunks = np.add(np.array_split(bw_len, num_channels), 10)
    for freq_list in data_chunks:
        c = channel(freq_list[0], freq_list[-1])
        channels.append(c)

def send_requests(data, ts, tc, t, chunks, fs):
    rx_ip = 'askrish2@40.87.3.106'
    tx = transmitter(channels, data, ts, tc, t, chunks, rx_ip, fs)
    print('beginning transmit')
    tx.start()

if __name__ == "__main__":

    fs, data = wav.read('440Hz-5sec.wav')
    ts = 1. / fs
    tc = 4

    data = np.array(data, dtype=np.uint8)
    bit_array = np.unpackbits(data)

    samples = bit_array.shape[0]
    t = np.arange(0, samples, 1)
    t = t / fs

    chunks = 4
    build_channel_map()
    send_requests(bit_array, ts, tc, t, chunks, fs)

