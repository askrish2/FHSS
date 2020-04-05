from channel import channel
from receiver import receiver
import numpy as np

channels = []

def build_channel_map():
    bw = 50
    bw_len = np.arange(bw)
    num_channels = 5
    data_chunks = np.array_split(bw_len, num_channels)
    for freq_list in data_chunks:
        c = channel(freq_list[0], freq_list[-1])
        channels.append(c)

def listen_requests(tc, ts, chunks):
    rx_ip = 'askrish2@40.87.3.106'
    rx = receiver(channels, chunks, ts, tc, rx_ip, 'received-wavfile.wav')
    print('beginning to receive')
    rx.start()

if __name__ == "__main__":
    ts = 10
    tc = 4
    chunks = 4
    build_channel_map()
    listen_requests(tc, ts, chunks)
