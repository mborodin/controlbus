import unittest
from io import BytesIO

from snet.messaging import mqtt

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
_MQTTAtMostDeliveryPublishFlow = mqtt._MQTTAtMostDeliveryPublishFlow
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
    def test_marshal_qos0(self):
        header = _MQTTHeader(_CONNACK, 2)
        bs = header.marshal()
        expected = b' \x02'
        self.assertEqual(bs, expected)

    def test_marshal_qos4(self):
        header = _MQTTHeader(_CONNACK, 2, 4)  # QoS should be trimmed to 0-3 range, thus 4 == 0
        bs = header.marshal()
        expected = b' \x02'
        self.assertEqual(bs, expected)

    def test_marshal_big_message(self):
        header = _MQTTHeader(_PUBLISH, 155, 2)
        bs = header.marshal()
        expected = b'4\x9b\x01'
        self.assertEqual(bs, expected)

    def test_umarshal_qos0(self):
        header = _MQTTHeader.unmarshal(BytesIO(b' \x02'))
        expected = _MQTTHeader(_CONNACK, 2)
        self.assertEqual(header.type, expected.type)
        self.assertEqual(header.qos, expected.qos)
        self.assertEqual(header.dup, expected.dup)
        self.assertEqual(header.retain, expected.retain)
        self.assertEqual(header.length, expected.length)

    def test_umarshal_big_message(self):
        header = _MQTTHeader.unmarshal(BytesIO(b'4\x9b\x01'))
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
        message = _MQTTMessage.unmarshal_message(self.clean_message)
        expected = _MQTTConnect(self.client_id)
        expected.set_keepalive(self.keepalive)
        expected.clean_session()
        self.compare_messages(expected, message)

    def test_umarshal_username_password(self):
        message = _MQTTMessage.unmarshal_message(self.username_password_message)
        expected = _MQTTConnect(self.client_id)
        expected.set_keepalive(self.keepalive)
        expected.clean_session()
        expected.set_username(self.username)
        expected.set_password(self.password)
        self.compare_messages(expected, message)

    def test_umarshal_username(self):
        message = _MQTTMessage.unmarshal_message(self.username_message)
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
        message = _MQTTMessage.unmarshal_message(self.will_message)
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
        message = _MQTTMessage.unmarshal_message(self.msg)
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
        message = _MQTTMessage.unmarshal_message(self.publish0)
        expected = _MQTTPublish(qos=0)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.message)
        self.compare_messages(message, expected)

    def test_unmarshal_qos1(self):
        message = _MQTTMessage.unmarshal_message(self.publish1)
        expected = _MQTTPublish(qos=1)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.message)
        self.compare_messages(message, expected)

    def test_unmarshal_qos2(self):
        message = _MQTTMessage.unmarshal_message(self.publish2)
        expected = _MQTTPublish(qos=2)
        expected.set_id(self.id)
        expected.set_topic(self.topic)
        expected.set_message(self.message)
        self.compare_messages(message, expected)

    def test_unmarshal_qos2_big(self):
        message = _MQTTMessage.unmarshal_message(self.publish2_big)
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


class test_MQTTPubAck(unittest.TestCase):
    def test___init__(self):
        # __mqtt_pub_ack = _MQTTPubAck()
        assert False


class test_MQTTPubRec(unittest.TestCase):
    def test___init__(self):
        # __mqtt_pub_rec = _MQTTPubRec()
        assert False


class test_MQTTPubRel(unittest.TestCase):
    def test___init__(self):
        # __mqtt_pub_rel = _MQTTPubRel(qos, dup)
        assert False


class test_MQTTPubComp(unittest.TestCase):
    def test___init__(self):
        # __mqtt_pub_comp = _MQTTPubComp()
        assert False


class test_MQTTSubscribe(unittest.TestCase):
    def setUp(self):
        self.topics = [('hello/world', 0)]
        self.msg = b'\x82\x10\x00\x01\x00\x0bhello/world\x00'
        self.id = 1
        self.qos = 1

    def test_marshal(self):
        message = _MQTTSubscribe(qos=self.qos)
        message.set_id(self.id)
        for (topic, qos) in self.topics:
            message.add_topic(topic, qos)
        bs = message.marshal()
        expected = self.msg
        self.assertEqual(bs, expected)

    def test_unmarshal(self):
        message = _MQTTMessage.unmarshal_message(self.msg)
        expected = _MQTTSubscribe(qos=self.qos)
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
        message = _MQTTMessage.unmarshal_message(self.msg)
        expected = _MQTTSubAck()
        expected.set_id(self.id)
        for qos in self.subscribed_qos:
            expected.add(qos)
        self.assertEqual(message.id, expected.id)
        for (idx, expected_qos) in enumerate(expected.qoses):
            actual_qos = message.qoses[idx]
            self.assertEqual(actual_qos, expected_qos)


class test_MQTTUnsubscribe(unittest.TestCase):
    def test_add_topic(self):
        # __mqtt_unsubscribe = _MQTTUnsubscribe(qos, dup)
        # self.assertEqual(expected, __mqtt_unsubscribe.add_topic(topic))
        assert False

    def test_marshal(self):
        # __mqtt_unsubscribe = _MQTTUnsubscribe(qos, dup)
        # self.assertEqual(expected, __mqtt_unsubscribe.marshal())
        assert False

    def test_unmarshal(self):
        # __mqtt_unsubscribe = _MQTTUnsubscribe(qos, dup)
        # self.assertEqual(expected, __mqtt_unsubscribe.unmarshal(buf))
        assert False


class test_MQTTUnsubAck(unittest.TestCase):
    def test___init__(self):
        # __mqtt_unsub_ack = _MQTTUnsubAck()
        assert False


