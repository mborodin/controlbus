import unittest
from io import BytesIO
import mock

from snet.messaging import mqtt
from snet.messaging.mqtt import _MQTTPingResp
from snet.utils import LeasedRoundRobin, flatten

_CONNACK = mqtt._CONNACK
_CONNACK_ACCEPTED = mqtt._CONNACK_ACCEPTED
_CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD = mqtt._CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD
_CONNACK_REFUSED_IDENTIFIER_REJECTED = mqtt._CONNACK_REFUSED_IDENTIFIER_REJECTED
_CONNACK_REFUSED_NOT_AUTHORIZED = mqtt._CONNACK_REFUSED_NOT_AUTHORIZED
_CONNACK_REFUSED_PROTOCOL_VERSION = mqtt._CONNACK_REFUSED_PROTOCOL_VERSION
_CONNACK_REFUSED_SERVER_UNAVAILABLE = mqtt._CONNACK_REFUSED_SERVER_UNAVAILABLE
_CONNACK_STRERR = mqtt._CONNACK_STRERR
_CONNECT = mqtt._CONNECT
_DISCONNECT = mqtt._DISCONNECT
_MQTTAtLeastOncePublishFlow = mqtt._MQTTAtLeastOncePublishFlow
_MQTTExactlyDeliveryPublishFlow = mqtt._MQTTExactlyDeliveryPublishFlow
_MQTTConnAck = mqtt._MQTTConnAck
_MQTTConnect = mqtt._MQTTConnect
_MQTTConnectFlow = mqtt._MQTTConnectFlow
_MQTTDisconnect = mqtt._MQTTDisconnect
_MQTTDisconnectFlow = mqtt._MQTTDisconnectFlow
_MQTTFlow = mqtt._MQTTFlow
_MQTTHeader = mqtt._MQTTHeader
_MQTTMessage = mqtt._MQTTMessage
_MQTTMessageWithID = mqtt._MQTTMessageWithID
_MQTTPingFlow = mqtt._MQTTPingFlow
_MQTTPingReq = mqtt._MQTTPingReq
_MQTTPingResp = mqtt._MQTTPingResp
_MQTTPubAck = mqtt._MQTTPubAck
_MQTTPubComp = mqtt._MQTTPubComp
_MQTTPubRec = mqtt._MQTTPubRec
_MQTTPubRel = mqtt._MQTTPubRel
_MQTTPublish = mqtt._MQTTPublish
_MQTTSimplePublishFlow = mqtt._MQTTSimplePublishFlow
_MQTTSubAck = mqtt._MQTTSubAck
_MQTTSubscribe = mqtt._MQTTSubscribe
_MQTTSubscribeFlow = mqtt._MQTTSubscribeFlow
_MQTTUnsubAck = mqtt._MQTTUnsubAck
_MQTTUnsubscribe = mqtt._MQTTUnsubscribe
_MQTTUnsubscribeFlow = mqtt._MQTTUnsubscribeFlow
_PINGREQ = mqtt._PINGREQ
_PINGRESP = mqtt._PINGRESP
_PUBACK = mqtt._PUBACK
_PUBCOMP = mqtt._PUBCOMP
_PUBLISH = mqtt._PUBLISH
_PUBREC = mqtt._PUBREC
_PUBREL = mqtt._PUBREL
_SUBACK = mqtt._SUBACK
_SUBSCRIBE = mqtt._SUBSCRIBE
_UNSUBACK = mqtt._UNSUBACK
_UNSUBSCRIBE = mqtt._UNSUBSCRIBE


class test_MQTTHeader(unittest.TestCase):
    def setUp(self):
        self.msg_empty = b'\xc0\x00'
        self.msg = b' \x02'
        self.big_msg = b'4\x9b\x01'

    def test_marshal_empty(self):
        message = _MQTTPingReq()
        bs = message.marshal()
        self.assertEqual(bs, self.msg_empty)

    def test_unmarshal_empty(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.msg_empty)
        expected = _MQTTPingReq()

        self.assertEqual(message.header.type, expected.header.type)

    def test_marshal_qos0(self):
        header = _MQTTHeader(_CONNACK, 2)
        bs = header.marshal()
        expected = self.msg
        self.assertEqual(bs, expected)

    def test_marshal_qos4(self):
        header = _MQTTHeader(_CONNACK, 2, 4)  # QoS should be trimmed to 0-3 range, thus 4 == 0
        bs = header.marshal()
        expected = self.msg
        self.assertEqual(bs, expected)

    def test_marshal_big_message(self):
        header = _MQTTHeader(_PUBLISH, 155, 2)
        bs = header.marshal()
        expected = self.big_msg
        self.assertEqual(bs, expected)

    def test_umarshal_qos0(self):
        header = _MQTTHeader.unmarshal(BytesIO(self.msg))
        expected = _MQTTHeader(_CONNACK, 2)
        self.assertEqual(header.type, expected.type)
        self.assertEqual(header.qos, expected.qos)
        self.assertEqual(header.dup, expected.dup)
        self.assertEqual(header.retain, expected.retain)
        self.assertEqual(header.length, expected.length)

    def test_umarshal_big_message(self):
        header = _MQTTHeader.unmarshal(BytesIO(self.big_msg))
        expected = _MQTTHeader(_PUBLISH, 155, 2)
        self.assertEqual(header.type, expected.type)
        self.assertEqual(header.qos, expected.qos)
        self.assertEqual(header.dup, expected.dup)
        self.assertEqual(header.retain, expected.retain)
        self.assertEqual(header.length, expected.length)


