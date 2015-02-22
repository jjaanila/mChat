"""
mChat client software.
"""

import sys, socket, threading

def hasEnoughArguments(command, required_n):
        if (len(command) != required_n + 1):
            print("This command requires " + str(required_n) + " arguments!")
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
    
    def connect(self, ip, port):
        try:
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.socket.connect((ip, port))
        except:
            print("Failed to connect", ip, port)
            self.socket = None
            return
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
        self.socket.send(message_format.encode())
        
    def join(self, room):#TODO: NW PART
        if (not self.isConnected()):
            return
        if (room in self.rooms):
            print("You are in that room already!")
            return
        self.rooms.append(room)
        message_format = "JOIN" + " " + room + "\n"
        self.socket.send(message_format.encode())
    
    def part(self, room):#TODO: NW PART
        if (not self.isConnected()):
            return
        if (not room in self.rooms):
            print("You are not in that room yet!")
            return
        self.rooms.remove(room)
        message_format = "PART" + " " + room + "\n"
        self.socket.send(message_format.encode())
        
    def printHelp(self):
        print("""Commands:
/connect <IP> <Port>
/disconnect
/join <room_name>
/part <room_name>
/quit
/msg <room_name> <message>
/help""")
        
    def processInput(self):
        terminal_input = input(self.nick + ": ")
        if (terminal_input.find("/") == 0):
            command = terminal_input.split(" ")
        else:
            print("Invalid input.")
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
            self.socket.close()
            sys.exit()
            
        elif (command[0] == "/msg"):
            if (hasEnoughArguments(command, 2)):
                self.sendMessage(command[1], command[2])
                
        elif (command[0] == "/help"):
            self.printHelp()
                   
        else:
            print("Unknown command.") 
        
    def run(self):
        #self.receiveMessages() to own thread
        while(True):
            self.processInput()

def main():
    client = Client("Seppo")
    client.run()


if __name__ == '__main__':
    main()

