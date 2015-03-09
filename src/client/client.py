"""
mChat client software.
"""

import sys, socket, threading, time

def hasEnoughArguments(command, required_n):
        if (len(command) != required_n + 1):
            print("This command requires " + str(required_n) + " argument(s)!")
            return False
        return True

class Client():
    BUFFER_SIZE = 1024
    
    def __init__(self, nick):
        self.socket = None
        self.nick = nick
        self.rooms = []
        
    def isConnected(self):
        if (self.socket == None):
            print("There is no connection.")
            return False
        return True
    
    def receiveMessages(self):
        while(True):
            data = ""
            while(not '\n' in data):
                time.sleep(0.1)
                data += self.socket.recv(Client.BUFFER_SIZE).decode()
            
            data = data.rstrip('\n')
            protocol_msg = data.split(" ", 3)
            if protocol_msg[0] == "MSG" and len(protocol_msg) == 4:
                print("<" + protocol_msg[2] + "> " + protocol_msg[1] + ": " + protocol_msg[3])
            else:
                print("Unidentified message: " + data)#Debug
    
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
        if (sock == None):
            print("Connection failed")
            return
        self.socket = sock
        t = threading.Thread(target=self.receiveMessages)
        t.daemon = True
        t.start()
        print("Connected to", ip, port)
        
    def disconnect(self):
        if (not self.isConnected()):
            return
        self.socket.close()
        self.socket = None
        print("Disconnected")
        
    def sendMessage(self, room, message):
        if (not self.isConnected()):
            return
        if (not room in self.rooms):
            print("You don't belong to that room!")
            return
        print("<" + room + "> " + self.nick + ": " + message)
        
        message_format = "MSG" + " " + self.nick + " " + room + " " + message + "\n"
        self.socket.sendall(message_format.encode())
        
    def changeNick(self, new_nick):
        if (len(new_nick) > 32):
            print("Too long nick!")
        elif (len(new_nick) == 0):
            print("You did not give a proper nick.")
        else:
            self.nick = new_nick
        
    def join(self, room):
        if (not self.isConnected()):
            return
        if (room in self.rooms):
            print("You are in that room already!")
            return
        self.rooms.append(room)
        print("Joined room", room)
        message_format = "JOIN" + " " + room + "\n"
        self.socket.sendall(message_format.encode())
    
    def part(self, room):
        if (not self.isConnected()):
            return
        if (not room in self.rooms):
            print("You are not in that room yet!")
            return
        self.rooms.remove(room)
        print("Left room", room)
        message_format = "PART" + " " + room + "\n"
        self.socket.sendall(message_format.encode())
        
    def printHelp(self):
        print("""Commands:
/connect <IP> <Port>
/disconnect
/join <room_name>
/part <room_name>
/quit
/msg <room_name> <message>
/nick <new_nick>
/help""")

    def processInput(self):
        terminal_input = input(self.nick + ": ")
        if (terminal_input.find("/") == 0):
            command = terminal_input.split(" ", 2)
        else:
            print("Invalid input. Commands should start with /")
            return
        
        if (command[0] == "/connect"):
            if (hasEnoughArguments(command, 2)):
                self.connect(command[1], command[2])
                
        elif (command[0] == "/disconnect"):
            self.disconnect()
            
        elif (command[0] == "/join"):
            if (hasEnoughArguments(command, 1)):
                self.join(command[1])
                       
        elif (command[0] == "/part"):
            if (hasEnoughArguments(command, 1)):
                self.part(command[1])
                
        elif (command[0] == "/quit"):
            self.disconnect()
            sys.exit()
            
        elif (command[0] == "/msg"):
            if (hasEnoughArguments(command, 2)):
                self.sendMessage(command[1], command[2])
                
        elif (command[0] == "/nick"):
            if (hasEnoughArguments(command, 1)):
                self.changeNick(command[1])
                
        elif (command[0] == "/help"):
            self.printHelp()
                   
        else:
            print("Unknown command.")
        
    def run(self):
        while(True):
            self.processInput()

def main():
    client = Client("mChatter")
    client.run()


if __name__ == '__main__':
    main()