class test_MQTTConnect(unittest.TestCase):
    def setUp(self):
        self.client_id = 'snet/publisher'
        self.username = 'test'
        self.password = 'asdfghjklqw'
        self.keepalive = 60
        self.qos = 2
        self.message = self.client_id
        self.topic = 'disconnect'
        self.will_message = b'\x108\x00\x06MQIsdp\x03\x16\x00<\x00\x0esnet/publisher\x00\ndisconnect\x00\x0esnet/publisher'
        self.username_message = b'\x10"\x00\x06MQIsdp\x03\x82\x00<\x00\x0esnet/publisher\x00\x04test'
        self.username_password_message = b'\x10/\x00\x06MQIsdp\x03\xc2\x00<\x00\x0esnet/publisher\x00\x04test\x00\x0basdfghjklqw'
        self.clean_message = b'\x10\x1c\x00\x06MQIsdp\x03\x02\x00<\x00\x0esnet/publisher'

    def test_marshal_clean(self):
        message = _MQTTConnect(self.client_id)
        message.set_keepalive(self.keepalive)
        message.clean_session()
        bs = message.marshal()
        expected = self.clean_message
        self.assertEqual(bs, expected)

    def test_marshal_username_password(self):
        message = _MQTTConnect(self.client_id)
        message.set_keepalive(self.keepalive)
        message.clean_session()
        message.set_username(self.username)
        message.set_password(self.password)
        bs = message.marshal()
        expected = self.username_password_message
        self.assertEqual(bs, expected)

    def test_marshal_username(self):
        message = _MQTTConnect(self.client_id)
        message.set_keepalive(self.keepalive)
        message.clean_session()
        message.set_username(self.username)
        bs = message.marshal()
        expected = self.username_message
        self.assertEqual(bs, expected)

    def test_marshal_will(self):
        message = _MQTTConnect(self.client_id)
        message.set_keepalive(self.keepalive)
        message.clean_session()
        message.will_qos(self.qos)
        message.will_message(self.topic, self.message)
        bs = message.marshal()
        expected = self.will_message
        self.assertEqual(bs, expected)

    def test_umarshal_clean(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.clean_message)
        expected = _MQTTConnect(self.client_id)
        expected.set_keepalive(self.keepalive)
        expected.clean_session()
        self.compare_messages(expected, message)

    def test_umarshal_username_password(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.username_password_message)
        expected = _MQTTConnect(self.client_id)
        expected.set_keepalive(self.keepalive)
        expected.clean_session()
        expected.set_username(self.username)
        expected.set_password(self.password)
        self.compare_messages(expected, message)

    def test_umarshal_username(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.username_message)
        expected = _MQTTConnect(self.client_id)
        expected.set_keepalive(self.keepalive)
        expected.clean_session()
        expected.set_username(self.username)
        self.compare_messages(expected, message)

    def compare_messages(self, expected, message):
        self.assertEqual(message.magic, expected.magic)
        self.assertEqual(message.version, expected.version)
        self.assertEqual(message.get_will_retain(), expected.get_will_retain())
        self.assertEqual(message.get_will_qos(), expected.get_will_qos())
        (expected_topic, expected_message) = expected.get_will_message()
        (actual_topic, actual_message) = message.get_will_message()
        self.assertEqual(actual_topic, expected_topic)
        self.assertEqual(actual_message, expected_message)
        self.assertEqual(message.get_username(), expected.get_username())
        self.assertEqual(message.get_password(), expected.get_password())
        self.assertEqual(message.is_clean_session(), expected.is_clean_session())
        self.assertEqual(message.get_keepalive(), expected.get_keepalive())
        self.assertEqual(message.id, expected.id)

    def test_umarshal_will(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.will_message)
        expected = _MQTTConnect(self.client_id)
        expected.set_keepalive(self.keepalive)
        expected.clean_session()
        expected.will_qos(self.qos)
        expected.will_message(self.topic, self.message)
        self.compare_messages(expected, message)


class test_MQTTConnAck(unittest.TestCase):
    def setUp(self):
        self.msg = b' \x02\x00\x00'
        self.code = _CONNACK_ACCEPTED

    def test_marshal(self):
        message = _MQTTConnAck(self.code)
        bs = message.marshal()
        expected = self.msg
        self.assertEqual(bs, expected)

    def test_unmarshal(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.msg)
        expected = _MQTTConnAck(self.code)
        self.assertEqual(message.code, expected.code)


