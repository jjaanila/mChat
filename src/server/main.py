from server import MChatServer
import sys


def print_instructions(program_name):
    print("""usage: %s start [--non-daemon] <ip> <client_port> <server_port> [<remote_ip> <remote_port>]
 | stop <ip> <client_port>""" % program_name)


def main():

    try:
        # raises ValueError if not present:
        sys.argv.remove("--non-daemon")
        daemon = False
    except ValueError:
        daemon = True

    if len(sys.argv) == 5 or len(sys.argv) == 7:
        ip = sys.argv[2]
        client_port = int(sys.argv[3])
        server_port = int(sys.argv[4])
        remote_ip = None
        remote_port = None
        pidfile = "/tmp/mchat_" + ip + "_" + str(client_port) + ".pid"
        if len(sys.argv) == 7:
            remote_ip = sys.argv[5]
            remote_port = int(sys.argv[6])

        if 'start' == sys.argv[1]:
            server = MChatServer(pidfile, ip, client_port, server_port, remote_ip, remote_port)
            if daemon:
                server.start()
                print("Server started.")
            else:
                server.run()
        else:
            print_instructions(sys.argv[0])
            sys.exit(2)
        sys.exit(0)

    elif len(sys.argv) == 4:
        pidfile = "/tmp/mchat_" + sys.argv[2] + "_" + sys.argv[3] + ".pid"
        if 'stop' == sys.argv[1]:
            server = MChatServer(pidfile, "", 0, 0)  # only pidfile has to be correct here
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
