from . import BaseProtocol
from ..utils import flatten
from builtins import staticmethod
import struct
from io import BytesIO


_CONNECT = 1
_CONNACK = 2
_PUBLISH = 3
_PUBACK = 4
_PUBREC = 5
_PUBREL = 6
_PUBCOMP = 7
_SUBSCRIBE = 8
_SUBACK = 9
_UNSUBSCRIBE = 10
_UNSUBACK = 11
_PINGREQ = 12
_PINGRESP = 13
_DISCONNECT = 14

_CONNACK_ACCEPTED = 0
_CONNACK_REFUSED_PROTOCOL_VERSION = 1
_CONNACK_REFUSED_IDENTIFIER_REJECTED = 2
_CONNACK_REFUSED_SERVER_UNAVAILABLE = 3
_CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD = 4
_CONNACK_REFUSED_NOT_AUTHORIZED = 5


class InvalidMessageIdException(Exception): pass


#def _find_all(s, ss):
#    idx = s.find(ss)
#    while idx != -1:
#        yield idx
#        idx = s.find(ss, idx+1)
#
#
#def _marshal_string(str):
#    pass
#
#
#def _tuple_fmt(tup, fmt):
#    newfmt = fmt[1:]
#    strings = [i for i in range(len(tup)) if isinstance(tup[i], str)]
#    if len(strings) > 0:
#        newfmt = newfmt.replace('s', 'H%is') % tuple([len(tup[i]) for i in strings])
#    return struct.pack(newfmt, tup)
#
#
#def _marshal_list(list, fmt):
#    pass
#
#
#def _marshal_value(val, fmt):
#    """
#    @param val:
#    @param fmt:
#     @type fmt str
#    @return:
#    """
#    if fmt == 's':
#        strlen = len(val)
#        buf = struct.pack('!H', strlen)
#        if strlen == 0:
#            continue
#        fmt = '%is' % strlen
#        buf += struct.pack(fmt, val.encode('ascii', 'replace'))
#        return buf
#    elif fmt.startswith('l'):
#        for v in val:
#            buf +=
#    elif fmt.startswith('t'):
#        newfmt = fmt[1:]
#        strings = [i for i in range(len(val)) if isinstance(val[i], str)]
#        if len(strings) > 0:
#            newfmt = newfmt.replace('s', 'H%is') % tuple([len(val[i]) for i in strings])
#            newval = list(val)
#            for i in strings:
#                newval.insert(i, len(val[i]))
#            newval = tuple(newval)
#        buf = struct.pack(newfmt, *newval)
#    else:
#        buf = struct.pack('!' + fmt, val)
#
#    return buf

def _marshal_string(val):
    strlen = len(val)
    buf = struct.pack('!H', strlen)
    if strlen == 0:
        return buf
    fmt = '%is' % strlen
    buf += struct.pack(fmt, val.encode('ascii', 'replace'))
    return buf


def _unmarshal_string(buf):
    strlen = struct.unpack('!H', buf.read(2))
    if strlen == 0:
        return ''
    fmt = '%is' % strlen
    return struct.unpack(fmt, buf.read(strlen))


class _MQTTHeader:
    def __init__(self, msgtype, length=0, qos=0, dup=False, retain=False):
        self.type = msgtype
        self.dup = dup
        self.qos = qos
        self.retain = retain
        self.length = length

    def marshal(self):
        packed = b''
        header = (self.type << 4) | (8 if self.dup else 0) \
                 | ((0x3 & self.qos) << 1) | (1 if self.retain else 0)
        packed += bytes(chr(header), 'ascii')
        length = self.length
        while length > 0:
            digit = length % 128
            length >>= 7
            if length > 0:
                digit |= 0x80
            packed += bytes(chr(digit), 'ascii')

        return packed

    @staticmethod
    def unmarshal(buf):
        header = buf.read(1)
        msgtype = (0xf0 & header) >> 4
        qos = (0x06 & header) >> 1
        dup = True if (0x08 & header) != 0 else False
        retain = True if (0x01 & header) != 0 else False
        multiplier = 7
        length = 0
        while True:
            digit = buf.read(1)
            length += (digit & 127) << multiplier
            multiplier += 7
            if (digit & 128) == 0:
                break
        return _MQTTHeader(msgtype, length, qos, dup, retain)


