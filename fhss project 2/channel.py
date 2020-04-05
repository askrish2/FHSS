class channel:

    def __init__(self, start_freq, end_freq):
        self.start_freq = start_freq
        self.end_freq = end_freq

    def get_start_freq(self):
        return self.start_freq

    def get_end_freq(self):
        return self.end_freq
