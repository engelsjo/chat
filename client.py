'''
@author: Joshua Engelsma

Created 9/15/2014

@summary: Python program acts as a client.
'''


import socket
import sys
import select

BUFSIZ = 1024

class ChatClient(object):

    def __init__(self, name, host='127.0.0.1', port=3490):
        self.name = name
        self.flag = False
        self.port = int(port)
        self.host = host
        self.prompt='[{}]> '.format(name)
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, self.port))
            print('You are connected to the chat server!!!')
            self.sock.send('NAME: ' + self.name) 
            data = self.sock.recv(BUFSIZ)
            addr = data.split('CLIENT: ')[1] #get client address and set it
            self.prompt = '[{}]> '.format(name)
        except socket.error, e:
            print 'Could not connect to chat server @{}'.format(self.port)
            sys.exit(1)

    def cmdloop(self):

        while not self.flag:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                # Wait for input from stdin & socket
                inputready, outputready,exceptrdy = select.select([0, self.sock], [],[])
                
                for i in inputready:
                    if i == 0:
                        data = sys.stdin.readline().strip()
                        if data: self.sock.send(data)
                    elif i == self.sock:
                        data = self.sock.recv(BUFSIZ)
                        if data == 'Shutdown':
                        	print 'Admin booted you from chat.'
                        	self.flag = True
                        	break
                        if not data:
                            print 'Shutting down.'
                            self.flag = True
                            break
                        else:
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()
                            
            except KeyboardInterrupt:
                print 'Interrupted.'
                self.sock.close()
                break
            
            
if __name__ == "__main__":
    import sys

    if len(sys.argv)<3:
        sys.exit('You are not correctly starting up the client')   
    client = ChatClient(sys.argv[1],sys.argv[2], int(sys.argv[3]))
    client.cmdloop()