class test_MQTTPublish(unittest.TestCase):
    def setUp(self):
        self.topic = 'hello/world'
        self.message = b'hallo'
        self.bigmessage = b'123456789012345678901234567890123456789012345678901234567890123456789012345678901234567' + \
                          b'89012345678901234567890123456789012345678901234567890'
        self.id = 1
        self.publish0 = b'0\x12\x00\x0bhello/worldhallo'
        self.publish1 = b'2\x14\x00\x0bhello/world\x00\x01hallo'
        self.publish2 = b'4\x14\x00\x0bhello/world\x00\x01hallo'
        self.publish2_big = b'4\x9b\x01\x00\x0bhello/world\x00\x011234567890123456789012345678901234567890123456789' + \
                            b'0123456789012345678901234567890123456789012345678901234567890123456789012345678901234' + \
                            b'567890'

    def test_marshal_qos0(self):
        message = _MQTTPublish(qos=0)
        message.set_topic(self.topic)
        message.set_message(self.message)
        bs = message.marshal()
        self.assertEqual(bs, self.publish0)

    def test_marshal_qos1(self):
        message = _MQTTPublish(qos=1)
        message.set_id(self.id)
        message.set_topic(self.topic)
        message.set_message(self.message)
        bs = message.marshal()
        self.assertEqual(bs, self.publish1)

    def test_marshal_qos2(self):
        message = _MQTTPublish(qos=2)
        message.set_id(self.id)
        message.set_topic(self.topic)
        message.set_message(self.message)
        bs = message.marshal()
        self.assertEqual(bs, self.publish2)

    def test_marshal_qos2_big(self):
        message = _MQTTPublish(qos=2)
        message.set_id(self.id)
        message.set_topic(self.topic)
        message.set_message(self.bigmessage)
        bs = message.marshal()
        self.assertEqual(bs, self.publish2_big)

    def test_unmarshal_qos0(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.publish0)
        expected = _MQTTPublish(qos=0)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.message)
        self.compare_messages(message, expected)

    def test_unmarshal_qos1(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.publish1)
        expected = _MQTTPublish(qos=1)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.message)
        self.compare_messages(message, expected)

    def test_unmarshal_qos2(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.publish2)
        expected = _MQTTPublish(qos=2)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.message)
        self.compare_messages(message, expected)

    def test_unmarshal_qos2_big(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.publish2_big)
        expected = _MQTTPublish(qos=2)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.bigmessage)
        self.compare_messages(message, expected)

    def compare_messages(self, actual, expected):
        """
        @type actual _MQTTPublish
        @type expected _MQTTPublish
        """
        if expected.header.qos > 0:
            self.assertEqual(actual.id, expected.id)

        self.assertEqual(actual.topic, expected.topic)
        self.assertEqual(actual.message, expected.message)


class test_MQTTSubscribe(unittest.TestCase):
    def setUp(self):
        self.topics = [('hello/world', 0)]
        self.msg = b'\x82\x10\x00\x01\x00\x0bhello/world\x00'
        self.id = 1

    def test_marshal(self):
        message = _MQTTSubscribe()
        message.set_id(self.id)
        for (topic, qos) in self.topics:
            message.add_topic(topic, qos)
        bs = message.marshal()
        expected = self.msg
        self.assertEqual(bs, expected)

    def test_unmarshal(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.msg)
        expected = _MQTTSubscribe()
        expected.set_id(self.id)
        for (expected_topic, expected_qos) in self.topics:
            expected.add_topic(expected_topic, expected_qos)
        self.assertEqual(message.id, expected.id)
        for (idx, (expected_topic, expected_qos)) in enumerate(expected.topics):
            (actual_topic, actual_qos) = message.topics[idx]
            self.assertEqual(actual_topic, expected_topic)
            self.assertEqual(actual_qos, expected_qos)


class test_MQTTSubAck(unittest.TestCase):
    def setUp(self):
        self.id = 1
        self.subscribed_qos = [0]
        self.msg = b'\x90\x03\x00\x01\x00'

    def test_marshal(self):
        message = _MQTTSubAck()
        message.set_id(self.id)
        for qos in self.subscribed_qos:
            message.add(qos)
        bs = message.marshal()
        expected = self.msg
        self.assertEqual(bs, expected)

    def test_unmarshal(self):
        (message, remaining) = _MQTTMessage.unmarshal_message(self.msg)
        expected = _MQTTSubAck()
        expected.set_id(self.id)
        for qos in self.subscribed_qos:
            expected.add(qos)
        self.assertEqual(message.id, expected.id)
        for (idx, expected_qos) in enumerate(expected.qoses):
            actual_qos = message.qoses[idx]
            self.assertEqual(actual_qos, expected_qos)


