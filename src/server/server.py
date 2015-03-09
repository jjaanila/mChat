import socket
import select
from daemon import Daemon
from channelmanager import ChannelManager
from channelmanager import ChannelJoinError


class SelectServer(Daemon):
    RECV_BUFFER = 1024
    MAX_SERVERS = 1000  # TODO: make use of this value
    MAX_CLIENTS = 10000  # TODO: limit self.connection_list with this
    MAX_CHANNELS = 30000
    MAX_CLIENTS_PER_CHANNEL = 10000  # probably good if this just equals MAX_CLIENTS

    def __init__(self, ip, port, pidfile):
        self.connection_list = []
        self.channels = ChannelManager(SelectServer.MAX_CHANNELS, SelectServer.MAX_CLIENTS_PER_CHANNEL)
        self.ip = ip
        self.port = port
        self.listen_socket = None
        super(SelectServer, self).__init__(pidfile)

    def run(self):
        running = True

        # Listen socket for accepting incoming connections
        self.listen_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind((self.ip, self.port))
        self.listen_socket.listen(128)  # parameter value = maximum number of queued connections
        self.connection_list.append(self.listen_socket)

        print("Server started on port " + str(self.port))

        while running:
            read_sockets, write_sockets, error_sockets = select.select(self.connection_list, [], [], 15)

            for sock in read_sockets:

                # New connection attempt to listen_socket
                if sock == self.listen_socket:
                    sockfd, addr = self.listen_socket.accept()
                    self.connection_list.append(sockfd)

                    # Tell about the new connection to server admin and other clients
                    print("Client connected, IP: %s, port: %s" % (addr[0], addr[1]))
                    self.broadcast_clients(str.encode("Client connected, IP: %s, port: %s\n" % (addr[0], addr[1])), [sockfd])

                # Incoming message from a client
                else:
                    try:
                        data = self.recv_until_newline(sock)
                        message = data.decode()  # decode bytes to utf-8
                        protocol_msg = message.split(" ", 3)

                        if len(protocol_msg) == 2:
                            if protocol_msg[0] == "JOIN":
                                self.channels.join(sock, protocol_msg[1])
                            elif protocol_msg[0] == "PART":
                                self.channels.part(sock, protocol_msg[1])
                            else:
                                continue  # ignore invalid message
                        elif len(protocol_msg) == 4:
                            if protocol_msg[0] == "MSG":
                                # Limit so that MSG can only be sent if joined the channel first
                                if sock in self.channels.get(protocol_msg[2]):
                                    self.broadcast_channel((message + "\n").encode(), protocol_msg[2], [sock])
                                    # TODO: send to servers in addition to clients
                            else:
                                continue  # ignore invalid message
                        else:
                            continue  # ignore invalid message

                    # Client disconnected
                    except socket.error:
                        self.close_client(sock)
                        continue
                    # Not valid unicode message, ignore the message
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        continue
                    # Unable to join a channel
                    except ChannelJoinError:
                        """
                        TODO: Here we should tell the client that joining channel was not successful.
                              The protocol doesn't support this yet, so let's just continue.
                        """
                        continue


        self.listen_socket.close()

    # Helper method for broadcasting to every other socket except sock (given as parameter)
    # and self.listen_sock
    def broadcast_clients(self, message, blacklist=None):
        self.broadcast_list(message, self.connection_list, blacklist)

    def broadcast_channel(self, message, channel, blacklist=None):
        socklist = self.channels.get(channel)
        self.broadcast_list(message, socklist, blacklist)

    def broadcast_list(self, message, socklist, blacklist=None):
        if blacklist is None:
            blacklist = []

        for recv_socket in socklist:
            if recv_socket != self.listen_socket and recv_socket not in blacklist:
                try:
                    recv_socket.send(message)
                except socket.error:
                    # Broken connection, close it
                    self.close_client(recv_socket)

    # Call recv() until newline (success) or RECV_BUFFER bytes received
    # Returns message received before newline. Does NOT return the newline character.
    # raises socket.error
    def recv_until_newline(self, sock):
        max_len = SelectServer.RECV_BUFFER
        total_data = bytearray()
        while max_len > 0:
            try:
                data = sock.recv(max_len)
            except socket.error:
                raise
            if data:
                max_len -= len(data)
                if b'\n' in data:
                    total_data.extend(data[:data.find(b'\n')])  # add + 1 to include the newline
                    break
                total_data.extend(data)
            else:
                raise socket.error
        return bytes(total_data)

    def close_client(self, client_sock):
        client_name = client_sock.getpeername()
        print("Client offline, IP: %s, port: %s" % (client_name[0], client_name[1]))
        self.broadcast_clients(str.encode("Client offline, IP: %s, port: %s\n" % (client_name[0], client_name[1])), [client_sock])

        # Part closing client from all channels
        self.channels.part_all(client_sock)

        client_sock.close()
        if client_sock in self.connection_list:
            self.connection_list.remove(client_sock)
