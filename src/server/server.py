import socket
import sys
import select
import logging
import signal
from logging.handlers import RotatingFileHandler
from daemon import Daemon
from channelmanager import ChannelManager
from channelmanager import ChannelJoinError
from connectionmanager import ConnectionManager
from connectionmanager import ConnectionAddError
from timer import Timer



class MChatServer(Daemon):
    """
    start() is inherited from Daemon class and starts the server as a daemon
    run() should be used to run the server as a non-daemon
    """
    
    PROTOCOL_MSG_MAXLEN = 1024
    NICKNAME_MAXLEN = 32
    CHANNELNAME_MAXLEN = 64

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

        self.servers = ConnectionManager(MChatServer.MAX_SERVERS, ConnectionManager.TYPE_SERVER)
        self.clients = ConnectionManager(MChatServer.MAX_CLIENTS, ConnectionManager.TYPE_CLIENT)
        self.channels = ChannelManager(MChatServer.MAX_CHANNELS, MChatServer.MAX_CLIENTS_PER_CHANNEL)
        self.ip = ip
        self.client_listen_port = client_listen_port
        self.server_listen_port = server_listen_port
        self.server_listen_socket = None
        self.client_listen_socket = None
        self.heartbleed_timer = Timer(MChatServer.HEARTBLEED_INTERVAL)
        self.candidate_server_socket = None
        self.logger = self.logger_setup()

        super(MChatServer, self).__init__(pidfile)
        
    def run(self):
        """
        Overrides run() of parent class Daemon
        """
        try:
            self.__start_server()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Server stopped.")
        except Exception as e:
            self.logger.exception("Uncaught exception:")
            raise e
        finally:
            print("Server stopped.")

    def __start_server(self):
        """
        Only run this function from the run() wrapper.
        """
        # Set signal handlers.
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        
        # Lets give new servers heartbleed interval amount of time to connect
        candidate_server_timer = Timer(MChatServer.HEARTBLEED_INTERVAL)

        # Listen socket for accepting incoming connections
        self.client_listen_socket = self.create_listen_socket(self.ip, self.client_listen_port)
        self.server_listen_socket = self.create_listen_socket(self.ip, self.server_listen_port)
        if self.client_listen_socket == None or self.server_listen_socket == None:
            sys.exit("Failed to open listen sockets to given hostname and port combination.")

        log_message = "Server started on '{}'. Client port: {}, Server port: {}".format(self.ip, self.client_listen_port, self.server_listen_port)
        print(log_message)
        self.logger.info(log_message)

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

            read_sockets, write_sockets, error_sockets = select.select(try_to_read_from_sockets, [], [], MChatServer.HEARTBLEED_INTERVAL)

            for sock in read_sockets:

                # New connection attempt to listen_socket
                if sock == self.client_listen_socket:
                    sockfd, addr = self.client_listen_socket.accept()
                    try:
                        self.clients.add(sockfd)
                        log_message = "Client connected, IP: {}, port: {}".format(addr[0], addr[1])
                        print(log_message)
                        self.logger.info(log_message)
                    except ConnectionAddError:
                        """
                        TODO: Tell client that server is full. Our protocol doesn't define how to do this so let's
                              just rudely close the connection and continue.
                        """
                        self.logger.exception("Connection from client IP: {}, port: {} refused.".format(addr[0], addr[1]))
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
                            if len(appended_message) >= MChatServer.PROTOCOL_MSG_MAXLEN:
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
                            self.servers.add(sock, listen_addr=(protocol_msg[1], int(protocol_msg[2])))

                            log_message = "Server connected, IP: {}, server listen port: {}".format(protocol_msg[1], protocol_msg[2])
                            print(log_message)
                            self.logger.info(log_message)

                            self.candidate_server_socket = None
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
                        self.logger.exception("Connection from candidate server refused.")
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
                                channel = protocol_msg[1]
                                if len(channel) > MChatServer.CHANNELNAME_MAXLEN:
                                    continue
                                if self.channels.join(sock, channel):
                                    nick = self.clients.get_nickname(sock)
                                    self.send_system_message(channel, nick + " joined channel")
                            elif protocol_msg[0] == "PART":
                                channel = protocol_msg[1]
                                if len(channel) > MChatServer.CHANNELNAME_MAXLEN:
                                    continue
                                if self.channels.part(sock, channel):
                                    nick = self.clients.get_nickname(sock)
                                    self.send_system_message(channel, nick + " left channel")
                            elif protocol_msg[0] == "NICK":
                                nick = protocol_msg[1]
                                if len(nick) > MChatServer.NICKNAME_MAXLEN:
                                    continue
                                old_nick = self.clients.get_nickname(sock)
                                if nick != old_nick:
                                    self.clients.set_nickname(sock, nick)
                                    for channel in self.channels.get_channels_of_socket(sock):
                                        self.send_system_message(channel, old_nick + " changed nickname to " + nick)

                        elif len(protocol_msg) == 4:
                            if protocol_msg[0] == "MSG":
                                nick = protocol_msg[1]
                                # check that MSG message is valid (length of channel name and nickname), continue if it isn't
                                if (len(nick) > MChatServer.NICKNAME_MAXLEN) or (len(protocol_msg[2]) > MChatServer.CHANNELNAME_MAXLEN):
                                    continue
                                # Limit so that MSG can only be sent if joined the channel first, continue if channel is not joined
                                if sock not in self.channels.get(protocol_msg[2]):
                                    continue

                                old_nick = self.clients.get_nickname(sock)
                                if nick != old_nick:
                                    self.clients.set_nickname(sock, nick)
                                    for channel in self.channels.get_channels_of_socket(sock):
                                        self.send_system_message(channel, old_nick + " changed nickname to " + nick)

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
                        try:
                            addr = sock.getpeername()
                            self.logger.exception("Client {} {} couldn't join channel {}.".format(addr[0], addr[1], protocol_msg[1]))
                        except socket.error:
                            self.logger.exception("Client couldn't join channel {}. Failed to fetch address of the client".format(protocol_msg[1]))
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
                            # check that MSG message is valid (length of channel name and nickname), continue if it isn't
                            if (len(protocol_msg[1]) > MChatServer.NICKNAME_MAXLEN) or (len(protocol_msg[2]) > MChatServer.CHANNELNAME_MAXLEN):
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
                        elif protocol_msg_id == "SYSTEM":
                            protocol_msg = message.split(" ", 2)
                            if len(protocol_msg) != 3:
                                continue
                            if len(protocol_msg[1]) > MChatServer.CHANNELNAME_MAXLEN:
                                continue
                            self.broadcast_channel((message + "\n").encode(), protocol_msg[1])

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

    # Call recv() until newline (success) or PROTOCOL_MSG_MAXLEN * 4 bytes received (utf-8 char is max 4 bytes)
    # Returns message received before newline. Does NOT return the newline character.
    # raises socket.error
    def recv_until_newline(self, sock):
        max_len = MChatServer.PROTOCOL_MSG_MAXLEN * 4
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

    # This method should not raise error or do anything unexpected even if the socket is already closed or invalid
    def close_client(self, client_sock):
        # check if this client has been closed already by trying to fetch nickname of client
        try:
            nick = self.clients.get_nickname(client_sock)
        except ValueError:
            # This is client is closed already, return
            return

        try:
            client_name = client_sock.getpeername()
            log_message = "Client offline, IP: {}, port: {}".format(client_name[0], client_name[1])
            print(log_message)
            self.logger.info(log_message)
        except socket.error:
            log_message = "Client offline, failed to fetch IP and port of the client"
            print(log_message)
            self.logger.info(log_message)

        # Part closing client from all channels
        parted_channels = self.channels.part_all(client_sock)

        self.clients.remove(client_sock)
        client_sock.close()

        # Send system message about the client leaving in the end of the method so that it does not get sent
        # to the  client itself
        for channel in parted_channels:
            self.send_system_message(channel, nick + " left channel")


    # This method should not raise error or do anything unexpected even if the socket is already closed or invalid
    def close_server(self, server_sock):
        # check if this server has been closed already by trying to fetch its listen_addr
        try:
            listen_addr = self.servers.get_socket_listen_addr(server_sock)
        except ValueError:
            # This is server is closed already, return
            return

        log_message = "Closed server connection, IP: {}, port: {}".format(listen_addr[0], listen_addr[1])
        print(log_message)
        self.logger.info(log_message)

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
            elif conn_manager.heartbleed_status[i] < MChatServer.MISSING_HEARTBLEEDS_ACCEPTED:
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
		# prevent connections to own ip and server ports
        if ip == self.ip and (port == self.client_listen_port or port == self.server_listen_port):
            return None
        sock = None

        try:
            addrinfo = socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.error:
            return None

        for result in addrinfo:
            family, socktype, proto, _, addr = result
            try:
                sock = socket.socket(family, socktype, proto)
            except socket.error:
                sock = None
                continue
            try:
                sock.connect(addr)
            except socket.error as e:
                log_message = "Failed to connect {}:{} due to {}".format(addr[0], addr[1], e)
                print(log_message)
                self.logger.error(log_message)
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
                self.servers.add(server_sock, listen_addr=server_addr)
            # This server is already connected to maximum amount of other servers.
            except ConnectionAddError:
                server_sock.close()
                continue
        self.not_connected_servers = []

    # Return created listen socket or None if unsuccessful
    def create_listen_socket(self, ip, port):
        sock = None

        try:
            addrinfo = socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.error:
            return None

        for result in addrinfo:
            family, socktype, proto, _, addr = result
            try:
                sock = socket.socket(family, socktype, proto)
            except socket.error:
                sock = None
                continue
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(addr)
                sock.listen(128)  # parameter value = maximum number of queued connections
            except socket.error as e:
                log_message = "Failed to bind listen socket to address {}:{} due to {}".format(addr[0], addr[1], e)
                print(log_message)
                self.logger.error(log_message)
                sock.close()
                sock = None
                continue
            break
        return sock

    def sigterm_handler(self, _signo, _stack_frame):
        raise SystemExit

    def logger_setup(self):
        log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
        log_file = self.ip + "_" + str(self.client_listen_port) + "_" + "server.log"
        my_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024, backupCount=1, encoding=None, delay=0)
        my_handler.setFormatter(log_formatter)
        my_handler.setLevel(logging.INFO)
        app_log = logging.getLogger("Rotating Logger")
        app_log.setLevel(logging.INFO)
        app_log.addHandler(my_handler)
        return app_log

    # parameter message is a string, not bytes
    def send_system_message(self, channel, message):
        system_message = "SYSTEM " + channel + " " + message + "\n"
        if len(system_message) > MChatServer.PROTOCOL_MSG_MAXLEN or len(channel) > MChatServer.CHANNELNAME_MAXLEN:
            raise InvalidProtocolMessageError("Tried to send invalid system message")
        byte_system_message = system_message.encode()
        self.broadcast_channel(byte_system_message, channel)
        self.broadcast_servers(byte_system_message)


class InvalidProtocolMessageError(Exception):
    pass
