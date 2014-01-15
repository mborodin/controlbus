try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import struct
from io import BytesIO

from snet.nio.protocols import BaseProtocol
from snet.nio import transport
from snet.utils import LeasedRoundRobin, get_subclasses, watchdog


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

_CONNACK_STRERR = {
    _CONNACK_REFUSED_PROTOCOL_VERSION: 'Invalid protocol version',
    _CONNACK_REFUSED_IDENTIFIER_REJECTED: 'Client ID rejected',
    _CONNACK_REFUSED_SERVER_UNAVAILABLE: 'Server unavailable',
    _CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD: 'Bad username or password',
    _CONNACK_REFUSED_NOT_AUTHORIZED: 'Not authorized'
}


class InvalidMessageIdException(Exception):
    pass


def _marshal_string(val):
    strlen = len(val)
    buf = struct.pack('!H', strlen)
    if strlen == 0:
        return buf
    fmt = '%is' % strlen
    buf += struct.pack(fmt, val.encode('ascii', 'replace'))
    return buf


def _unmarshal_string(buf):
    strlen = struct.unpack('!H', buf.read(2))[0]
    if strlen == 0:
        return ''
    fmt = '%is' % strlen
    return struct.unpack(fmt, buf.read(strlen))[0].decode('UTF-8')


def _marshal_data(val):
    blen = len(val)
    if blen == 0:
        return b''
    fmt = '%ip' % blen
    buf = struct.pack(fmt, val)
    return buf


def _unmarshal_data(buf):
    return struct.unpack('p', buf.read())[0]


class _MQTTHeader:
    def __init__(self, msgtype, length=0, qos=0, dup=False, retain=False):
        self.type = msgtype
        self.dup = dup
        self.qos = qos
        self.retain = retain
        self.length = length

    def marshal(self):
        packed = b''
        header = (self.type << 4) | (8 if self.dup else 0) | ((0x3 & self.qos) << 1) | (1 if self.retain else 0)
        packed += struct.pack('B', header)  # bytes(chr(header), 'ascii')
        length = self.length
        if length == 0:
            packed += b'\x00'
        else:
            while length > 0:
                digit = length % 128
                length >>= 7
                if length > 0:
                    digit |= 0x80
                packed += struct.pack('B', digit)  # bytes(chr(digit), 'ascii')

        return packed

    @staticmethod
    def unmarshal(buf):
        header = struct.unpack('B', buf.read(1))[0]
        msgtype = (0xf0 & header) >> 4
        qos = (0x06 & header) >> 1
        dup = True if (0x08 & header) != 0 else False
        retain = True if (0x01 & header) != 0 else False
        multiplier = 0
        length = 0
        while True:
            digit = struct.unpack('B', buf.read(1))[0]
            length += (digit & 127) << multiplier
            multiplier += 7
            if (digit & 128) == 0:
                break
        return _MQTTHeader(msgtype, length, qos, dup, retain)


class _MQTTMessage(object):
    def __init__(self, msgtype, qos=0, dup=False, retain=False):
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
            elif ftype == 'p':
                buf += val
            else:
                buf += struct.pack('!' + ftype, val)
        return buf

    def unmarshal_fields(self, fields, buf):
        for (field, ftype) in fields:
            if ftype == 's':
                self.__dict__[field] = _unmarshal_string(buf)
                continue
            elif ftype == 'p':
                self.__dict__[field] = buf.read()
                break  # pointer type consumes all available data
            bsc = struct.calcsize(ftype)
            self.__dict__[field] = struct.unpack('!' + ftype, buf.read(bsc))[0]

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
        msgbuf = BytesIO(bufio.read(header.length))
        message.unmarshal(msgbuf)
        remaining = bufio.read()
        return message, remaining


