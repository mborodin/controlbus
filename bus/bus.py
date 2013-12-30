BUS_MASTER_AGENT = 0
BUS_MASTER_BROKER = 1


class BusMessage:
    pass


class Event(BusMessage):
    pass


class Bus:
    def __init__(self, master=False, kind=BUS_MASTER_AGENT):
        self.master = master
        self.kind = kind
        self.connection = None
        self.qos = None

    def acquire(self, *args, **kwargs):
        if not self.master:
            self.find_master()
        else:
            self.prepare_master(*args, **kwargs)

    def release(self):
        pass

    def find_master(self):
        pass

    def prepare_master(self, endpoints):
        pass

    def add_listener(self, listener, acceptance_callback=lambda x: True):
        pass

    def put(self, msg, destination=None, ttl=1):
        """
        @param msg Message to send
        @type msg BusMessage
        @param destination Message recipient. None == broadcast message
        @type destination str
        @param ttl TTL for message - number of brokers to pass through
        @param ttl int
        """

    def get(self, queue):
        pass

    def set_qos(self, qos=None):
        self.qos = qos

    def get_qos(self):
        return self.qos

    def marshal(self, msg):
        pass

    def unmarshal(self):
        pass