class test_MQTTPublish(unittest.TestCase):
    def setUp(self):
        self.message = _MQTTPublish()
        self.payload = b'hello'

    def test_set_message_ok(self):
        try:
            self.message.set_message(self.payload)
        except Exception as e:
            self.fail('No exception was expected but {0} is raised'.format(e))

    def test_set_message_none_fail(self):
        self.assertRaises(ValueError, self.message.set_message, None)

    def test_set_message_empty_fail(self):
        self.assertRaises(ValueError, self.message.set_message, b'')

    def test_set_message_non_bytes_fail(self):
        self.assertRaises(ValueError, self.message.set_message, 'hello')


#class test_MQTTUnsubscribe(unittest.TestCase):
#    def test_add_topic(self):
#        # __mqtt_unsubscribe = _MQTTUnsubscribe(qos, dup)
#        # self.assertEqual(expected, __mqtt_unsubscribe.add_topic(topic))
#        assert False
#
#    def test_marshal(self):
#        # __mqtt_unsubscribe = _MQTTUnsubscribe(qos, dup)
#        # self.assertEqual(expected, __mqtt_unsubscribe.marshal())
#        assert False
#
#    def test_unmarshal(self):
#        # __mqtt_unsubscribe = _MQTTUnsubscribe(qos, dup)
#        # self.assertEqual(expected, __mqtt_unsubscribe.unmarshal(buf))
#        assert False


class test_MQTTFlow(unittest.TestCase):
    def test_get_connect_connect(self):
        flow = _MQTTFlow.get(_MQTTConnect())
        self.assertIsInstance(flow, _MQTTConnectFlow)

    def test_get_connect_connack(self):
        flow = _MQTTFlow.get(_MQTTConnAck())
        self.assertIsInstance(flow, _MQTTConnectFlow)

    def test_get_subscribe_subscribe(self):
        message = _MQTTSubscribe()
        message.set_id(1)
        flow = _MQTTFlow.get(message)
        self.assertIsInstance(flow, _MQTTSubscribeFlow)

    def test_get_subscribe_suback(self):
        flow = _MQTTFlow.get(_MQTTSubAck())
        self.assertIsInstance(flow, _MQTTSubscribeFlow)

    def test_get_ping_pingreq(self):
        flow = _MQTTFlow.get(_MQTTPingReq())
        self.assertIsInstance(flow, _MQTTPingFlow)

    def test_get_ping_pingresp(self):
        flow = _MQTTFlow.get(_MQTTPingResp())
        self.assertIsInstance(flow, _MQTTPingFlow)

    def test_get_disconnect(self):
        flow = _MQTTFlow.get(_MQTTDisconnect())
        self.assertIsInstance(flow, _MQTTDisconnectFlow)

    def test_get_simple_publish(self):
        flow = _MQTTFlow.get(_MQTTPublish(qos=0))
        self.assertIsInstance(flow, _MQTTSimplePublishFlow)

    def test_get_atleastonce_publish(self):
        flow = _MQTTFlow.get(_MQTTPublish(qos=1))
        self.assertIsInstance(flow, _MQTTAtLeastOncePublishFlow)

    def test_get_atleastonce_puback(self):
        flow = _MQTTFlow.get(_MQTTPubAck())
        self.assertIsInstance(flow, _MQTTAtLeastOncePublishFlow)

    def test_get_exactly_publish(self):
        flow = _MQTTFlow.get(_MQTTPublish(qos=2))
        self.assertIsInstance(flow, _MQTTExactlyDeliveryPublishFlow)

    def test_get_exactly_pubrec(self):
        flow = _MQTTFlow.get(_MQTTPubRec())
        self.assertIsInstance(flow, _MQTTExactlyDeliveryPublishFlow)

    def test_get_exactly_pubrel(self):
        flow = _MQTTFlow.get(_MQTTPubRel(qos=2))
        self.assertIsInstance(flow, _MQTTExactlyDeliveryPublishFlow)

    def test_get_exactly_pubcomp(self):
        flow = _MQTTFlow.get(_MQTTPubComp())
        self.assertIsInstance(flow, _MQTTExactlyDeliveryPublishFlow)

    def test_get_unsubscribe_unsubscribe(self):
        flow = _MQTTFlow.get(_MQTTUnsubscribe())
        self.assertIsInstance(flow, _MQTTUnsubscribeFlow)

    def test_get_unsubscribe_unsuback(self):
        flow = _MQTTFlow.get(_MQTTUnsubAck())
        self.assertIsInstance(flow, _MQTTUnsubscribeFlow)


class SimpleProtocol(object):
    def __init__(self, iid=None):
        self.iid = iid
        self.processing = {}
        self.retry_timeout = 60
        self.ping_sent = None
        self.message_id_generator = LeasedRoundRobin(range(0, 0xFFFF))
        self.connected = None
        self.keepalive = None

    def resend(self, mid):
        pass


