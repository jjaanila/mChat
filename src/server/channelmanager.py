class ChannelJoinError(Exception):
    pass


class ChannelManager():
    def __init__(self, max_channels, max_members):
        self.max_channels = max_channels
        self.max_members = max_members
        self.channels = {}

    # Return True if join succesful (socket not joined already), otherwise return False
    def join(self, socket, channel):
        # If channel exists make socket join it
        if channel in self.channels:
            # Check that socket not already joined
            if socket not in self.channels[channel]:
                if len(self.channels[channel]) < self.max_members:
                    self.channels[channel].append(socket)
                    return True
                else:
                    raise ChannelJoinError("Too many members on channel. Unable to add more.")
        # If channel doesn't exist create the channel list and add socket as the only subscriber
        else:
            if len(self.channels) < self.max_channels:
                self.channels[channel] = [socket]
                return True
            else:
                raise ChannelJoinError("Too many channels. Can't create more.")

        return False

    # Part socket from channel but doesn't delete channel if it is empty.
    # Instead returns false if channel is empty and has to be deleted, otherwise returns true
    def __part_but_dont_delete_channel(self, socket, channel):
        if channel in self.channels:
            if socket in self.channels[channel]:
                self.channels[channel].remove(socket)

                if self.channels[channel] == []:
                    return False
        return True

    # return True if part succesful (client had joined first), return False if unsuccesful
    def part(self, socket, channel):
        if socket in self.channels[channel]:
            if not self.__part_but_dont_delete_channel(socket, channel):
                del self.channels[channel]
            return True
        return False


    # return a list of all the parted channels
    def part_all(self, socket):
        empty_channels = []
        sockets_channels = []
        for channel in self.channels:
            if socket in self.channels[channel]:
                sockets_channels.append(channel)
            if not self.__part_but_dont_delete_channel(socket, channel):
                empty_channels.append(channel)
        for empty_channel in empty_channels:
            del self.channels[empty_channel]
        return sockets_channels

    # Returns list of sockets that are subscribed to channel.
    # Returns empty list if channel doesn't exist
    def get(self, channel):
        if self.channels.get(channel) is None:
            return []
        return self.channels.get(channel)

    def get_channels_of_socket(self, sock):
        socket_channels = []
        for channel in self.channels:
            if sock in self.channels[channel]:
                socket_channels.append(channel)
        return socket_channels