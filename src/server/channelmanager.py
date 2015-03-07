class ChannelManager():
    def __init__(self):
        self.channels = {}

    def join(self, socket, channel):
        # If channel exists, make socket join it
        if channel in self.channels:
            self.channels[channel].append(socket)
        # If channel doesn't exist create the channel list and add socket as the only subscriber
        else:
            self.channels[channel] = [socket]

    # Part socket from channel but doesn't delete channel if it is empty.
    # Instead returns false if channel is empty and has to be deleted, otherwise returns true
    def __part_but_dont_delete_channel(self, socket, channel):
        if channel in self.channels:
            if socket in self.channels[channel]:
                self.channels[channel].remove(socket)

                if self.channels[channel] == []:
                    return False
        return True

    def part(self, socket, channel):
        if not self.__part_but_dont_delete_channel(socket, channel):
            del self.channels[channel]

    def part_all(self, socket):
        empty_channels = []
        for channel in self.channels:
            if not self.__part_but_dont_delete_channel(socket, channel):
                empty_channels.append(channel)
        for empty_channel in empty_channels:
            del self.channels[empty_channel]

    # Returns list of sockets that are subscribed to channel.
    # Returns empty list if channel doesn't exist
    def get(self, channel):
        if self.channels.get(channel) is None:
            return []
        return self.channels.get(channel)