class test_MQTTPingReq(unittest.TestCase):
    def setUp(self):
        self.msg = b'\xc0\x00'

    def test_marshal(self):
        message = _MQTTPingReq()
        bs = message.marshal()
        self.assertEqual(bs, self.msg)

    def test_unmarshal(self):
        message = _MQTTMessage.unmarshal_message(self.msg)
        expected = _MQTTPingReq()

        self.assertEqual(message.header.type, expected.header.type)


class test_MQTTPingResp(unittest.TestCase):
    def test___init__(self):
        # __mqtt_ping_resp = _MQTTPingResp()
        assert False


class test_MQTTFlow(unittest.TestCase):
    def test_get(self):
        # __mqtt_flow = _MQTTFlow(message)
        # self.assertEqual(expected, __mqtt_flow.get())
        assert False

    def test_has_next(self):
        # __mqtt_flow = _MQTTFlow(message)
        # self.assertEqual(expected, __mqtt_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_flow = _MQTTFlow(message)
        # self.assertEqual(expected, __mqtt_flow.next())
        assert False

    def test_process(self):
        # __mqtt_flow = _MQTTFlow(message)
        # self.assertEqual(expected, __mqtt_flow.process(protocol, handler))
        assert False


class test_MQTTSimplePublishFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_simple_publish_flow = _MQTTSimplePublishFlow(message)
        # self.assertEqual(expected, __mqtt_simple_publish_flow.has_next())
        assert False

    def test_process(self):
        # __mqtt_simple_publish_flow = _MQTTSimplePublishFlow(message)
        # self.assertEqual(expected, __mqtt_simple_publish_flow.process(protocol, handler))
        assert False


class test_MQTTAtLeastOncePublishFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_at_least_once_publish_flow = _MQTTAtLeastOncePublishFlow(message)
        # self.assertEqual(expected, __mqtt_at_least_once_publish_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_at_least_once_publish_flow = _MQTTAtLeastOncePublishFlow(message)
        # self.assertEqual(expected, __mqtt_at_least_once_publish_flow.next())
        assert False

    def test_process(self):
        # __mqtt_at_least_once_publish_flow = _MQTTAtLeastOncePublishFlow(message)
        # self.assertEqual(expected, __mqtt_at_least_once_publish_flow.process(protocol, handler))
        assert False


class test_MQTTAtMostDeliveryPublishFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_at_most_delivery_publish_flow = _MQTTAtMostDeliveryPublishFlow(message)
        # self.assertEqual(expected, __mqtt_at_most_delivery_publish_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_at_most_delivery_publish_flow = _MQTTAtMostDeliveryPublishFlow(message)
        # self.assertEqual(expected, __mqtt_at_most_delivery_publish_flow.next())
        assert False

    def test_process(self):
        # __mqtt_at_most_delivery_publish_flow = _MQTTAtMostDeliveryPublishFlow(message)
        # self.assertEqual(expected, __mqtt_at_most_delivery_publish_flow.process(protocol, handler))
        assert False


class test_MQTTSubscribeFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_subscribe_flow = _MQTTSubscribeFlow(message)
        # self.assertEqual(expected, __mqtt_subscribe_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_subscribe_flow = _MQTTSubscribeFlow(message)
        # self.assertEqual(expected, __mqtt_subscribe_flow.next())
        assert False

    def test_process(self):
        # __mqtt_subscribe_flow = _MQTTSubscribeFlow(message)
        # self.assertEqual(expected, __mqtt_subscribe_flow.process(protocol, handler))
        assert False


class test_MQTTConnectFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_connect_flow = _MQTTConnectFlow(message)
        # self.assertEqual(expected, __mqtt_connect_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_connect_flow = _MQTTConnectFlow(message)
        # self.assertEqual(expected, __mqtt_connect_flow.next())
        assert False

    def test_process(self):
        # __mqtt_connect_flow = _MQTTConnectFlow(message)
        # self.assertEqual(expected, __mqtt_connect_flow.process(protocol, handler))
        assert False


class test_MQTTDisconnectFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_disconnect_flow = _MQTTDisconnectFlow(message)
        # self.assertEqual(expected, __mqtt_disconnect_flow.has_next())
        assert False

    def test_process(self):
        # __mqtt_disconnect_flow = _MQTTDisconnectFlow(message)
        # self.assertEqual(expected, __mqtt_disconnect_flow.process(protocol, handler))
        assert False


class test_MQTTUnsubscribeFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_unsubscribe_flow = _MQTTUnsubscribeFlow(message)
        # self.assertEqual(expected, __mqtt_unsubscribe_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_unsubscribe_flow = _MQTTUnsubscribeFlow(message)
        # self.assertEqual(expected, __mqtt_unsubscribe_flow.next())
        assert False

    def test_process(self):
        # __mqtt_unsubscribe_flow = _MQTTUnsubscribeFlow(message)
        # self.assertEqual(expected, __mqtt_unsubscribe_flow.process(protocol, handler))
        assert False


class test_MQTTPingFlow(unittest.TestCase):
    def test_has_next(self):
        # __mqtt_ping_flow = _MQTTPingFlow(message)
        # self.assertEqual(expected, __mqtt_ping_flow.has_next())
        assert False

    def test_next(self):
        # __mqtt_ping_flow = _MQTTPingFlow(message)
        # self.assertEqual(expected, __mqtt_ping_flow.next())
        assert False

    def test_process(self):
        # __mqtt_ping_flow = _MQTTPingFlow(message)
        # self.assertEqual(expected, __mqtt_ping_flow.process(protocol, handler))
        assert False


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