class _MQTTMessage:
    def __init__(self, msgtype, qos, dup, retain=False):
        self.header = _MQTTHeader(msgtype, 0, qos, dup, retain)
        self.varheader = ()
        self.payload = ()

    def retain(self):
        self.header.retain = True

    def dup(self):
        self.header.dup = True

    def marshal_fields(self, fields):
        buf = b''
        for (field, ftype) in fields:
            val = self.__dict__[field]
            if ftype == 's':
                buf += _marshal_string(val)
            else:
                buf += struct.pack('!' + ftype, val)
        return buf

    def unmarshal_fields(self, fields, buf):
        for (field, ftype) in fields:
            if ftype == 's':
                self.__dict__[field] = _unmarshal_string(buf)
                continue
            bsc = struct.calcsize(ftype)
            self.__dict__[field] = struct.upack('!' + ftype, buf.read(bsc))

    def marshal(self):
        buf = self.marshal_fields(self.varheader)
        buf += self.marshal_fields(self.payload)
        self.header.length = len(buf)
        packet = self.header.marshal()
        packet += buf
        return packet

    def unmarshal(self, buf):
        self.unmarshal_fields(self.varheader, buf)
        self.unmarshal_fields(self.payload, buf)

    @staticmethod
    def unmarshal_message(buf):
        bufio = BytesIO(buf)
        header = _MQTTHeader.unmarshal(bufio)
        m = [None,
             _MQTTConnect,
             _MQTTConnAck,
             _MQTTPublish,
             _MQTTPubAck,
             _MQTTPubRec,
             _MQTTPubRel,
             _MQTTPubComp,
             _MQTTSubscribe,
             _MQTTSubAck,
             _MQTTUnsubscribe,
             _MQTTUnsubAck,
             _MQTTPingReq,
             _MQTTPingResp,
             _MQTTDisconnect]
        message = m[header.type]()
        message.header = header
        message.unmarshal(bufio)
        return message


