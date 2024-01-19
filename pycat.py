# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# Press Ctrl+F8 to toggle the breakpoint.
# Press the green button in the gutter to run the script.
import argparse
import socket
import shlex
import subprocess
import sys
import textwrap
import threading

def execute(cmd):
    cmd=cmd.strip()
    if not cmd:
        return("Enter a command")
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    return output.decode()

class PyCat:

    def __init__(self, args, buffer=None):
        self.args = args
        self.buffer = buffer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        if self.args.listener:
            self.listen()
        else:
            self.send()

    def listen(self):
        print(f"Binding to {self.args.target}:{self.args.port}")
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)
        while True:
            client_socket, _ = self.socket.accept()
            client_thread = threading.Thread(
                target=self.handle, args=(client_socket,)
            )
            client_thread.start()

    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.send(self.buffer)

        try:
            while True:
                recv_len = 1
                response = ""
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()
                    if recv_len < 4096:
                        break
                if response:
                    print(response)
                    buffer = input('> ')
                    buffer += '\n'
                    self.socket.send(buffer.encode())
        except KeyboardInterrupt:
            print("USER CMD EXIT RECEIVED...")
            self.socket.close()
            sys.exit()

    def handle(self, client_socket):
        if self.args.execute:
            output = execute(self.args.execute)
            client_socket.send(output.encode())

        elif self.args.upload:
            file_buffer = b''
            while True:
                data = client_socket.recv(4096)
                if data:
                    file_buffer += data
                else:
                    break

            with open(self.args.upload, 'wb') as f:
                f.write(file_buffer)

            msg = f'Saved file {self.args.upload}'
            client_socket.send(msg.encode())

        elif self.args.command:
            cmd_buffer = b''
            while True:
                try:
                    client_socket.send(b'PyCat: $> ')
                    while "\n" not in cmd_buffer.decode():
                        cmd_buffer += client_socket.recv(64)
                    resp = execute(cmd_buffer.decode())
                    if resp:
                        client_socket.send(resp.encode())
                    cmd_buffer = b''
                except Exception as e:
                    print(f'Server died. {e}')
                    self.socket.close()
                    sys.exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Netcat in Python3.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Example:
            netcat.py -t 10.10.10.8 -p 5555 # Connect to server
            netcat.py -t 10.10.10.8 -p 5555 -c # Command shell
            netcat.py -t 10.10.10.8 -p 5555 -u=file.txt # Upload file
            netcat.py -t 10.10.10.8 -p 5555 -e=\"cat /etc/passwd\" # Execute command and return output
            echo "TEST" | ./pycat.py -t 10.10.10.8 -p 999 # Echo text to server port 999
        ''')
    )
    parser.add_argument('-t', '--target', default='127.0.0.1', help='Target IP address')
    parser.add_argument('-p', '--port', type=int, default=8000, help='Taget port')
    parser.add_argument('-c', '--command', action='store_true', help='Command shell')
    parser.add_argument('-e', '--execute', help='Execute a command')
    parser.add_argument('-u', '--upload', help='Upload specified file')
    parser.add_argument('-l', '--listener', action='store_true', help='Listen')

    args = parser.parse_args()
    if args.listener:
        buffer = ''
    else:
        buffer = sys.stdin.read()

    nc = PyCat(args, buffer.encode())
    nc.run()