class _MQTTConnect(_MQTTMessage):
    _USERNAME_BIT = 128
    _PASSWORD_BIT = 64
    _WILL_RETAIN_BIT = 32
    _WILL_QOS = 3  # Shift, not bits
    _WILL_FLAG_BIT = 4
    _CLEAN_SESSION_BIT = 2

    def __init__(self, cid=None):
        super(_MQTTConnect, self).__init__(_CONNECT)
        self.magic = 'MQIsdp'
        self.version = 3
        self.flags = 0
        self.keepalive = 60
        self.varheader = (('magic', 's'),
                          ('version', 'B'),
                          ('flags', 'B'),
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

    def get_username(self):
        return None if (self.flags & _MQTTConnect._USERNAME_BIT == 0) else self.username

    def set_password(self, password):
        self.flags |= _MQTTConnect._PASSWORD_BIT
        self.password = password

    def get_password(self):
        return None if (self.flags & _MQTTConnect._PASSWORD_BIT == 0) else self.password

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

    def get_keepalive(self):
        return self.keepalive

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

    def get_will_qos(self):
        return (self.flags >> _MQTTConnect._WILL_QOS) & 0x3

    def will_retain(self):
        """
        The Will Retain flag indicates whether the server should retain the Will message which is
        published by the server on behalf of the client in the event that the client is
        disconnected unexpectedly.
        """
        self.flags |= _MQTTConnect._WILL_RETAIN_BIT

    def get_will_retain(self):
        return self.flags & _MQTTConnect._WILL_RETAIN_BIT != 0

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
        @type msg bytes
        """
        self.flags |= _MQTTConnect._WILL_FLAG_BIT
        self.message = msg
        self.topic = topic

    def get_will_message(self):
        return (None, None) if (self.flags & _MQTTConnect._WILL_FLAG_BIT) == 0 else (self.topic, self.message)

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

    def is_clean_session(self):
        return (self.flags & _MQTTConnect._CLEAN_SESSION_BIT) != 0

    def marshal(self):
        self.payload = (('id', 's'),)
        if self.flags & _MQTTConnect._WILL_FLAG_BIT != 0:
            self.payload += (('topic', 's'), ('message', 's'),)
        if self.flags & _MQTTConnect._USERNAME_BIT != 0:
            self.payload += (('username', 's'),)
        if self.flags & _MQTTConnect._PASSWORD_BIT != 0:
            self.payload += (('password', 's'),)
        return super(_MQTTConnect, self).marshal()

    def unmarshal(self, buf):
        super(_MQTTConnect, self).unmarshal(buf)
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
        super(_MQTTConnAck, self).__init__(_CONNACK)
        self.reserved = 0
        self.code = code
        self.varheader = (('reserved', 'B'),
                          ('code', 'B'))


class _MQTTMessageWithID(_MQTTMessage):
    def __init__(self, msgtype, qos=0, dup=False, retain=False):
        super(_MQTTMessageWithID, self).__init__(msgtype, qos, dup, retain)
        self.id = None
        if qos > 0 or msgtype == _SUBSCRIBE or msgtype == _SUBACK or msgtype == _PUBREC \
            or msgtype == _PUBREL or msgtype == _PUBCOMP:
            self.varheader = (('id', 'H'),)

    def unmarshal(self, buf):
        if self.header.qos > 0 \
            or self.header.type == _SUBSCRIBE \
            or self.header.type == _SUBACK \
            or self.header.type == _PUBREC \
            or self.header.type == _PUBREL \
            or self.header.type == _PUBCOMP:
            t = ('id', 'H')
            if not t in self.varheader:
                self.varheader += (t,)
        super(_MQTTMessageWithID, self).unmarshal(buf)

    def want_id(self):
        return self.qos > 0

    def set_id(self, mid=None):
        self.id = mid


class _MQTTPublish(_MQTTMessageWithID):
    def __init__(self, qos=0, dup=False, retain=False):
        super(_MQTTPublish, self).__init__(_PUBLISH, qos, dup, retain)
        self.varheader = (('topic', 's'),) + self.varheader

        self.message = b''
        self.topic = None

    def set_topic(self, topic):
        self.topic = topic

    def get_topic(self):
        return self.topic

    def set_message(self, message):
        if message is None or not isinstance(message, bytes) or message == b'':
            raise ValueError
        self.payload = (('message', 'p'),)
        self.message = message

    def get_message(self):
        return self.message

    def unmarshal(self, buf):
        super(_MQTTPublish, self).unmarshal(buf)
        if buf.readable() > 0:
            self.payload = (('message', 'p'),)
            self.unmarshal_fields(self.payload, buf)


class _MQTTPubAck(_MQTTMessageWithID):
    def __init__(self):
        super(_MQTTPubAck, self).__init__(_PUBACK)


class _MQTTPubRec(_MQTTMessageWithID):
    def __init__(self):
        super(_MQTTPubRec, self).__init__(_PUBREC)


class _MQTTPubRel(_MQTTMessageWithID):
    def __init__(self, qos=1, dup=False):
        super(_MQTTPubRel, self).__init__(_PUBREL, qos, dup)


class _MQTTPubComp(_MQTTMessageWithID):
    def __init__(self):
        super(_MQTTPubComp, self).__init__(_PUBCOMP)


class _MQTTSubscribe(_MQTTMessageWithID):
    def __init__(self, dup=False):
        super(_MQTTSubscribe, self).__init__(_SUBSCRIBE, 1, dup)
        self.topics = []

    def marshal(self):
        for (tid, (topic, qos)) in enumerate(self.topics):
            topicf = 'topic%i' % tid
            qosf = 'qos%i' % tid
            setattr(self, topicf, topic)
            setattr(self, qosf, qos)
            self.payload += ((topicf, 's'), (qosf, 'B'),)
        return super(_MQTTSubscribe, self).marshal()

    def unmarshal(self, buf):
        super(_MQTTSubscribe, self).unmarshal(buf)
        while self.header.length - buf.tell() > 0:
            topic = _unmarshal_string(buf)
            qos = struct.unpack('B', buf.read(1))[0]
            self.add_topic(topic, qos)

    def add_topic(self, topic, qos):
        self.topics.append((topic, qos))


class _MQTTSubAck(_MQTTMessageWithID):
    def __init__(self):
        super(_MQTTSubAck, self).__init__(_SUBACK)
        self.qoses = []

    def add(self, qos):
        self.qoses.append(qos)

    def marshal(self):
        for (tid, qos) in enumerate(self.qoses):
            qosf = 'qos%i' % tid
            setattr(self, qosf, qos)
            self.payload += ((qosf, 'B'),)
        return super(_MQTTSubAck, self).marshal()

    def unmarshal(self, buf):
        super(_MQTTSubAck, self).unmarshal(buf)
        while buf.readable():
            b = buf.read(1)
            if b == b'':
                break
            qos = struct.unpack('B', b)[0]
            self.add(qos)


class _MQTTUnsubscribe(_MQTTMessageWithID):
    def __init__(self, dup=False):
        super(_MQTTUnsubscribe, self).__init__(_UNSUBSCRIBE, 1, dup)
        self.topics = []

    def marshal(self):
        buf = super(_MQTTUnsubscribe, self).marshal()
        for topic in self.topics:
            buf += _marshal_string(topic)
        return buf

    def unmarshal(self, buf):
        super(_MQTTUnsubscribe, self).unmarshal(buf)
        while self.header.length - buf.tell() > 0:
            self.add_topic(_unmarshal_string(buf))

    def add_topic(self, topic):
        self.topics.append(topic)


class _MQTTUnsubAck(_MQTTMessageWithID):
    def __init__(self):
        super(_MQTTUnsubAck, self).__init__(_UNSUBACK)


class _MQTTPingReq(_MQTTMessage):
    def __init__(self):
        super(_MQTTPingReq, self).__init__(_PINGREQ)


class _MQTTPingResp(_MQTTMessage):
    def __init__(self):
        super(_MQTTPingResp, self).__init__(_PINGRESP)


class _MQTTDisconnect(_MQTTMessage):
    def __init__(self):
        super(_MQTTDisconnect, self).__init__(_DISCONNECT)


class _MQTTFlow(object):
    messages = []
    ignore_qos = []
    qos = [0, 1, 2]

    @staticmethod
    def get(message):
        """
        @type message _MQTTMessage
        @param message:
        @return: _MQTTFlow
        """
        cls = [i for i in get_subclasses(_MQTTFlow) if
               not (not (message.header.type in i.messages) or (not (message.header.qos in i.qos)
                                                                and not (message.header.type in i.ignore_qos)))][0]
        return cls(message)

    def __init__(self, message):
        self.message = message

    def has_next(self):
        pass

    def next(self):
        pass

    def process(self, protocol=None, handler=None):
        pass


class _MQTTSimplePublishFlow(_MQTTFlow):
    messages = [_PUBLISH]
    qos = [0]

    def __init__(self, message):
        super(_MQTTSimplePublishFlow, self).__init__(message)

    def has_next(self):
        return False

    def process(self, protocol=None, handler=None):
        handler.publish(protocol.iid, self.message.get_topic(), self.message.get_message())


class _MQTTAtLeastOncePublishFlow(_MQTTFlow):
    messages = [_PUBLISH, _PUBACK]
    ignore_qos = [_PUBACK]
    qos = [1]

    def __init__(self, message):
        super(_MQTTAtLeastOncePublishFlow, self).__init__(message)
        self.rmessage = None

    def process(self, protocol=None, handler=None):
        message = self.message
        mtype = message.header.type
        if mtype == _PUBLISH:
            protocol.message_id_generator.lease(message.id)
            handler.publish(protocol.iid, self.message.get_topic(), self.message.get_message())
            self.rmessage = _MQTTPubAck()
            self.rmessage.id = message.id
        else:
            watchdog.remove(message.id)
            protocol.processing.pop(message.id)

    def has_next(self):
        return self.message.header.type == _PUBLISH

    def next(self):
        return self.rmessage


class _MQTTExactlyDeliveryPublishFlow(_MQTTFlow):
    messages = [_PUBLISH, _PUBREC, _PUBREL, _PUBCOMP]
    ignore_qos = [_PUBREC, _PUBREL, _PUBCOMP]
    qos = [2]

    def __init__(self, message):
        super(_MQTTExactlyDeliveryPublishFlow, self).__init__(message)
        self.rmessage = None

    def process(self, protocol=None, handler=None):
        message = self.message
        mtype = message.header.type
        if mtype == _PUBLISH:
            protocol.message_id_generator.lease(message.id)
            handler.publish(protocol.iid, self.message.get_topic(), self.message.get_message())
            self.rmessage = _MQTTPubRec()
            self.rmessage.set_id(message.id)
            watchdog.add(message.id, protocol.retry_timeout, protocol.resend)
            protocol.processing[message.id] = self.rmessage
        elif mtype == _PUBREC:
            protocol.message_id_generator.lease(message.id)
            self.rmessage = _MQTTPubRel()
            self.rmessage.set_id(message.id)
            #watchdog.add(message.id, protocol.retry_timeout, protocol.resend)
            watchdog.touch(message.id)
            protocol.processing[message.id] = self.rmessage
        else:
            if mtype == _PUBREL:
                self.rmessage = _MQTTPubComp()
                self.rmessage.set_id(message.id)
            watchdog.remove(message.id)
            protocol.processing.pop(message.id)

    def has_next(self):
        return self.message.header.type == _PUBLISH or self.message.header.type == _PUBREC \
            or self.message.header.type == _PUBREL

    def next(self):
        return self.rmessage


class _MQTTSubscribeFlow(_MQTTFlow):
    messages = [_SUBSCRIBE, _SUBACK]

    def __init__(self, message):
        super(_MQTTSubscribeFlow, self).__init__(message)
        self.rmessage = None

    def process(self, protocol=None, handler=None):
        message = self.message
        mtype = message.header.type
        if mtype == _SUBSCRIBE:
            rep = handler.subscribe(protocol.iid, self.message.topics)
            protocol.message_id_generator.lease(message.id)
            self.rmessage = _MQTTSubAck()
            self.rmessage.set_id(message.id)
            [self.rmessage.add(x) for x in rep]
            protocol.processing[id] = self.rmessage
        else:
            val = protocol.processing[message.id]
            num = val[0]
            if isinstance(val[1], list):
                qoses = val[1]
            else:
                qoses = []
                protocol.processing[message.id] = (num, qoses)
            for qos in message.qoses:
                qoses.append(qos)
            if len(qoses) == num:
                watchdog.remove(message.id)
                protocol.processing.pop(message.id)
                handler.subscribed(protocol.iid, qoses)
            else:
                watchdog.touch(message.id)

    def has_next(self):
        return self.message.header.type == _SUBSCRIBE

    def next(self):
        return self.rmessage


class _MQTTConnectFlow(_MQTTFlow):
    messages = [_CONNECT, _CONNACK]

    def __init__(self, message):
        super(_MQTTConnectFlow, self).__init__(message)
        self.rmessage = None

    def process(self, protocol=None, handler=None):
        message = self.message
        mtype = message.header.type
        if mtype == _CONNECT:
            self.rmessage = _MQTTConnAck(_CONNACK_REFUSED_PROTOCOL_VERSION)
            if message.version == 3:
                iid = message.id
                protocol.iid = iid
                user = message.get_username()
                password = message.get_password()
                is_clean = message.is_clean_session()
                will = message.get_will_message() + (message.get_will_qos(), message.get_will_retain())
                protocol.connected = handler.connect(iid, protocol, user, password, is_clean, will)
                if not protocol.connected:
                    self.rmessage.code = _CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD
                else:
                    self.rmessage.code = _CONNACK_ACCEPTED
                    keepalive = message.get_keepalive()
                    protocol.keepalive = keepalive
        elif mtype == _CONNACK:
            if message.code == _CONNACK_ACCEPTED:
                protocol.connected = True
                handler.connected(protocol.iid)
            else:
                handler.error(protocol.iid, (message.code, _CONNACK_STRERR[message.code]))

    def has_next(self):
        return self.message.header.type == _CONNECT

    def next(self):
        return self.rmessage


class _MQTTDisconnectFlow(_MQTTFlow):
    messages = [_DISCONNECT]

    def __init__(self, message):
        super(_MQTTDisconnectFlow, self).__init__(message)

    def process(self, protocol=None, handler=None):
        handler.disconnect(protocol.iid)

    def has_next(self):
        return False


class _MQTTUnsubscribeFlow(_MQTTFlow):
    messages = [_UNSUBSCRIBE, _UNSUBACK]

    def __init__(self, message):
        super(_MQTTUnsubscribeFlow, self).__init__(message)
        self.rmessage = None

    def process(self, protocol=None, handler=None):
        message = self.message
        mtype = message.header.type
        if mtype == _UNSUBSCRIBE:
            handler.unsubscribe(protocol.iid, message.topics)
            if message.header.qos > 0:
                protocol.message_id_generator.lease(message.id)
                self.rmessage = _MQTTUnsubAck()
                self.rmessage.set_id(message.id)
                protocol.processing[message.id] = self.rmessage
        else:
            watchdog.remove(message.id)
            handler.unsubscribed(protocol.iid)
            protocol.processing.pop(message.id)

    def has_next(self):
        return self.message.header.qos > 0 and self.message.header.type == _UNSUBSCRIBE

    def next(self):
        return self.rmessage


class _MQTTPingFlow(_MQTTFlow):
    messages = [_PINGREQ, _PINGRESP]

    def __init__(self, message):
        super(_MQTTPingFlow, self).__init__(message)
        self.rmessage = None

    def process(self, protocol=None, handler=None):
        message = self.message
        mtype = message.header.type
        if mtype == _PINGREQ:
            self.rmessage = _MQTTPingResp()
        else:
            protocol.ping_sent = False

    def has_next(self):
        return self.message.header.type == _PINGREQ

    def next(self):
        return self.rmessage


class MQTTEventHandler(object):
    def connect(self, client_id, protocol, user, password, is_clean, will):
        pass

    def connected(self, client_id):
        pass

    def publish(self, client_id, topic, message):
        pass

    def subscribe(self, client_id, topics):
        pass

    def subscribed(self, client_id, qoses):
        pass

    def unsubscribe(self, client_id, topic):
        pass

    def disconnect(self, client_id):
        pass

    def connection_closed(self, client_id):
        pass

    def error(self, client_id, err):
        pass


class MQTTProtocol(BaseProtocol):
    def set_qos_level(self, level=None):
        self.qos = 0 if level is None else level

    def connection_made(self, t):
        client = MQTTProtocol()
        client.transport = t
        t.data_handler = client
        self.clients.append(client)

    def __init__(self, addr=None, port=None, handler=None, iid=None, want_clean=False, keepalive=60, proto='tcp'):
        self.qos = 0
        self.handler = handler
        self.iid = iid
        if not addr is None:
            self.transport = transport.get(proto, addr, port, self)
        else:
            self.transport = None
        self.clients = []
        self.is_server = False
        self.drop = False
        self.output = Queue()
        self.connected = False
        self.message_id_generator = LeasedRoundRobin(range(0, 0xFFFF))
        self.processing = {}
        self.held = {}
        self.ping_sent = False
        self.retry_timeout = 10.0
        self.keepalive = keepalive
        self.want_clean = want_clean

    def set_retry_timeout(self, retry_timeout):
        self.retry_timeout = retry_timeout

    def close_client(self, cid):
        idx = self.clients.index(cid)
        client = self.clients.pop(idx)
        client.transport.close()

    def get_qos_level(self):
        return self.qos

    def has_output(self):
        return not self.output.empty()

    def connection_exception(self, exc):
        self.handler.error(self.iid, exc)

    def receive(self, data):
        if not self.drop:
            while data != b'':
                (message, remaining) = _MQTTMessage.unmarshal_message(data)
                flow = _MQTTFlow.get(message)
                flow.process(self, self.handler)
                watchdog.touch(self.iid)
                if flow.has_next():
                    self.send(flow.next())
                elif isinstance(message, _MQTTMessageWithID):  # aka has_next = False && instance_check
                    mid = message.id
                    self.message_id_generator.release(mid)
                data = remaining

    def get_output(self):
        message = self.output.get()
        self.output.task_done()
        return message.marshal()

    def open(self, is_server=False):
        self.is_server = is_server
        if not is_server:
            watchdog.add(self.iid, self.keepalive, self.request_ping, 0.1)
            message = _MQTTConnect(self.iid)
            message.set_keepalive(self.keepalive)
            if self.want_clean:
                message.clean_session()
            self.output.put(message)
            self.transport.open()
        else:
            self.transport.listen()

    def close(self):
        if not self.is_server:
            self.drop = True
            with self.output.mutex:
                self.output.queue.clear()
            message = _MQTTDisconnect()
            self.output.put(message)
            self.output.join()
        else:
            for client in self.clients:
                watchdog.remove(client.iid)
                client.transport.close()
        for mid in self.processing:
            watchdog.remove(mid)
        self.transport.close()

    def connection_closed(self):
        watchdog.remove(self.iid)
        self.handler.connection_closed(self.iid)

    def send(self, message):
        if self.connected and not self.drop:
            if isinstance(message, _MQTTMessageWithID) and message.id is None:
                id = self.message_id_generator.next()
                message.set_id(id)
            self.output.put(message)

    def resend(self, mid):
        val = self.processing[mid]
        if not isinstance(val, tuple):  # Handle special case: subscribe message
            message = val
        elif isinstance(val[1], _MQTTSubscribe):
            message = val[1]
        else:  # If we are receiving SubAcks's - we can only wait
            return
        message.dup()
        self.send(message)
        watchdog.touch(mid)

    def subscribe(self, topics, qos=None):
        message = _MQTTSubscribe(qos=qos)
        for topic in topics:
            message.add_topic(topic[0], topic[1])
        self.send(message)
        self.processing[message.id] = (len(message.topics), message)
        watchdog.add(message.id, self.retry_timeout, self.resend)

    def publish(self, topic, data, qos=None):
        message = _MQTTPublish(qos=qos)
        message.set_topic(topic)
        message.set_message(data)
        self.send(message)
        if qos > 0:
            self.processing[message.id] = message
            watchdog.add(message.id, self.retry_timeout, self.resend)

    def unsubscribe(self, topics, qos=None):
        message = _MQTTUnsubscribe(qos=qos)
        map(message.add_topic, topics)
        self.send(message)
        if qos > 0:
            self.processing[message.id] = message
            watchdog.add(message.id, self.retry_timeout, self.resend)

    def ping(self):
        if not self.ping_sent:
            message = _MQTTPingReq()
            self.send(message)
        else:
            raise RuntimeError('Ping in progress')

    def request_ping(self, iid):
        client = self if iid == self.iid else self.clients[self.clients.index(iid)]
        try:
            client.ping()
            watchdog.touch(iid)
        except RuntimeError:
            watchdog.remove(iid)
            self.handler.connection_closed(iid)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.iid == other
        if isinstance(other, MQTTProtocol):
            return self.iid == other.iid

    def __hash__(self):
        return hash(self.iid)
