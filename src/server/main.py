from server import SelectServer
import sys


def print_instructions(program_name):
    print("usage: %s start <ip> <client_port> <server_port> | restart <ip> <client_port> <server_port> | stop" % program_name)


def main():
    pidfile = "/tmp/select-server-daemon.pid"

    if len(sys.argv) == 5:
        if 'start' == sys.argv[1]:
            server = SelectServer(pidfile, sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
            server.start()
            print("Server started.")
        elif 'restart' == sys.argv[1]:
            server = SelectServer(pidfile, sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
            server.restart()
            print("Server restarted.")
        else:
            print_instructions(sys.argv[0])
            sys.exit(2)
        sys.exit(0)

    elif len(sys.argv) == 2:
        if 'stop' == sys.argv[1]:
            server = SelectServer(pidfile, "", 0, 0)  # only pidfile has to be correct here
            server.stop()
            print("Server stopped.")
        else:
            print_instructions(sys.argv[0])
            sys.exit(2)
        sys.exit(0)

    else:
        print_instructions(sys.argv[0])
        sys.exit(2)


if __name__ == "__main__":
    main()
