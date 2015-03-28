import hashlib

class Room(object):
    
    def __init__(self, name):
        self.name = name
    
    def getRoomNetworkName(self):
        return self.name
        
class PrivateRoom(object):
    
    def __init__(self, name, password):
        self.name = name
        
        name_pwd = name + password
        hashlib.digest_size = 20
        h = hashlib.sha1(name_pwd.encode())
        self.hash = h.hexdigest()
        
    def getRoomNetworkName(self):
        return self.hash