import socket
import select
from daemon import Daemon
from channelmanager import ChannelManager
from channelmanager import ChannelJoinError
from connectionmanager import ConnectionManager
from connectionmanager import ConnectionAddError
from timer import Timer


class SelectServer(Daemon):
    PROTOCOL_MSG_MAXLEN = 1024
    MAX_SERVERS = 1000
    MAX_CLIENTS = 10000
    MAX_CHANNELS = 30000
    MAX_CLIENTS_PER_CHANNEL = 10000  # probably good if this just equals MAX_CLIENTS
    HEARTBLEED_INTERVAL = 2  # seconds
    MISSING_HEARTBLEEDS_ACCEPTED = 2  # the server closes connection when MORE than this amount of heartbleed responses
                                      # are missing in a row

    def __init__(self, pidfile, ip, client_listen_port, server_listen_port, existing_server_ip=None, existing_server_port=None):
        # Servers that have been detected but not connected to yet. A list of (ip, port) tuples
        self.not_connected_servers = []
        if (existing_server_ip is not None) and (existing_server_port is not None):
            self.not_connected_servers.append((existing_server_ip, existing_server_port))

        self.servers = ConnectionManager(SelectServer.MAX_SERVERS, ConnectionManager.TYPE_SERVER)
        self.clients = ConnectionManager(SelectServer.MAX_CLIENTS, ConnectionManager.TYPE_CLIENT)
        self.channels = ChannelManager(SelectServer.MAX_CHANNELS, SelectServer.MAX_CLIENTS_PER_CHANNEL)
        self.ip = ip
        self.client_listen_port = client_listen_port
        self.server_listen_port = server_listen_port
        self.server_listen_socket = None
        self.client_listen_socket = None
        self.heartbleed_timer = Timer(SelectServer.HEARTBLEED_INTERVAL)
        self.candidate_server_socket = None
        super(SelectServer, self).__init__(pidfile)

    def run(self):
        # Lets give new servers heartbleed interval amount of time to connect
        candidate_server_timer = Timer(SelectServer.HEARTBLEED_INTERVAL)

        # Listen socket for accepting incoming connections
        self.client_listen_socket = self.create_listen_socket(self.ip, self.client_listen_port)
        self.server_listen_socket = self.create_listen_socket(self.ip, self.server_listen_port)

        print("Server started on port " + str(self.client_listen_port))
        self.heartbleed_timer.start()

        while True:
            # Create connection to all not_connected_servers
            self.connect_to_new_servers()

            if self.heartbleed_timer.has_expired():
                self.process_heartbleeds()
                self.heartbleed_timer.start()

            if self.candidate_server_socket == None:
                candidate_server_timer.reset()
            if candidate_server_timer.has_expired():
                self.candidate_server_socket.close()
                self.candidate_server_socket = None
                candidate_server_timer.reset()

            try_to_read_from_sockets = self.clients.sockets + self.servers.sockets + [self.client_listen_socket, self.server_listen_socket]
            if self.candidate_server_socket != None:
                try_to_read_from_sockets.append(self.candidate_server_socket)

            read_sockets, write_sockets, error_sockets = select.select(try_to_read_from_sockets, [], [], SelectServer.HEARTBLEED_INTERVAL)

            for sock in read_sockets:

                # New connection attempt to listen_socket
                if sock == self.client_listen_socket:
                    sockfd, addr = self.client_listen_socket.accept()
                    try:
                        self.clients.add(sockfd)
                        # Tell about the new connection to server admin and other clients
                        print("Client connected, IP: %s, port: %s" % (addr[0], addr[1]))
                        self.broadcast_clients(str.encode("Client connected, IP: %s, port: %s\n" % (addr[0], addr[1])), [sockfd])
                    except ConnectionAddError:
                        """
                        TODO: Tell client that server is full. Our protocol doesn't define how to do this so let's
                              just rudely close the connection and continue.
                        """
                        sockfd.close()
                        continue

                # New server connection attempt
                elif sock == self.server_listen_socket and self.candidate_server_socket == None:
                    sockfd, addr = self.server_listen_socket.accept()
                    try:
                        message = "ALL_ADDRS"
                        for address in self.servers.listen_addrs:
                            new_part = " " + address[0] + " " + str(address[1])
                            appended_message = message + new_part
                            if len(appended_message.encode()) >= SelectServer.PROTOCOL_MSG_MAXLEN:
                                sockfd.sendall((message + "\n").encode())
                                message = "ALL_ADDRS" + new_part
                                continue
                            message = appended_message
                        sockfd.sendall((message + "\n").encode())

                        candidate_server_timer.start()
                        self.candidate_server_socket = sockfd
                    except socket.error:
                        sockfd.close()
                        continue


                elif sock == self.candidate_server_socket and self.candidate_server_socket != None:
                    try:
                        data = self.recv_until_newline(sock)
                        message = data.decode()  # decode bytes to utf-8
                        protocol_msg = message.split(" ")
                        if len(protocol_msg) == 3 and protocol_msg[0] == "MY_ADDR":
                            self.servers.add(sock, (protocol_msg[1], int(protocol_msg[2])))
                            print("Server connected, IP: %s, server listen port: %s" % (protocol_msg[1], protocol_msg[2]))
                            self.candidate_server_socket = None
                            candidate_server_timer.reset()
                    except socket.error:
                        sock.close()
                        self.candidate_server_socket = None
                        continue
                    # Not valid unicode message, ignore the message
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        continue
                    except ConnectionAddError:
                        """ TODO: here we should tell the new server that we can not accept any more
                                  servers (we're full). For now just close the connection.
                        """
                        sock.close()
                        self.candidate_server_socket = None
                        continue


                # Incoming message from a client
                elif sock in self.clients.sockets:
                    try:
                        data = self.recv_until_newline(sock)
                        message = data.decode()  # decode bytes to utf-8
                        protocol_msg = message.split(" ", 3)
                        if len(protocol_msg) == 1:
                            if protocol_msg[0] == "BLEED":
                                self.clients.set_heartbleed_received(sock)
                            elif protocol_msg[0] == "HEART":
                                sock.sendall("BLEED\n".encode())
                        elif len(protocol_msg) == 2:
                            if protocol_msg[0] == "JOIN":
                                self.channels.join(sock, protocol_msg[1])
                            elif protocol_msg[0] == "PART":
                                self.channels.part(sock, protocol_msg[1])
                        elif len(protocol_msg) == 4:
                            if protocol_msg[0] == "MSG":
                                # Limit so that MSG can only be sent if joined the channel first
                                if sock in self.channels.get(protocol_msg[2]):
                                    broadcast_data = (message + "\n").encode()
                                    self.broadcast_channel(broadcast_data, protocol_msg[2], [sock])
                                    self.broadcast_servers(broadcast_data)

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

                elif sock in self.servers.sockets:
                    try:
                        data = self.recv_until_newline(sock)
                        message = data.decode()  # decode bytes to utf-8
                        protocol_msg_id = message.split(" ", 1)[0]
                        if protocol_msg_id == "MSG":
                            protocol_msg = message.split(" ", 3)
                            if len(protocol_msg) != 4:
                                continue
                            self.broadcast_channel((message + "\n").encode(), protocol_msg[2])
                        elif protocol_msg_id == "ALL_ADDRS":
                            all_addrs = message.split(" ")[1:]
                            if len(all_addrs) % 2 == 1:
                                continue  # odd number, address and port should come in pairs
                            for i in range(0, len(all_addrs), 2):
                                addr_tuple = (all_addrs[i], int(all_addrs[i+1]))
                                if addr_tuple not in (self.servers.listen_addrs + self.not_connected_servers):
                                    self.not_connected_servers.append(addr_tuple)
                            # Send MY_ADDR as a response
                            my_addr_msg = "MY_ADDR " + self.ip + " " + str(self.server_listen_port) + "\n"
                            sock.sendall(my_addr_msg.encode())
                        elif protocol_msg_id == "HEART" and len(message.split(" ")) == 1:
                            sock.sendall("BLEED\n".encode())
                        elif protocol_msg_id == "BLEED" and len(message.split(" ")) == 1:
                            self.servers.set_heartbleed_received(sock)
                            
                    except socket.error:
                        self.close_server(sock)
                        continue
                    # Not valid unicode message, ignore the message
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        continue
                        

    # Helper method for broadcasting to every other socket except sock (given as parameter)
    # and self.listen_sock
    def broadcast_clients(self, message, blacklist=None):
        self.broadcast_list(message, self.clients.sockets, blacklist)

    def broadcast_servers(self, message, blacklist=None):
        self.broadcast_list(message, self.servers.sockets, blacklist)

    def broadcast_channel(self, message, channel, blacklist=None):
        socklist = self.channels.get(channel)
        self.broadcast_list(message, socklist, blacklist)

    def broadcast_list(self, message, socklist, blacklist=None):
        if blacklist is None:
            blacklist = []

        forced_blacklist = [self.client_listen_socket, self.server_listen_socket]

        for recv_socket in socklist:
            if recv_socket not in forced_blacklist and recv_socket not in blacklist:
                try:
                    recv_socket.sendall(message)
                except socket.error:
                    # Broken connection, close it
                    if recv_socket in self.clients.sockets:
                        self.close_client(recv_socket)
                    elif recv_socket in self.servers.sockets:
                        self.close_server(recv_socket)
                    elif recv_socket == self.candidate_server_socket:
                        self.candidate_server_socket.close()
                        self.candidate_server_socket = None
                    else:
                        raise

    # Call recv() until newline (success) or PROTOCOL_MSG_MAXLEN bytes received
    # Returns message received before newline. Does NOT return the newline character.
    # raises socket.error
    def recv_until_newline(self, sock):
        max_len = SelectServer.PROTOCOL_MSG_MAXLEN
        total_data = bytearray()
        while max_len > 0:
            try:
                data = sock.recv(1)
            except socket.error:
                raise
            if data:
                max_len -= 1
                if data == b'\n':
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

        self.clients.remove(client_sock)
        client_sock.close()


    def close_server(self, server_sock):
        print("Closed server connection, IP: %s, port: %s" % (self.servers.get_socket_listen_addr(server_sock)[0], self.servers.get_socket_listen_addr(server_sock)[1]))
        self.servers.remove(server_sock)
        server_sock.close()

    def process_heartbleeds(self):
        self.check_heartbleed_responses(self.clients)
        self.check_heartbleed_responses(self.servers)

        self.send_heartbleed_requests(self.clients)
        self.send_heartbleed_requests(self.servers)

    def check_heartbleed_responses(self, conn_manager):
        # Check if previous HEART\m messages were answered
        dead_sockets = []
        for i in range(len(conn_manager.heartbleed_status)):
            if conn_manager.heartbleed_status[i] < 0:
                conn_manager.heartbleed_status[i] = 0
            elif conn_manager.heartbleed_status[i] < SelectServer.MISSING_HEARTBLEEDS_ACCEPTED:
                conn_manager.heartbleed_status[i] += 1
            else:
                dead_sockets.append(conn_manager.sockets[i])

        for sock in dead_sockets:
            if conn_manager.type == ConnectionManager.TYPE_CLIENT:
                self.close_client(sock)
            elif conn_manager.type == ConnectionManager.TYPE_SERVER:
                self.close_server(sock)

    def send_heartbleed_requests(self, conn_manager):
        dead_sockets = []
        for sock in conn_manager.sockets:
            try:
                sock.sendall("HEART\n".encode())
            except socket.error:
                dead_sockets.append(sock)

        for dead_sock in dead_sockets:
            if conn_manager.type == ConnectionManager.TYPE_CLIENT:
                self.close_client(dead_sock)
            elif conn_manager.type == ConnectionManager.TYPE_SERVER:
                self.close_server(dead_sock)

    # Return connected socket or None if unsuccessful
    def connect(self, ip, port):
        sock = None
        for result in socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            family, socktype, proto, _, addr = result
            try:
                sock = socket.socket(family, socktype, proto)
            except socket.error:
                sock = None
                continue
            try:
                sock.connect(addr)
            except socket.error as e:
                print("Failed to connect", ip, port, "due to", e)
                sock.close()
                sock = None
                continue
            break
        return sock

    def connect_to_new_servers(self):
        for server_addr in self.not_connected_servers:
            server_sock = self.connect(server_addr[0], server_addr[1])
            if server_sock == None:
                continue
            try:
                self.servers.add(server_sock, server_addr)
            # This server is already connected to maximum amount of other servers.
            except ConnectionAddError:
                server_sock.close()
                continue
        self.not_connected_servers = []

    def create_listen_socket(self, ip, port):
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(128)  # parameter value = maximum number of queued connections
        return sock