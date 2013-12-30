import socket
from nio import reactor
from nio.utils import get_subclasses


class UnknownTransport(Exception):
    pass

_MSG_FASTOPEN = 0x20000000
_TCP_FASTOPEN = 23
_QLEN = 7

_transport_map = {}


def add_transport(transport, protocol):
    if not protocol in _transport_map:
        _transport_map[protocol] = []
    _transport_map[protocol].append(transport)


def find_transports(protocol) -> list:
    if not protocol in _transport_map:
        return None
    return _transport_map[protocol]


def get(name, *args, **kwargs):
    transports = {cls.name: cls for cls in get_subclasses(Transport)}
    if not name in transports:
        raise UnknownTransport()
    return transports[name](*args, **kwargs)


class Transport:
    name = ''

    def __init__(self, data_handler):
        self.data_handler = data_handler
        add_transport(self, data_handler)

    def fd(self) -> int:
        pass

    def open(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def is_readable(self) -> bool:
        pass

    def is_writeable(self) -> bool:
        pass

    def is_listening(self) -> bool:
        pass

    def handle_connected(self):
        pass

    def handle_incoming_connection(self):
        pass

    def handle_read(self):
        pass

    def handle_write(self):
        pass

    def handle_close(self):
        pass

    def handle_error(self):
        pass


class TCPTransport(Transport):
    name = 'tcp'

    def __init__(self, host, port, data_handler):
        super().__init__(data_handler)
        self.host = host
        self.port = port
        self.sock = None
        self.idata = None
        self.odata = None
        self.server = False

    def is_readable(self) -> bool:
        return not self.server

    def handle_close(self):
        reactor.remove_transport(self)
        self.sock.close()
        self.data_handler.connection_closed()

    def handle_error(self):
        super().handle_error()

    def fd(self):
        return self.sock.fileno()

    def is_listening(self) -> bool:
        return self.server

    def make_unblocking(self):
        self.sock.setblocking(0)
        reactor.add_transport(self)

    def make_socket(self):
        af, socktype, _, _, _ = socket.getaddrinfo(self.host, self.port,
                                                   socket.AF_UNSPEC,
                                                   socket.SOCK_STREAM)[0]
        self.sock = socket.socket(af, socktype)

    def open(self):
        self.make_socket()
        self.sock.connect((self.host, self.port))
        self.make_unblocking()

    def listen(self):
        self.server = True
        self.make_socket()
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        self.make_unblocking()

    def close(self):
        self.handle_close()

    def handle_incoming_connection(self):
        s, (host, port) = self.sock.accept()
        transport = TCPTransport(host, port, self.data_handler)
        transport.sock = s
        reactor.add_transport(transport)
        self.data_handler.connection_made(transport)

    def handle_read(self):
        data = self.sock.recv(8192)
        if data:
            self.data_handler.receive(data)

    def handle_write(self):
        if self.data_handler.has_output():
            data = self.data_handler.get_output()
            self.sock.send(data)

    def is_writeable(self) -> bool:
        return not self.server


class TFOTransport(TCPTransport):
    name = 'tfo'

    def listen(self):
        self.server = True
        self.make_socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setsockopt(socket.SOL_TCP, _TCP_FASTOPEN, _QLEN)
        self.sock.listen(1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.make_unblocking()

    def open(self, hello):
        if hello is None:
            super().open()
            return
        self.make_socket()
        self.sock.sendto(hello, _MSG_FASTOPEN, (self.host, self.port))
        self.make_unblocking()
