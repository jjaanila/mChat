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
    cl.quit()

def main():
    no_newline_test()
