class FakeUser:
    @property
    def id(self):
        return -1

    @property
    def name(self):
        return 'fake'

    def key(self):
        return 'fake key'

    def client_data(self):
        return None

    def json_data(self):
        return 'null'

