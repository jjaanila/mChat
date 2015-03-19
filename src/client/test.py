from client import Client

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
    cl = Client("tester", prints_disabled=True)
    cl.connect("localhost", 6061)
    cl.sendString("-")  # no newline here
    # input line for keeping the socket open
    input("press enter to quit")
    cl.disconnect()

def quick_resend_test():
    """
    The test connects to server, sends a longish string
    and quickly repeats this. The server crashes to
    an unhandled exception in this case.
    """
    cl = Client("tester", prints_disabled=True)
    buf = "\n"*2**12
    for i in range(2):
        cl.connect("localhost", 6061)
        cl.sendString(buf)
        cl.disconnect()

def main():
    """
    Some simple test cases.
    Changing the test is only possible by
    commenting the function calls..
    """
    # no_newline_test()
    quick_resend_test()

if __name__ == "__main__":
    main()
