import time

from snet.nio import reactor
from snet.nio import transport
from sample_tfo_server import SampleProtocol


class SampleProtocolClient(SampleProtocol):
    def receive(self, data):
        print(data.decode('UTF-8'))
        print('\n')


if __name__ == '__main__':
    handler = SampleProtocolClient()
    tr = transport.get('tfo', 'localhost', 3333, handler)

    try:

        tr.open(b'Hummel-Hummel')

        reactor.start()

        handler.send(b'Mors-Mors!')
        time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        tr.close()
        reactor.stop()
