import socket
import select
from daemon import Daemon


class SelectServer(Daemon):
    RECV_BUFFER = 2048

    def __init__(self, ip, port, pidfile):
        self.connection_list = []
        self.ip = ip
        self.port = port
        self.listen_socket = None
        super(SelectServer, self).__init__(pidfile)

    def run(self):
        running = True

        # Listen socket for accepting incoming connections
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
                    self.broadcast(sockfd, str.encode("Client connected, IP: %s, port: %s\n" % (addr[0], addr[1])))

                # Incoming message from a client
                else:
                    try:
                        data = self.recv_until_newline(sock)
                        message = data.decode()  # decode bytes to utf-8
                        # Broadcast message to other clients
                        self.broadcast(sock, ("Nick here: " + message).encode())
                    # Client disconnected
                    except socket.error:
                        self.close_client(sock)
                        continue
                    # Not valid unicode message, ignore the message
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        continue

        self.listen_socket.close()

    # Helper method for broadcasting to every other socket except sock (given as parameter)
    # and self.listen_sock
    def broadcast(self, sock, message):
        for recv_socket in self.connection_list:
            if recv_socket != self.listen_socket and recv_socket != sock:
                try:
                    recv_socket.send(message)
                except socket.error:
                    # Broken connection, close it
                    self.close_client(recv_socket)

    # Call recv() until newline (success) or RECV_BUFFER bytes received
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
                    total_data.extend(data[:data.find(b'\n') + 1])  # +1 includes the line feed
                    break
                total_data.extend(data)
            else:
                raise socket.error
        return bytes(total_data)

    def close_client(self, client_sock):
        client_name = client_sock.getpeername()
        print("Client offline, IP: %s, port: %s" % (client_name[0], client_name[1]))
        self.broadcast(client_sock, str.encode("Client offline, IP: %s, port: %s\n" % (client_name[0], client_name[1])))
        client_sock.close()
        if client_sock in self.connection_list:
            self.connection_list.remove(client_sock)