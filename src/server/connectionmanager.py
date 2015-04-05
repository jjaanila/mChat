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
        self.nickname = []

    def add(self, sock, listen_addr=None, nickname="NoName"):
        if len(self.sockets) < self.max_connections:
            if sock not in self.sockets:
                self.sockets.append(sock)
                self.heartbleed_status.append(-1)
                self.listen_addrs.append(listen_addr)
                self.nickname.append(nickname)
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
            nick = self.nickname.pop(i)
            return (sock, status, addr, nick)
        except IndexError:
            return None

    def set_heartbleed_received(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            self.heartbleed_status[conn_index] = -1
        except ValueError:
            raise

    # Returns listen_address of socket. Raises ValueError if socket not self.sockets
    def get_socket_listen_addr(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            return self.listen_addrs[conn_index]
        # Socket not in self.sockets. Raise error
        except ValueError:
            raise

    # Returns heartbleed_status of socket. Raises ValueError if socket not self.sockets
    def get_heartbleed_status(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            return self.heartbleed_status[conn_index]
        # Socket not in self.sockets. Raise error
        except ValueError:
            raise

    def get_nickname(self, sock):
        try:
            conn_index = self.sockets.index(sock)
            return self.nickname[conn_index]
        # Socket not in self.sockets. Raise error
        except ValueError:
            raise

    # return True if a new nickname was set (that is different from the previous nick), otherwise return False
    def set_nickname(self, sock, nickname):
        try:
            conn_index = self.sockets.index(sock)
            previous_nickname = self.nickname[conn_index]

            if previous_nickname != nickname:
                self.nickname[conn_index] = nickname
                return True
        except ValueError:
            raise
        return False