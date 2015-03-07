from server import SelectServer

"""
This file can be used to run the server as a non-daemon.
Pre-defined IP and port.
Convenient for testing...
"""

def main():
    pidfile = "/tmp/select-server-daemon.pid"

    server = SelectServer("", 6061, pidfile)
    server.run()

if __name__ == "__main__":
    main()