def validate_call(case, mock_method, method_name, eargs, ekwargs):
    mname, args, kwargs = mock_method
    case.assertEqual(mname, method_name)

    for idx in range(0, len(args)):
        case.assertEqual(args[idx], eargs[idx])
    for arg in kwargs:
        case.assertEqual(kwargs[arg], ekwargs[arg])

    case.assertLessEqual(len(args) + len(kwargs), len(eargs))


class test_MQTTSimplePublishFlow(unittest.TestCase):

    def setUp(self):
        self.topic = 'test/unittest'
        self.message = b'execute'
        message = _MQTTPublish(qos=0)
        message.set_topic(self.topic)
        message.set_message(self.message)
        self.flow = _MQTTFlow.get(message)

    def test_has_next(self):
        self.assertFalse(self.flow.has_next())

    def test_next(self):
        self.flow.process(SimpleProtocol(None), mqtt.MQTTEventHandler())
        self.assertIsNone(self.flow.next())

    def test_process(self):
        handler = mock.Mock(spec=mqtt.MQTTEventHandler)
        iid = SimpleProtocol('snet/client-1')

        self.flow.process(iid, handler)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (iid.iid, self.topic, self.message)
        ekwargs = {'client_id': iid.iid,
                   'topic': self.topic,
                   'message': self.message}
        validate_call(self, handler.method_calls[0], 'publish', eargs, ekwargs)


class test_MQTTAtLeastOncePublishFlow(unittest.TestCase):
    def setUp(self):
        self.topic = 'test/unittest'
        self.message = b'execute'
        self.id = 1
        self.iid = 'snet/client-1'
        message = _MQTTPublish(qos=1)
        message.set_id(self.id)
        message.set_topic(self.topic)
        message.set_message(self.message)
        self.flow_publish = _MQTTFlow.get(message)
        message = _MQTTPubAck()
        message.set_id(self.id)
        self.flow_puback = _MQTTFlow.get(message)

    def test_has_next_publish(self):
        self.assertTrue(self.flow_publish.has_next())

    def test_has_next_puback(self):
        self.assertFalse(self.flow_puback.has_next())

    def test_process_publish(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()
        handler.publish.return_vallue = []

        self.flow_publish.process(protocol, handler)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (protocol.iid, self.topic, self.message)
        ekwargs = {'client_id': protocol.iid,
                   'topic': self.topic,
                   'message': self.message}
        validate_call(self, handler.method_calls[0], 'publish', eargs, ekwargs)

    def test_process_publish(self):
        protocol = SimpleProtocol(self.iid)
        protocol.processing[self.id] = None
        handler = mock.Mock()

        self.flow_puback.process(protocol, handler)

        self.assertEqual(len(handler.method_calls), 0)

    def test_next_publish(self):
        self.flow_publish.process(SimpleProtocol(None), mqtt.MQTTEventHandler())
        self.assertEqual(self.flow_publish.next().id, self.id)

    def test_next_puback(self):
        protocol = SimpleProtocol(None)
        protocol.processing[self.id] = None
        self.flow_puback.process(protocol, mqtt.MQTTEventHandler())
        self.assertIsNone(self.flow_puback.next())


class test_MQTTExactlyDeliveryPublishFlow(unittest.TestCase):
    def setUp(self):
        self.topic = 'test/unittest'
        self.message = b'execute'
        self.id = 1
        message = _MQTTPublish(qos=2)
        message.set_id(1)
        message.set_topic(self.topic)
        message.set_message(self.message)
        self.flow_publish = _MQTTFlow.get(message)

        message = _MQTTPubRec()
        message.set_id(1)
        self.flow_pubrec = _MQTTFlow.get(message)

        message = _MQTTPubRel(qos=1)
        message.set_id(1)
        self.flow_pubrel = _MQTTFlow.get(message)

        message = _MQTTPubComp()
        message.set_id(1)
        self.flow_pubcomp = _MQTTFlow.get(message)

        self.protocol = SimpleProtocol('snet/client-1')
        self.handler = mqtt.MQTTEventHandler()

    def test_has_next_publish(self):
        self.assertTrue(self.flow_publish.has_next())

    def test_has_next_pubrec(self):
        self.assertTrue(self.flow_pubrec.has_next())

    def test_has_next_pubrel(self):
        self.assertTrue(self.flow_pubrel.has_next())

    def test_has_next_pubcomp(self):
        self.assertFalse(self.flow_pubcomp.has_next())

    def test_next_publish(self):
        self.flow_publish.process(self.protocol, self.handler)
        message = self.flow_publish.next()
        self.assertIsInstance(message, _MQTTPubRec)
        self.assertEqual(message.id, self.id)

    def test_next_pubrec(self):
        self.flow_pubrec.process(self.protocol, self.handler)
        message = self.flow_pubrec.next()
        self.assertIsInstance(message, _MQTTPubRel)
        self.assertEqual(message.id, self.id)

    def test_next_pubrel(self):
        self.protocol.processing[self.id] = None
        self.flow_pubrel.process(self.protocol, self.handler)
        message = self.flow_pubrel.next()
        self.assertIsInstance(message, _MQTTPubComp)
        self.assertEqual(message.id, self.id)

    def test_next_pubcomp(self):
        self.protocol.processing[self.id] = None
        self.flow_pubcomp.process(self.protocol, self.handler)
        self.assertIsNone(self.flow_pubcomp.next())

    def test_process_publish(self):
        handler = mock.Mock(spec=mqtt.MQTTEventHandler)

        watchdog_mock = mock.Mock()
        with mock.patch('snet.utils.watchdog.add', watchdog_mock):
            self.flow_publish.process(self.protocol, handler)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.protocol.iid, self.topic, self.message)
        ekwargs = {'client_id': self.protocol.iid,
                   'topic': self.topic,
                   'message': self.message}
        validate_call(self, handler.method_calls[0], 'publish', eargs, ekwargs)

        self.assertEqual(len(watchdog_mock.mock_calls), 1)

        expected_grace = 0.0
        eargs = (self.id, self.protocol.retry_timeout, self.protocol.resend, expected_grace)
        ekwargs = {'uid': self.id,
                   'timeout': self.protocol.retry_timeout,
                   'callback': self.protocol.resend,
                   'grace': expected_grace}
        validate_call(self, watchdog_mock.mock_calls[0], '', eargs, ekwargs)

    def test_process_pubrec(self):
        handler = mock.Mock(spec=mqtt.MQTTEventHandler)

        watchdog_mock = mock.Mock()
        with mock.patch('snet.utils.watchdog.touch', watchdog_mock):
            self.flow_pubrec.process(self.protocol, handler)

        self.assertEqual(len(handler.method_calls), 0)

        self.assertEqual(len(watchdog_mock.mock_calls), 1)

        eargs = (self.id,)
        ekwargs = {'uid': self.id}
        validate_call(self, watchdog_mock.mock_calls[0], '', eargs, ekwargs)

    def test_process_pubrel(self):
        handler = mock.Mock(spec=mqtt.MQTTEventHandler)

        self.protocol.processing[self.id] = None

        watchdog_mock = mock.Mock()
        with mock.patch('snet.utils.watchdog.remove', watchdog_mock):
            self.flow_pubrel.process(self.protocol, handler)

        self.assertEqual(len(handler.method_calls), 0)

        self.assertEqual(len(watchdog_mock.mock_calls), 1)

        eargs = (self.id,)
        ekwargs = {'uid': self.id}
        validate_call(self, watchdog_mock.mock_calls[0], '', eargs, ekwargs)

    def test_process_pubcomp(self):
        handler = mock.Mock(spec=mqtt.MQTTEventHandler)

        self.protocol.processing[self.id] = None

        watchdog_mock = mock.Mock()
        with mock.patch('snet.utils.watchdog.remove', watchdog_mock):
            self.flow_pubcomp.process(self.protocol, handler)

        self.assertEqual(len(handler.method_calls), 0)

        self.assertEqual(len(watchdog_mock.mock_calls), 1)

        eargs = (self.id,)
        ekwargs = {'uid': self.id}
        validate_call(self, watchdog_mock.mock_calls[0], '', eargs, ekwargs)


