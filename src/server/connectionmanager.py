class ConnectionAddError(Exception):
    pass


class ConnectionManager():
    TYPE_UNKNOWN = 0
    TYPE_SERVER = 1
    TYPE_CLIENT = 2

    def __init__(self, max_connections, conn_type):
        self.max_connections = max_connections
        self.type = conn_type  # receives one of the values defined in class variables
        # Same index in these three list means that the values belong to same connection
        self.sockets = []  # Socket objects
        self.heartbleed_status = []  # Integer telling how many HEART\n messages have not been answered with BLEED\n
                                     # message. Negative value means that an answer has been received during that cycle
        self.listen_addrs = []  # A tuple with ip/dns as string and port as integer

    def add(self, sock, listen_addr=None):
        if len(self.sockets) < self.max_connections:
            if sock not in self.sockets:
                self.sockets.append(sock)
                self.heartbleed_status.append(-1)
                self.listen_addrs.append(listen_addr)
            else:
                raise ConnectionAddError("Socket is already added.")
        else:
            raise ConnectionAddError("Server can't handle more connections.")

    def remove(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            self.pop(conn_index)
        # Socket not in self.sockets. No need to do anything special.
        except ValueError:
            return

    def pop(self, i):
        try:
            sock = self.sockets.pop(i)
            status = self.heartbleed_status.pop(i)
            addr = self.listen_addrs.pop(i)
            return (sock, status, addr)
        except IndexError:
            return None

    def set_heartbleed_received(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            self.heartbleed_status[conn_index] = -1
        except ValueError:
            return

    # Returns listen_address of socket. Raises ValueError if socket not self.sockets
    def get_socket_listen_addr(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            return self.listen_addrs[conn_index]
        # Socket not in self.sockets. No need to do anything special.
        except ValueError:
            raise