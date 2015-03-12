import os

class FancyUI:
    MAX_N_HISTORY_RECORDS = 500
    
    def __init__(self, nick):
        self.history = []
        self.nick = nick
        
    def printString(self, string):
        if len(self.history) > FancyUI.MAX_N_HISTORY_RECORDS:
            self.history.pop(0)
        self.history.append(string)
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        for record in self.history:
            print(record)
        print(self.nick + ": ", end="", flush=True)
        