class test_MQTTSubscribeFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.iid = 'snet/client-1'
        cls.topics = [('test/topic0', 0),
                      ('test/topic1', 1),
                      ('test/topic2', 2)]
        cls.granted_qos = [0, 1, 2]
        cls.partial_granted_qos = ((0, 1), (2,))
        cls.msg_id = 1

    def setUp(self):
        message = _MQTTSubscribe()
        message.set_id(self.msg_id)
        [message.add_topic(x[0], x[1]) for x in self.topics]
        self.flow_subscribe = _MQTTFlow.get(message)

        message = _MQTTSubAck()
        message.set_id(self.msg_id)
        [message.add(x) for x in self.granted_qos]
        self.flow_suback = _MQTTFlow.get(message)

    def test_has_next_subscribe(self):
        self.assertTrue(self.flow_subscribe.has_next())

    def test_has_next_suback(self):
        self.assertFalse(self.flow_suback.has_next())

    def test_flow_subscribe(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()
        handler.subscribe.return_value = self.granted_qos

        self.flow_subscribe.process(protocol, handler)
        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid, self.topics)
        ekwargs = {'client_id': self.iid,
                   'topics': self.topics}
        validate_call(self, handler.method_calls[0], 'subscribe', eargs, ekwargs)

        message = self.flow_subscribe.next()

        self.assertIsInstance(message, _MQTTSubAck)
        self.assertEqual(message.id, self.msg_id)
        self.assertEqual(message.qoses, self.granted_qos)

    def test_flow_suback(self):
        protocol = SimpleProtocol(self.iid)
        protocol.processing[self.msg_id] = (len(self.granted_qos), None)
        handler = mock.Mock()

        self.flow_suback.process(protocol, handler)
        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid, self.granted_qos)
        ekwargs = {'client_id': self.iid,
                   'topics': self.granted_qos}
        validate_call(self, handler.method_calls[0], 'subscribed', eargs, ekwargs)

        message = self.flow_suback.next()

        self.assertIsNone(message)

    def test_flow_suback_partial(self):
        partial = flatten(list(self.partial_granted_qos))
        protocol = SimpleProtocol(self.iid)
        protocol.processing[self.msg_id] = (len(self.granted_qos), None)
        handler = mock.Mock()

        idx = 1
        c = len(self.partial_granted_qos)
        for qoses in self.partial_granted_qos:
            self.flow_suback.message.qoses = []
            for qos in qoses:
                self.flow_suback.message.add(qos)
            self.flow_suback.process(protocol, handler)
            self.assertEqual(len(handler.method_calls), 1 if idx == c else 0)
            idx += 1

        eargs = (self.iid, partial)
        ekwargs = {'client_id': self.iid,
                   'qoses': partial}
        validate_call(self, handler.method_calls[0], 'subscribed', eargs, ekwargs)

        message = self.flow_suback.next()

        self.assertIsNone(message)


