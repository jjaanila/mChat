from server import SelectServer
from random import randint

"""
This file can be used to run the server as a non-daemon.
Run main_without_daemon first and then this script as many times as you want to.
This script creates servers that connect to the same network.
"""

def main():
    pidfile = "/tmp/select-server-daemon.pid"

    server = SelectServer(pidfile, "localhost", randint(2000, 65000), randint(2000, 65000), "localhost", 6071)
    server.run()

if __name__ == "__main__":
    main()