class _MQTTConnect(_MQTTMessage):
    _USERNAME_BIT = 128
    _PASSWORD_BIT = 64
    _WILL_RETAIN_BIT = 32
    _WILL_QOS = 3  # Shift, not bits
    _WILL_FLAG_BIT = 4
    _CLEAN_SESSION_BIT = 2

    def __init__(self, cid=None):
        super().__init__(_CONNECT)
        self.magic = 'MQIsdp'
        self.version = 3
        self.flags = 0
        self.keepalive = 60
        self.varheader = (('magic', 's'),
                          ('version', 'b'),
                          ('flags', 'b'),
                          ('keepalive', 'H'))

        self.id = cid
        self.username = ''
        self.password = ''
        self.topic = ''
        self.message = ''

    def set_username(self, username):
        """
        @todo Check if username is empty
        @param username: username
        @type username: str
        """
        self.flags |= _MQTTConnect._USERNAME_BIT
        self.username = username

    def set_password(self, password):
        self.flags |= 64
        self.password = password

    def set_keepalive(self, keepalive):
        """
        The Keep Alive timer, measured in seconds, defines the maximum time interval between
        messages received from a client. It enables the server to detect that the network
        connection to a client has dropped, without having to wait for the long TCP/IP timeout.
        The client has a responsibility to send a message within each Keep Alive time period. In
        the absence of a data-related message during the time period, the client sends a
        PINGREQ message, which the server acknowledges with a PINGRESP message.
        If the server does not receive a message from the client within one and a half times the
        Keep Alive time period (the client is allowed "grace" of half a time period), it disconnects
        the client as if the client had sent a DISCONNECT message. This action does not impact
        any of the client's subscriptions. See DISCONNECT for more details.
        If a client does not receive a PINGRESP message within a Keep Alive time period after
        sending a PINGREQ, it should close the TCP/IP socket connection.
        The Keep Alive timer is a 16-bit value that represents the number of seconds for the
        time period. The actual value is application-specific, but a typical value is a few minutes.
        The maximum value is approximately 18 hours. A value of zero (0) means the client is
        not disconnected.

        @param keepalive: Keep alive value in seconds
        @type keepalive int
        """
        self.keepalive = keepalive

    def will_qos(self, qos):
        """
        A connecting client specifies the QoS level in the Will QoS field for a Will message that is
        sent in the event that the client is disconnected involuntarily. The Will message is
        defined in the payload of a CONNECT message.
        If the Will flag is set, the Will QoS field is mandatory, otherwise its value is disregarded.

        @param qos: QoS for will message
        @type qos int
        """
        self.flags |= (qos & 3) << _MQTTConnect._WILL_QOS

    def will_retain(self):
        """
        The Will Retain flag indicates whether the server should retain the Will message which is
        published by the server on behalf of the client in the event that the client is
        disconnected unexpectedly.
        """
        self.flags |= _MQTTConnect._WILL_RETAIN_BIT

    def will_message(self, topic, msg):
        """
        The Will message defines that a message is published on behalf of the client by the
        server when either an I/O error is encountered by the server during communication
        with the client, or the client fails to communicate within the Keep Alive timer schedule.
        Sending a Will message is not triggered by the server receiving a DISCONNECT
        message from the client.
        If the Will flag is set, the Will QoS and Will Retain fields must be present in the Connect
        flags byte, and the Will Topic and Will Message fields must be present in the payload.

        @param msg: message to publish on communication failure
        @type msg str
        """
        self.flags |= _MQTTConnect._WILL_FLAG_BIT
        self.message = msg
        self.topic = topic

    def clean_session(self):
        """
        If not set (0), then the server must store the subscriptions of the client after it
        disconnects. This includes continuing to store QoS 1 and QoS 2 messages for the
        subscribed topics so that they can be delivered when the client reconnects. The server
        must also maintain the state of in-flight messages being delivered at the point the
        connection is lost. This information must be kept until the client reconnects.
        If set (1), then the server must discard any previously maintained information about the
        client and treat the connection as "clean". The server must also discard any state when
        the client disconnects.
        """
        self.flags |= _MQTTConnect._CLEAN_SESSION_BIT

    def marshal(self):
        self.payload = (('id', 's'),)
        if self.flags & _MQTTConnect._WILL_FLAG_BIT != 0:
            self.payload += (('topic', 's'), ('message', 's'),)
        if self.flags & _MQTTConnect._USERNAME_BIT != 0:
            self.payload += (('username', 's'),)
        if self.flags & _MQTTConnect._PASSWORD_BIT != 0:
            self.payload += (('password', 's'),)
        return super().marshal()

    def unmarshal(self, buf):
        super().unmarshal(buf)
        self.payload = (('id', 's'),)
        if self.flags & _MQTTConnect._WILL_FLAG_BIT != 0:
            self.payload += (('topic', 's'), ('message', 's'),)
        if self.flags & _MQTTConnect._USERNAME_BIT != 0:
            self.payload += (('username', 's'),)
        if self.flags & _MQTTConnect._PASSWORD_BIT != 0:
            self.payload += (('password', 's'),)

        self.unmarshal_fields(self.payload, buf)


class _MQTTConnAck(_MQTTMessage):
    def __init__(self, code=None):
        super().__init__(_CONNACK)
        self.reserved = 0
        self.code = code
        self.varheader(('reserved', 'b'),
                       ('code', 'b'))


class _MQTTPublish(_MQTTMessage):
    def __init__(self, topic, qos, dup, mid=-1, retain=False):
        super().__init__(_PUBLISH, qos, dup, retain)
        self.topic = topic
        self.id = mid
        self.varheader = (('topic', 's'),)
        if qos > 0:
            if mid < 0:
                raise InvalidMessageIdException
            self.varheader += (('id', 'H'),)

        self.message = b''

    def set_message(self, message):
        self.payload = (('message', 'p'))
        self.message = message

    def unmarshal(self, buf):
        super().unmarshal(buf)
        if self.header.length - buf.tell() > 0:
            self.payload = (('message', 'p'))
            self.unmarshal_fields(self.payload, buf)


