import os
import sys

class FancyUI:
    MAX_N_HISTORY_RECORDS = 500
    
    def __init__(self, nick, prints_disabled = False):
        self.history = []
        self.nick = nick
        self.prints_disabled = prints_disabled
        
    def printString(self, string):
        if self.prints_disabled:
            return
        if len(self.history) > FancyUI.MAX_N_HISTORY_RECORDS:
            self.history.pop(0)
        self.history.append(string)
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        for record in self.history:
            print(record)
        print(self.nick + ": ", end="")
        sys.stdout.flush()
