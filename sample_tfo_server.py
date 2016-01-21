from snet.nio import reactor
from snet.nio.protocols import BaseProtocol
from snet.nio.transport import TFOTransport
from snet.utils.daemon import sigfinish, daemon


class SampleProtocol(BaseProtocol):

    def __init__(self):
        self.data = b'hello'

    def has_output(self):
        return self.data is not None and self.data != b''

    def receive(self, data):
        self.send(data)

    def get_output(self):
        data = self.data
        self.data = None
        return data

    def send(self, data):
        self.data = data

handler = SampleProtocol()
transport = None


@sigfinish
def stop(*args, **kwargs):
    transport.close()
    reactor.stop()


@daemon(pidfile='/var/run/sample_server.pid')
def main():

    transport = TFOTransport('localhost', 3333, handler)
    reactor.start()
    transport.listen()


if __name__ == '__main__':
    main()
