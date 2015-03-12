class ChannelJoinError(Exception):
    pass


class ChannelManager():
    def __init__(self, max_channels, max_members):
        self.max_channels = max_channels
        self.max_members = max_members
        self.channels = {}

    def join(self, socket, channel):
        # If channel exists make socket join it
        if channel in self.channels:
            # Check that socket not already joined
            if socket not in self.channels[channel]:
                if len(self.channels[channel]) < self.max_members:
                    self.channels[channel].append(socket)
                else:
                    raise ChannelJoinError("Too many members on channel. Unable to add more.")
        # If channel doesn't exist create the channel list and add socket as the only subscriber
        else:
            if len(self.channels) < self.max_channels:
                self.channels[channel] = [socket]
            else:
                raise ChannelJoinError("Too many channels. Can't create more.")

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