"""
This module contains test functions
"""

# an ugly way to import both client and server and still keep them runnable on their own
# beware of name shadowing (timer at least had some mismatching names..)
import sys
import os
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir + "/client")
sys.path.append(base_dir + "/server")

from client.client import Client
from server.server import MChatServer


def no_newline_test():
    """
    This test creates a client, connects to a
    hardcoded server and sends a single message
    without terminating newline.

    This will stall the whole server because
    the server tries to read a whole line from the client.
    It will also be eventually cause the server to be
    disconnected from the server network as it cannot
    respond to HEART messages.
    """
    import time
    import socket
    cl = socket.socket()
    cl.connect(("localhost", 6061))
    print("Press ctrl-c to stop")
    while True:
        cl.sendall("-".encode())  # no newline here
        time.sleep(0.8) # just keep sending
    cl.close()


def quick_resend_test():
    """
    The test connects to server, sends a longish string
    and quickly repeats this. The server crashed to
    an unhandled exception in this case, but it was fixed.
    """
    cl = Client("tester", prints_disabled=True)
    buf = "\n"*2**12
    for i in range(2):
        cl.connect("localhost", 6061)
        cl.sendString(buf)
        cl.disconnect()


def many_nodes(client_count, server_count):
    """
    Spawns given number of clients and servers keeps them running.
    The clients connect to the network, join channels, and start
    sending messages.
    Lacks any proper output of the status.
    """
    from multiprocessing import Process
    import time
    import random

    # the task functions will be run in a subprocess
    def server_task(*args):
        # suppress the output
        sys.stdout = open(os.devnull, "w")
        # run the server
        MChatServer(*args).run()

    def client_task(number, server_addr):
        # start the client
        cl = Client("tester"+str(number), prints_disabled=True)
        cl.connect(server_addr[0], server_addr[1])
        # join channels
        channels = []
        channel_count = 30
        for i in range(channel_count):
            channel = "chan"+str(i)
            cl.join(channel)
            channels.append(channel)
        # spam messages
        while True:
            # keep sending as quickly as possible (high load)
            for channel in channels:
                cl.sendMessage(channel, "Fasfsadfasdfasdfasfda")
        cl.disconnect()

    # subprocess containers
    client_procs = []
    server_procs = {}

    # launch servers
    print("Launching {} servers".format(server_count))
    for i in range(server_count):
        ip = "localhost"
        client_port = 62000+i
        server_port = 64000+i
        known_ip = ip
        known_port = 64000+(i-1)
        if i == 0:
            known_port += 1
            # for the first server
            known_ip = None
            known_port = None
        # create and start the child process
        proc = Process(target=server_task, args=("", ip, client_port, server_port, known_ip, known_port))
        proc.start()
        server_procs[(ip, client_port, server_port)] = proc
        print("Launched server {}. (ports {}, {})".format(i, client_port, server_port))
        # avoid launching everything in the same moment
        time.sleep(0.08)

    # launch clients
    print("Launching {} clients".format(client_count))
    server_infos = tuple(server_procs.keys())
    for i in range(client_count):
        # choose a random server
        server_info = random.choice(server_infos)
        proc = Process(target=client_task, args=(i, (server_info[0], server_info[1])))
        proc.start()
        client_procs.append(proc)
        print("Launched client {}".format(i))
        time.sleep(0.08)

    print("Waiting for the child processes (or ctrl-c)")
    # wait for the processes
    for key, proc in server_procs.items():
        # wait for the processes
        proc.join()
    for proc in client_procs:
        proc.join()


def main():
    """
    Some simple test cases.
    Changing the test is only possible by
    commenting the function calls..
    """
    # no_newline_test()
    # quick_resend_test()
    many_nodes(50, 50)

if __name__ == "__main__":
    main()
