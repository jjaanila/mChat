"""
This module implements simple timers
"""

import time

"""
Simple timer with a constant timeout
"""
class Timer:
    def __init__(self, timeout=0):
        self.timeout = timeout  # seconds
        self.reset()

    def start(self, timeout=None):
        if timeout != None:
            self.timeout = timeout
        self.start_time = time.time()
        self.running = True

    def reset(self):
        self.start_time = -1
        self.running = False

    def hasExpired(self):
        return self.running and time.time() >= self.start_time + self.timeout