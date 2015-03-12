"""
mChat client software.
"""

import sys, socket, threading, time
from timer import Timer
from fancyui import FancyUI

def hasEnoughArguments(command, required_n):
        if (len(command) != required_n + 1):
            self.ui.printString("This command requires " + str(required_n) + " argument(s)!")
            return False
        return True

class Client:
    BUFFER_SIZE = 1024
    
    def __init__(self, nick, is_heartbleed_on):
        self.socket = None
        self.nick = nick
        self.rooms = []
        
        self.heartbleed_on = is_heartbleed_on
        self.heartbleed_interval = 2
        self.heartbleed_timer = Timer(6)
        
        self.ui = FancyUI(nick)
        
    def isConnected(self):
        if (self.socket == None):
            return False
        return True
    
    def receiveMessages(self):
        while(self.socket != None):
            data = ""
            while(not '\n' in data):
                time.sleep(0.1)
                self.checkTimers()#Just put this somewhere.
                if self.socket == None:
                    return
                data += self.socket.recv(Client.BUFFER_SIZE).decode()
            
            data = data.rstrip('\n')
            protocol_msg = data.split(" ", 3)

            if protocol_msg[0] == "MSG" and len(protocol_msg) == 4:
                self.ui.printString("<" + protocol_msg[2] + "> " + protocol_msg[1] + ": " + protocol_msg[3])
            elif protocol_msg[0] == "HEART":
                self.socket.sendall("BLEED\n".encode())
            elif protocol_msg[0] == "BLEED":
                if self.heartbleed_on:
                    self.heartbleed_timer.start()
            else:
                self.ui.printString("Unidentified message: " + data)#Debug
    
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
                self.ui.printString("Failed to connect " + ip + ":" + port + " due to " + str(e))
                sock.close()
                sock = None
                continue
            break
        if (sock == None):
            self.ui.printString("Connection failed.")
            return
        self.socket = sock
        t = threading.Thread(target=self.receiveMessages)
        t.daemon = True
        t.start()
        if self.heartbleed_on:
            self.sendKeepAliveMessage()#Will continue sending in a separate thread.
            self.heartbleed_timer.start()
        self.ui.printString("Connected to " + ip + ":" + port)
        
    def disconnect(self):
        if (not self.isConnected()):
            self.ui.printString("There is no connection.")
            return
        self.rooms = []
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None
        self.heartbleed_timer.reset()
        self.ui.printString("Disconnected.")
    
    def quit(self):
        if self.isConnected():
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        self.ui.printString("Goodbye!")
        sys.exit()
        
    def sendMessage(self, room, message):
        if (not self.isConnected()):
            return
        if (not room in self.rooms):
            self.ui.printString("You don't belong to that room!")
            return
        self.ui.printString("<" + room + "> " + self.nick + ": " + message)
        
        message_format = "MSG" + " " + self.nick + " " + room + " " + message + "\n"
        self.socket.sendall(message_format.encode())
        
    def changeNick(self, new_nick):
        if (len(new_nick) > 32):
            self.ui.printString("Too long nick!")
        elif (len(new_nick) == 0):
            self.ui.printString("You did not give a proper nick.")
        else:
            self.nick = new_nick
            self.ui.nick = new_nick
            self.ui.printString("Nick changed to " + new_nick + ".")
        
    def join(self, room):
        if (not self.isConnected()):
            return
        if (room in self.rooms):
            self.ui.printString("You are in that room already!")
            return
        self.rooms.append(room)
        self.ui.printString("Joined room " + room + ".")
        message_format = "JOIN" + " " + room + "\n"
        self.socket.sendall(message_format.encode())
    
    def part(self, room):
        if (not self.isConnected()):
            return
        if (not room in self.rooms):
            self.ui.printString("You are not in that room yet!")
            return
        self.rooms.remove(room)
        self.ui.printString("Left room " + room)
        message_format = "PART" + " " + room + "\n"
        self.socket.sendall(message_format.encode())
        
    def sendKeepAliveMessage(self):
        if self.socket != None:
            self.socket.sendall("HEART\n".encode())
            thread = threading.Timer(self.heartbleed_interval, self.sendKeepAliveMessage)
            thread.daemon = True # the main thread won't wait for this thread after exiting
            thread.start()
            
    def checkTimers(self):
        if self.heartbleed_on:
            if (self.heartbleed_timer.hasExpired()):
                self.ui.printString("Server lost! Disconnecting...")
                self.disconnect()
        
    def printHelp(self):
        self.ui.printString("""Commands:
/connect <IP> <Port>
/disconnect
/join <room_name>
/part <room_name>
/quit
/msg <room_name> <message>
/nick <new_nick>
/help""")

    def processInput(self):
        while(True):
            terminal_input = input("")
            if (terminal_input.find("/") == 0):
                command = terminal_input.split(" ", 2)
            else:
                self.ui.printString("Invalid input. Commands should start with /")
                continue
            
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
                self.quit()
                
            elif (command[0] == "/msg"):
                if (hasEnoughArguments(command, 2)):
                    self.sendMessage(command[1], command[2])
                    
            elif (command[0] == "/nick"):
                if (hasEnoughArguments(command, 1)):
                    self.changeNick(command[1])
                    
            elif (command[0] == "/help"):
                self.printHelp()
                       
            else:
                self.ui.printString("Unknown command.")
        
    def run(self):
        self.ui.printString("Hi!\nmChat client at your service. Type /help for instructions.")
        self.processInput()

def main():
    heartbleed_on = False
    if len(sys.argv) > 1:
        if "-h" in sys.argv:
            heartbleed_on = True
    client = Client("mChatter", heartbleed_on)
    client.run()


if __name__ == '__main__':
    main()

