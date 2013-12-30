from minerbus.io import reactor
from minerbus.io import transport
from sample_tfo_server import SampleProtocol
import time


class SampleProtocolClient(SampleProtocol):
    def receive(self, data):
        print(data.decode('UTF-8'))
        print('\n')


if __name__ == '__main__':
    handler = SampleProtocolClient()
    transport = transport.get('tfo', 'localhost', 3333, handler)  # TFOTransport('localhost', 3333, handler)

    try:

        transport.open(b'Hummel-Hummel')

        reactor.start()

        handler.send(b'Mors-Mors!')
        time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        reactor.stop()
