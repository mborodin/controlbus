import unittest

from minerbus import Bus


class TestBus(unittest.TestCase):
    def test_slave_acquire_ok(self):
        bus = Bus()
        try:
            bus.acquire()
        except Exception:
            self.fail('No exception is expected')
        finally:
            bus.release()