class _MQTTPubAck(_MQTTMessage):
    def __init__(self, mid=None):
        super().__init__(_PUBACK)
        self.id = mid
        self.varheader = (('mid', 'H'),)


class _MQTTPubRec(_MQTTMessage):
    def __init__(self, mid=None):
        super().__init__(_PUBREC)
        self.id = mid
        self.varheader = (('mid', 'H'),)


class _MQTTPubRel(_MQTTMessage):
    def __init__(self, mid=None, qos=0, dup=False):
        super().__init__(_PUBREL, qos, dup)
        self.id = mid
        self.varheader = (('mid', 'H'),)


class _MQTTPubComp(_MQTTMessage):
    def __init__(self, mid):
        super().__init__(_PUBCOMP)
        self.varheader = (('mid', 'H'),)
        self.id = mid


class _MQTTSubscribe(_MQTTMessage):
    def __init__(self, mid=None, qos=0, dup=False):
        super().__init__(_SUBSCRIBE, qos, dup)
        self.mid = mid
        self.topics = []
        self.varheader = (('mid', 'H'),)

    def marshal(self):
        buf = super().marshal()
        for (topic, qos) in self.topics:
            buf += _marshal_string(topic)
            buf += struct.pack('b', qos)
        return buf

    def unmarshal(self, buf):
        super().unmarshal(buf)
        while self.header.length - buf.tell() > 0:
            topic = _unmarshal_string(buf)
            qos = struct.unpack('b', buf.read(1))
            self.add_topic(topic, qos)

    def add_topic(self, topic, qos):
        self.topics.append((topic, qos))


class _MQTTSubAck(_MQTTMessage):
    def __init__(self, mid):
        super().__init__(_SUBACK)
        self.varheader = (('mid', 'H'),)
        self.id = mid
        self.qoses = []

    def add(self, qos):
        self.qoses.append(qos)

    def marshal(self):
        buf = super().marshal()
        for qos in self.qoses:
            buf += struct.pack('b', qos)
        return buf

    def unmarshal(self, buf):
        super().unmarshal(buf)
        while self.header.length - buf.tell() > 0:
            qos = struct.unpack('b', buf.read(1))
            self.add_topic(qos)


class _MQTTUnsubscribe(_MQTTMessage):
    def __init__(self, mid=None, qos=0, dup=False):
        super().__init__(_UNSUBSCRIBE, qos, dup)
        self.mid = mid
        self.topics = []
        self.varheader = (('mid', 'H'),)

    def marshal(self):
        buf = super().marshal()
        for topic in self.topics:
            buf += _marshal_string(topic)
        return buf

    def unmarshal(self, buf):
        super().unmarshal(buf)
        while self.header.length - buf.tell() > 0:
            self.add_topic(_unmarshal_string(buf))


    def add_topic(self, topic):
        self.topics.append(topic)


class _MQTTUnsubAck(_MQTTMessage):
    def __init__(self, mid):
        super().__init__(_UNSUBACK)
        self.varheader = (('mid', 'H'),)
        self.id = mid


class _MQTTPingReq(_MQTTMessage):
    def __init__(self):
        super().__init__(_PINGREQ)


class _MQTTPingResp(_MQTTMessage):
    def __init__(self):
        super().__init__(_PINGRESP)


class _MQTTDisconnect(_MQTTMessage):
    def __init__(self):
        super().__init__(_DISCONNECT)


class MQTTProtocol(BaseProtocol):
    def set_qos_level(self, level=None):
        self.qos = 0 if level is None else level

    def connection_made(self, transport):
        super().connection_made(transport)

    def __init__(self):
        super().__init__()
        self.qos = 0

    def get_qos_level(self):
        return self.qos

    def has_output(self):
        super().has_output()

    def connection_exception(self, exc):
        super().connection_exception(exc)

    def receive(self, data):
        super().receive(data)

    def get_output(self):
        super().get_output()

    def open(self, is_server=False):
        super().open(is_server)

    def close(self):
        super().close()

    def connection_closed(self):
        super().connection_closed()

    def send(self, data):
        super().send(data)