from server import SelectServer
import sys


def print_instructions(program_name):
    print("usage: %s start <ip> <port> | restart <ip> <port> | stop" % program_name)


def main():
    pidfile = "/tmp/select-server-daemon.pid"

    if len(sys.argv) == 4:
        if 'start' == sys.argv[1]:
            server = SelectServer(pidfile, sys.argv[2], int(sys.argv[3]))
            server.start()
        elif 'restart' == sys.argv[1]:
            server = SelectServer(pidfile, sys.argv[2], int(sys.argv[3]))
            server.restart()
        else:
            print_instructions(sys.argv[0])
            sys.exit(2)
        sys.exit(0)

    elif len(sys.argv) == 2:
        if 'stop' == sys.argv[1]:
            server = SelectServer(pidfile, "", 5453)  # only pidfile has to be correct here
            server.stop()
        else:
            print_instructions(sys.argv[0])
            sys.exit(2)
        sys.exit(0)

    else:
        print_instructions(sys.argv[0])
        sys.exit(2)


if __name__ == "__main__":
    main()