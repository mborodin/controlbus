from nio import reactor
from nio.protocol import Protocol
from nio.transport import TFOTransport
from nio.daemon import sigfinish, daemon


class SampleProtocol(Protocol):

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


@daemon(pidfile='/home/mborodin/sample_server.pid')
def main():

    transport = TFOTransport('localhost', 3333, handler)
    reactor.start()
    transport.listen()


if __name__ == '__main__':
    main()
