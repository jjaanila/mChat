class ConnectionAddError(Exception):
    pass


class ConnectionManager():
    def __init__(self, max_connections):
        self.max_connections = max_connections

        # Same index in these three list means that the values belong to same connection
        self.sockets = []  # Socket objects
        self.heartbleeds = []  # Boolean values: True means a heartbleed has been received, False means no heartbleed
        self.listen_addrs = []  # A tuple with ip/dns as string and port as integer

    def add(self, sock, listen_addr=None):
        if len(self.sockets) < self.max_connections:
            if sock not in self.sockets:
                self.sockets.append(sock)
                self.heartbleeds.append(True)
                self.listen_addrs.append(listen_addr)
            else:
                raise ConnectionAddError("Socket is already added.")
        else:
            raise ConnectionAddError("Server can't handle more connections.")

    def remove(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            self.sockets.pop(conn_index)
            self.heartbleeds.pop(conn_index)
            self.listen_addrs.pop(conn_index)

        # Socket not in self.sockets. No need to do anything special.
        except ValueError:
            return