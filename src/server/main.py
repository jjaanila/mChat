from server import MChatServer
import sys


def print_instructions(program_name):
    print("""usage: %s start [-d] <ip> <client_port> <server_port> [<remote_ip> <remote_port>]
 | restart <ip> <client_port> <server_port>
 | stop""" % program_name)


def main():
    pidfile = "/tmp/select-server-daemon.pid"

    try:
        # raises ValueError if not present:
        sys.argv.remove("-d")
        daemon = True
    except ValueError:
        daemon = False

    if len(sys.argv) == 5 or len(sys.argv) == 7:
        ip = sys.argv[2]
        client_port = int(sys.argv[3])
        server_port = int(sys.argv[4])
        remote_ip = None
        remote_port = None
        if len(sys.argv) == 7:
            remote_ip = sys.argv[5]
            remote_port = int(sys.argv[6])

        if 'start' == sys.argv[1]:
            server = MChatServer(pidfile, ip, client_port, server_port, remote_ip, remote_port)
            if daemon:
                server.start()
            else:
                server.run()
            print("Server started.")
        elif 'restart' == sys.argv[1]:
            # NOTE: This might need some some rethinking when it comes to the parameters
            server = MChatServer(pidfile, ip, client_port, server_port)
            server.restart()
            print("Server restarted.")
        else:
            print_instructions(sys.argv[0])
            sys.exit(2)
        sys.exit(0)

    elif len(sys.argv) == 2:
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
