class Protocol:
    def __init__(self):
        pass

    def open(self, is_server=False):
        pass

    def close(self):
        pass

    def send(self, data):
        pass

    def connection_made(self, transport):
        pass

    def connection_closed(self):
        pass

    def connection_exception(self, exc):
        pass

    def has_output(self):
        pass

    def get_output(self):
        pass

    def get_qos_level(self):
        pass

    def set_qos_level(self, level=None):
        pass

    def receive(self, data):
        pass