class test_MQTTConnectFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.code = _CONNACK_ACCEPTED
        cls.err_code = _CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD
        cls.iid = 'snet/client-1'
        cls.username = 'testuser'
        cls.password = 'testpassword'
        cls.topic = 'disconnected'
        cls.message = cls.iid.encode('ascii')
        cls.qos = 2
        cls.retain = True
        cls.clean = True
        cls.keepalive = 120

    def setUp(self):
        message = _MQTTConnect(self.iid)
        message.set_keepalive(self.keepalive)
        message.set_username(self.username)
        message.set_password(self.password)
        if self.clean:
            message.clean_session()
        message.will_qos(self.qos)
        message.will_message(self.topic, self.message)
        if self.retain:
            message.will_retain()
        self.flow_connect = _MQTTFlow.get(message)

        message = _MQTTConnAck(self.code)
        self.flow_connack = _MQTTFlow.get(message)

    def test_has_next_connect(self):
        self.assertTrue(self.flow_connect.has_next())

    def test_has_next_connack(self):
        self.assertFalse(self.flow_connack.has_next())

    def test_flow_connect_ok(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()
        handler.connect.return_value = True

        will = (self.topic, self.message, self.qos, self.retain)

        self.flow_connect.process(protocol, handler)

        self.assertTrue(protocol.connected)
        self.assertEqual(protocol.keepalive, self.keepalive)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid, protocol, self.username, self.password, self.clean, will)
        ekwargs = {'client_id': self.iid,
                   'protocol': protocol,
                   'username': self.username,
                   'password': self.password,
                   'is_clean': self.clean,
                   'will': will}
        validate_call(self, handler.method_calls[0], 'connect', eargs, ekwargs)

        message = self.flow_connect.next()

        self.assertIsInstance(message, _MQTTConnAck)
        self.assertEqual(message.code, self.code)

    def test_flow_connect_bad_version_fail(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()

        self.flow_connect.message.version = -1  # Set definitely wrong protocol version

        self.flow_connect.process(protocol, handler)

        self.assertFalse(protocol.connected)
        self.assertIsNone(protocol.keepalive)

        self.assertEqual(len(handler.method_calls), 0)

        message = self.flow_connect.next()

        self.assertIsInstance(message, _MQTTConnAck)
        self.assertEqual(message.code, _CONNACK_REFUSED_PROTOCOL_VERSION)

    def test_flow_connect_bad_username_or_password_fail(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()
        handler.connect.return_value = False

        will = (self.topic, self.message, self.qos, self.retain)

        self.flow_connect.process(protocol, handler)

        self.assertFalse(protocol.connected)
        self.assertIsNone(protocol.keepalive)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid, protocol, self.username, self.password, self.clean, will)
        ekwargs = {'client_id': self.iid,
                   'protocol': protocol,
                   'username': self.username,
                   'password': self.password,
                   'is_clean': self.clean,
                   'will': will}
        validate_call(self, handler.method_calls[0], 'connect', eargs, ekwargs)

        message = self.flow_connect.next()

        self.assertIsInstance(message, _MQTTConnAck)
        self.assertEqual(message.code, _CONNACK_REFUSED_BAD_USERNAME_OR_PASSWORD)

    def test_flow_connack_ok(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()

        self.flow_connack.process(protocol, handler)

        self.assertTrue(protocol.connected)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid,)
        ekwargs = {'client_id': self.iid}
        validate_call(self, handler.method_calls[0], 'connected', eargs, ekwargs)

        self.assertIsNone(self.flow_connack.next())

    def test_flow_connack_error_code_fail(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()

        self.flow_connack.message.code = self.err_code

        self.flow_connack.process(protocol, handler)

        self.assertFalse(protocol.connected)

        self.assertEqual(len(handler.method_calls), 1)

        err = (self.err_code, _CONNACK_STRERR[self.err_code])

        eargs = (self.iid, err)
        ekwargs = {'client_id': self.iid,
                   'err': err}
        validate_call(self, handler.method_calls[0], 'error', eargs, ekwargs)

        self.assertIsNone(self.flow_connack.next())


class test_MQTTDisconnectFlow(unittest.TestCase):
    def setUp(self):
        self.flow = _MQTTFlow.get(_MQTTDisconnect())
        self.id = 'snet/client-1'

    def test_process(self):
        protocol = SimpleProtocol(self.id)
        handler = mock.Mock()

        self.flow.process(protocol, handler)

        self.assertEqual(len(handler.method_calls), 1)

        eargs = (protocol.iid,)
        ekwargs = {'client_id': protocol.iid}
        validate_call(self, handler.method_calls[0], 'disconnect', eargs, ekwargs)

    def test_has_next(self):
        self.assertFalse(self.flow.has_next())

    def test_next(self):
        self.flow.process(SimpleProtocol(self.id), mqtt.MQTTEventHandler())
        self.assertIsNone(self.flow.next())


class test_MQTTUnsubscribeFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.iid = 'snet/client-1'
        cls.topics = ['test/topic1', 'test/topic2']
        cls.msg_id = 1

    def setUp(self):
        message = _MQTTUnsubscribe()
        message.set_id(self.msg_id)
        [message.add_topic(x) for x in self.topics]
        self.flow_unsubscribe = _MQTTFlow.get(message)

        message = _MQTTUnsubAck()
        message.set_id(self.msg_id)
        self.flow_unsuback = _MQTTFlow.get(message)

    def test_has_next_unsubscribe(self):
        self.assertTrue(self.flow_unsubscribe.has_next())

    def test_has_next_unsuback(self):
        self.assertFalse(self.flow_unsuback.has_next())

    def test_flow_unsubscribe(self):
        protocol = SimpleProtocol(self.iid)
        handler = mock.Mock()

        self.flow_unsubscribe.process(protocol, handler)
        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid, self.topics)
        ekwargs = {'client_id': self.iid,
                   'topics': self.topics}
        validate_call(self, handler.method_calls[0], 'unsubscribe', eargs, ekwargs)

        message = self.flow_unsubscribe.next()

        self.assertIsInstance(message, _MQTTUnsubAck)
        self.assertEqual(message.id, self.msg_id)

    def test_process(self):
        protocol = SimpleProtocol(self.iid)
        protocol.processing[self.msg_id] = None
        handler = mock.Mock()

        self.flow_unsuback.process(protocol, handler)
        self.assertEqual(len(handler.method_calls), 1)

        eargs = (self.iid,)
        ekwargs = {'client_id': self.iid}
        validate_call(self, handler.method_calls[0], 'unsubscribed', eargs, ekwargs)

        message = self.flow_unsuback.next()

        self.assertIsNone(message)


class test_MQTTPingFlow(unittest.TestCase):
    def setUp(self):
        self.flow_pingreq = _MQTTFlow.get(_MQTTPingReq())
        self.flow_pingresp = _MQTTFlow.get(_MQTTPingResp())

    def test_has_next_pingreq(self):
        self.assertTrue(self.flow_pingreq.has_next())

    def test_has_next_pingresp(self):
        self.assertFalse(self.flow_pingresp.has_next())

    def test_next_pingreq(self):
        self.flow_pingreq.process(None, None)
        self.assertIsInstance(self.flow_pingreq.next(), _MQTTPingResp)

    def test_process_pingresp(self):
        protocol = SimpleProtocol(None)
        self.flow_pingreq.process(protocol, None)
        self.assertTrue(protocol.ping_sent)

    def test_process_pingresp(self):
        self.flow_pingreq.process(None, None)


class TestMQTTProtocol(unittest.TestCase):
    def test_close(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.close())
        assert False

    def test_close_client(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.close_client(cid))
        assert False

    def test_connection_closed(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.connection_closed())
        assert False

    def test_connection_exception(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.connection_exception(exc))
        assert False

    def test_connection_made(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.connection_made(t))
        assert False

    def test_get_output(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.get_output())
        assert False

    def test_get_qos_level(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.get_qos_level())
        assert False

    def test_has_output(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.has_output())
        assert False

    def test_open(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.open(is_server))
        assert False

    def test_ping(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.ping())
        assert False

    def test_publish(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.publish(topic, data, qos))
        assert False

    def test_receive(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.receive(data))
        assert False

    def test_request_ping(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.request_ping(iid))
        assert False

    def test_resend(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.resend(mid))
        assert False

    def test_send(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.send(message))
        assert False

    def test_subscribe(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.subscribe(topics, qos))
        assert False

    def test_unsubscribe(self):
        # m_qtt_protocol = MQTTProtocol(addr, port, handler, iid, proto)
        # self.assertEqual(expected, m_qtt_protocol.unsubscribe(topics, qos))
        assert False


if __name__ == '__main__':
    unittest.main()
