import threading
import time


class Timer:
    def __init__(self, target, timeout=1):
        """
        @param target: Function to be executed on each timer tick
        @param timeout: Timer tick period
        """

        self.target = target
        self.timeout = timeout
        self.thread = None
        self.ticking = False
        self.tick_count = 0

    def start(self):
        if not self.ticking:
            self.thread = threading.Thread(target=self.tick)
            self.ticking = True
            self.tick_count = 0
            self.thread.start()

    def tick(self):
        while self.ticking:
            self.tick_count += 1
            self.target()
            time.sleep(self.timeout)

    def stop(self):
        self.ticking = False
        self.thread.join()
        self.thread = None

    def get_tick_count(self):
        return self.tick_count
