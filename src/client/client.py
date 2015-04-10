"""
mChat client software.
"""

import sys, socket, threading, time
from timer import Timer
from fancyui import FancyUI
from rooms import Room, PrivateRoom

class Client:
    BUFFER_SIZE = 4096
    MAX_NICK_LEN = 32
    MAX_ROOM_LEN = 64
    MAX_MSG_LEN = 1024 #Max size in bytes: 4096
    
    def __init__(self, nick, prints_disabled=False):
        self.socket = None
        self.nick = nick
        self.rooms = []

        self.heartbleed_interval = 2
        self.heartbleed_timer = Timer(5)
        
        self.ui = FancyUI(nick, prints_disabled)
        
    def isConnected(self):
        if (self.socket == None):
            return False
        return True
    
    def hasEnoughArguments(self, command, required_n):
        if (len(command) != required_n + 1):
            self.ui.printString("This command requires " + str(required_n) + " argument(s)!")
            return False
        return True
    
    def sendString(self, string):
        if self.isConnected():
            try:
                self.socket.sendall(string.encode())
            except socket.error as e:
                self.ui.printString("Send error, " + str(e))
        else:
            self.ui.printString("There is no connection.")
            
    def getRoom(self, room_name):
        for room in self.rooms:
            if room.name == room_name:
                return room
            if room.getRoomNetworkName() == room_name:
                return room
        return None
    
    def receiveMessagesAndCheckTimers(self):
        data = b""
        while(self.isConnected):
            while(b'\n' not in data):
                time.sleep(0.1)
                self.checkTimers()
                if len(data) > Client.BUFFER_SIZE:
                    data = b""
                try:
                    if self.socket == None:
                        return
                    data += self.socket.recv(Client.BUFFER_SIZE)
                except socket.error as e:
                    self.ui.printString("Receive error." + str(e))
            data_u = data.decode()
            messages = data_u.split("\n", 1)
            data = messages[1].encode()
            protocol_msg = messages[0].split(" ", 3)
            
            if protocol_msg[0] == "MSG" and len(protocol_msg) == 4:
                room = self.getRoom(protocol_msg[2])
                if room != None:
                    self.ui.printString("<" + room.name + "> " + protocol_msg[1] + ": " + protocol_msg[3])
                else:
                    #Message from a room the client does not belong to.
                    self.ui.printString("<" + protocol_msg[2] + "> " + protocol_msg[1] + "DEBUG: #Message from a room the client does not belong to.")
                    
            elif protocol_msg[0] == "SYSTEM" and len(protocol_msg) >= 3:
                room = self.getRoom(protocol_msg[1])
                message = " ".join(protocol_msg[2:])
                if room != None:
                    self.ui.printString("<" + room.name + "> " + protocol_msg[0] + ": " + message)
                else:
                    #Message from a room the client does not belong to.
                    self.ui.printString("<" + protocol_msg[1] + "> " + protocol_msg[0] + ": " + message + "DEBUG: #Message from a room the client does not belong to.")
                    
            elif protocol_msg[0] == "HEART":
                self.sendString("BLEED\n")
                
            elif protocol_msg[0] == "BLEED":
                self.heartbleed_timer.start()
            else:
                self.ui.printString("Unidentified message: " + messages[0])
    
    def connect(self, ip, port):
        if (self.isConnected()):
            self.ui.printString("There is a connection already. Disconnect before a new connection.")
            return
        sock = None
        try:
            addr_info = socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.error as e:
            self.ui.printString("Failed to connect to " + ip + ":" + port + " due to " + str(e))
            return
        for result in addr_info:
            family, socktype, proto, _, addr = result
            try:
                sock = socket.socket(family, socktype, proto)
            except socket.error:
                sock = None
                continue
            try:
                sock.connect(addr)
            except socket.error as e:
                self.ui.printString("Failed to connect to " + addr[0] + ":" + str(addr[1]) + " due to " + str(e))
                sock.close()
                sock = None
                continue
            break
        if (sock == None):
            self.ui.printString("Connection failed.")
            return
        self.socket = sock
        t = threading.Thread(target=self.receiveMessagesAndCheckTimers)
        t.daemon = True
        t.start()
        self.sendKeepAliveMessage()#Will continue sending in a separate thread.
        self.heartbleed_timer.start()
        self.sendString("NICK " + self.nick + "\n")
        self.ui.printString("Connected to " + ip + ":" + str(port))
        
    def disconnect(self):
        if (not self.isConnected()):
            self.ui.printString("There is no connection.")
            return
        self.rooms = []
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error:
            pass
        self.socket = None
        self.heartbleed_timer.reset()
        self.ui.printString("Disconnected.")
    
    def quit(self):
        if self.isConnected():
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        self.ui.printString("Goodbye!")
        sys.exit()
        
    def sendMessage(self, room_name, message):
        if (not self.isConnected()):
            self.ui.printString("There is no connection.")
            return
        room = self.getRoom(room_name)
        if (room == None):
            self.ui.printString("You don't belong to that room!")
            return
        msg_space = Client.MAX_MSG_LEN - len(self.nick) - len(room.name) - 7 #Magic number: len(Tag + spaces + newline)
        rng = range(0, len(message), msg_space)
        message_split = [message[i:i + msg_space] for i in rng]

        for message_part in message_split:
            self.ui.printString("<" + room.name + "> " + self.nick + ": " + message_part)
            message_format = "MSG" + " " + self.nick + " " + room.getRoomNetworkName() + " " + message_part + "\n"
            try:
                self.sendString(message_format)
            except socket.error as e:
                self.ui.printString("Send error." + str(e))
                return
        
    def changeNick(self, new_nick):
        if (len(new_nick) > Client.MAX_NICK_LEN):
            self.ui.printString("Too long nick! (Max {})".format(Client.MAX_NICK_LEN))
        elif (len(new_nick) == 0):
            self.ui.printString("You did not give a proper nick.")
        else:
            self.nick = new_nick
            self.ui.nick = new_nick
            self.sendString("NICK " + new_nick + "\n")
            self.ui.printString("Nick changed to " + new_nick + ".")
        
    def join(self, room_name, password=None):
        if (not self.isConnected()):
            self.ui.printString("There is no connection.")
            return
        if (self.getRoom(room_name) != None):
            self.ui.printString("You are in that room already!")
            return
        if len(room_name) > Client.MAX_ROOM_LEN:
            self.ui.printString("Too long room name.(Max {})".format(Client.MAX_ROOM_LEN))
            return
        
        if password != None:
            self.rooms.append(PrivateRoom(room_name, password))
        else:
            self.rooms.append(Room(room_name))
            
        message_format = "JOIN" + " " + self.rooms[-1].getRoomNetworkName() + "\n"      
        self.ui.printString("Joined room " + room_name + ".")
        self.sendString(message_format)
    
    def part(self, room_name):
        if (not self.isConnected()):
            self.ui.printString("There is no connection.")
            return
        room = self.getRoom(room_name)
        if (room == None):
            self.ui.printString("You are not in that room yet!")
            return
        message_format = "PART" + " " + room.getRoomNetworkName() + "\n"
        self.ui.printString("Left room " + room.name + ".")
        self.rooms.remove(room)
        self.sendString(message_format)
        
    def sendKeepAliveMessage(self):
        if self.socket != None:
            self.sendString("HEART\n")
            thread = threading.Timer(self.heartbleed_interval, self.sendKeepAliveMessage)
            thread.daemon = True # the main thread won't wait for this thread after exiting
            thread.start()
            
    def checkTimers(self):
        if (self.heartbleed_timer.has_expired()):
            self.ui.printString("Server lost! Disconnecting...")
            self.disconnect()
        
    def printHelp(self):
        self.ui.printString("""Commands:
connect <IP> <Port>
disconnect
join <room_name>
joinprivate <room_name> <password>
part <room_name>
quit
msg <room_name> <message>
nick <new_nick>
help""")

    def processInput(self):
        while(True):
            try:
                terminal_input = input("")
            except (EOFError, KeyboardInterrupt) as e:
                self.ui.printString("Stopping the client. {}".format(e))
                break
            command = terminal_input.split(" ", 2)
            
            if (command[0] == "connect"):
                if (self.hasEnoughArguments(command, 2)):
                    self.connect(command[1], command[2])
                    
            elif (command[0] == "disconnect"):
                self.disconnect()
                
            elif (command[0] == "join"):
                if (self.hasEnoughArguments(command, 1)):
                    self.join(command[1])
            
            elif (command[0] == "joinprivate"):
                if (self.hasEnoughArguments(command, 2)):
                    self.join(command[1], command[2])
                           
            elif (command[0] == "part"):
                if (self.hasEnoughArguments(command, 1)):
                    self.part(command[1])
                    
            elif (command[0] == "quit"):
                self.quit()
                
            elif (command[0] == "msg"):
                if (self.hasEnoughArguments(command, 2)):
                    self.sendMessage(command[1], command[2])
                    
            elif (command[0] == "nick"):
                if (self.hasEnoughArguments(command, 1)):
                    self.changeNick(command[1])
                    
            elif (command[0] == "help"):
                self.printHelp()
                       
            else:
                self.ui.printString("Unknown command.")
        
    def run(self):
        self.ui.printString("Hi!\nmChat client at your service. Type help for instructions.")
        self.processInput()
        self.quit()

def main():
    h = False
    d = False
    if len(sys.argv) > 1:
        if "-d" in sys.argv:
            d = True
    client = Client("mChatter", prints_disabled=d)
    client.run()


if __name__ == '__main__':
    main()

