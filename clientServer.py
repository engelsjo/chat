'''
@author: Joshua Engelsma

Created 9/15/2014

@summary: Python program acts as a server-client.
'''

import select
import socket
import sys
import signal

BUFSIZ = 1024


class ChatServer(object):
    def __init__(self, port=3490, backlog=5):
        self.clients = 0
        self.clientmap = {}
        self.groupmap = {}
        self.outputs = []
        self.inputs = []
        self.adminPassword = 'fuzzybunnies'
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('',port))
        print ('Listening to port'.format(port))
        self.server.listen(backlog)
        signal.signal(signal.SIGINT, self.sighandler)
        
    def sighandler(self, signum, frame):
        print ('Shutting down server...')
        for o in self.outputs:
            o.close() 
        self.server.close()
        
    def getname(self, client):
    	return self.clientmap[client][1]

    def getHelp(self, client):
    	helpCmd = '''
    		LIST OF USER CHAT COMMANDS:
    		
    		help - provide list of all chat commands
    		list - provide list of all users online
    		send user  message- send a message to a user on the network
    		sendall message- send a message to everyone on the network.
    		sendgroup group message- send a message to a named group
    		
    		LIST OF ADMINISTRATOR COMMANDS:
    		
    		kick user password - as admin kick a user.
    		joingroup group password - as admin join a listed group
    		creategroup name users password- create a group of users.
    		listgroups password - list all active groups
    		removegroup group password - remove active group
    		addgroupuser user group password - add user to group
    	'''
    	for o in self.outputs:
    		if o == client:
    			o.send(helpCmd)
    			
    def getListOfUsers(self, client):
    	users = []
    	for keyClient in self.clientmap:
    		clientInfo = self.clientmap[keyClient]
    		users.append(clientInfo[1])
    	listOfUsers = 'Online Users ' + str(users)
    	for o in self.outputs:
    		if o == client:
    			o.send(listOfUsers)
    			
    def sendMessageToAll(self, client, arguments):
    	for o in self.outputs:
    		if o != client: #send to everyone except ourselves.
    			msg = ''
    			for arg in arguments:
    				msg += (arg + ' ')
    			p = '{}: '.format(self.getname(client))
    			o.send(p + msg)
    			
    def sendMessage(self, client, arguments):
    	if len(arguments) < 2:
    		e = 'To send a message you need two arguments. A user, and a message'
    		self.errorMessage(client, '', e)
    		return
    	for key in self.clientmap:
    		user = self.clientmap[key][1]
    		if user == arguments[0]:
    			msg = ''
    			for arg in range(1, len(arguments)):
    				msg += (arguments[arg] + ' ')
    			for o in self.outputs:
    				if o == key:
    					p = '{}: '.format(self.getname(client))
    					o.send(p + msg)
    					return
    	e = 'User {} is not connected.'.format(arguments[0])
    	self.errorMessage(client, '', e)
    	
    def adminKick(self, client, arguments):
    	if len(arguments) < 2:
    		e = 'To kick a user you must specify the user and enter the password'
    		self.errorMessage(client, '', e)
    		return
    	if arguments[1] != self.adminPassword:
    		e = 'Invalid password. Unable to kick user'
    		self.errorMessage(client, '', e)
    		return
    	usr = arguments[0]
    	for gkey in self.groupmap: #remove user from all groups
    			if usr in self.groupmap[gkey]:
    				self.groupmap[gkey].remove(usr)
    	for key in self.clientmap:
    		usr = self.clientmap[key][1]
    		if usr == arguments[0]:
    			for o in self.outputs:
    				if o == key:
    					o.send('Shutdown')
    					self.inputs.remove(o)
    					self.outputs.remove(o)
    					self.clientmap.pop(key)
    					key.close()
    					o.close()
    					return
    					
    def adminCreateGroup(self, client, arguments):
    	if len(arguments) < 3:
    		e = 'To create group you must specify group name, users, and admin password'
    		self.errorMessage(client, '', e)
    		return
    	if arguments[len(arguments)-1] != self.adminPassword:
    		e = 'Invalid password. Unable to create group'
    		self.errorMessage(client, '', e)
    		return
    	groupName = arguments[0]
    	if groupName in self.groupmap:
    		e = 'group name already exists'
    		self.errorMessage(client, '', e)
    		return
    	self.groupmap[groupName] = []
    	for i in range(1, len(arguments)-1): # add all specified users online to your group
    		userNameToAdd = arguments[i]
    		if not self.isUserOnline(userNameToAdd):
    			e = '''user {} is not online and can't be added to group 
    			- try again'''.format(userNameToAdd)
    		else:
    			self.groupmap[groupName].append(userNameToAdd)
    	usr = ''
    	for key in self.clientmap: #send all added users a message saying they can join
    		usr = self.clientmap[key][1]
    		if usr in self.groupmap[groupName]:
    			for o in self.outputs:
    				if o == key:
    					o.send(''''You have been added to the group - {} - feel free to join.'''.format(groupName))
    		
    def listGroups(self, client, arguments):
    	if len(arguments) < 1:
    		e = 'To list groups you must enter admin password'
    		self.errorMessage(client, '', e)
    		return
    	if arguments[0] != self.adminPassword:
    		e = 'Invalid password. Unable to show you groups'
    		self.errorMessage(client, '', e)
    		return
    	allGroups = []
    	for key in self.groupmap:
    		groupString = key + str([usr for usr in self.groupmap[key]])
    		allGroups.append(groupString)
    	for o in self.outputs:
    		if o == client:
    			o.send(str(allGroups))
    			
    def removeGroup(self, client, arguments):
    	if len(arguments) < 2:
    		e = 'To remove group you must enter group name and admin password'
    		self.errorMessage(client, '', e)
    		return
    	if arguments[1] != self.adminPassword:
    		e = 'Invalid password. Unable to show you groups'
    		self.errorMessage(client, '', e)
    		return
    	if arguments[0] not in self.groupmap:
    		e = '{} is not an active group. You can not remove non-existent group'
    		self.errorMessage(client, '', e)
    		return
    	self.groupmap.pop(arguments[0])
    	
    def sendGroupMessage(self, client, arguments):
    	if len(arguments) < 2:
    		e = 'To send group message, you must enter group name and message'
    		self.errorMessage(client, '', e)
    		return
    	if arguments[0] not in self.groupmap:
    		e = 'group {} has not been set up by an admin'.format(arguments[0])
    		self.errorMessage(client, '', e)
    		return
    	usr = ''
    	usr = self.clientmap[client][1]
    	if usr not in self.groupmap[arguments[0]]:
    		e = 'You are not a part of this group and cannot send a message'
    		self.errorMessage(client, '', e)
    		return
    	listOfGroup = self.groupmap[arguments[0]]
    	msg = ''
    	for arg in range(1, len(arguments)):
    		msg += (arguments[arg] + ' ')
    	for key in self.clientmap:
    		usr = self.clientmap[key][1]
    		if usr in listOfGroup:
    			for o in self.outputs:
    				if o == key:
    					p = '{}: '.format(self.getname(client))
    					o.send(p + msg)
    					
    def joinGroup(self, client, arguments):
    	if len(arguments) < 2:
    		e = 'To send group message, you must enter group name and password'
    		self.errorMessage(client, '', e)
    		return
    	groupName = arguments[0]
    	password = arguments[1]
    	usrJoining = ''
    	usrJoining = self.clientmap[client][1]
    	if groupName not in self.groupmap:
    		e = 'group {} has not been set up by an admin'.format(arguments[0])
    		self.errorMessage(client, '', e)
    		return
    	if password != self.adminPassword:
    		e = 'Invalid admin password'
    		self.errorMessage(client, '', e)
    		return
    	self.groupmap[groupName].append(usrJoining)
    	for o in self.outputs:
    		if o == client:
    			o.send('you have been added to group {}'.format(groupName))
    			
    def addUserToGroup(self, client, arguments):
    	if len(arguments) < 3:
    		e = 'To add a user to a group you must pass the user, group name and password'
    		self.errorMessage(client, '', e)
    	usr = arguments[0]
    	group = arguments[1]
    	password = arguments[2]
    	if not self.isUserOnline(usr):
    		e = 'User is not online, and can not be added to the group'
    		self.errorMessage(client, '', e)
    		return
    	if group not in self.groupmap:
    		e = 'Group {} has not been created.'.format(group)
    		self.errorMessage(client, '', e)
    		return
    	if password != self.adminPassword:
    		e = 'Invalid admin password'
    		self.errorMessage(client, '', e)
    		return
    	self.groupmap[group].append(usr)
    	for key in self.clientmap:
    		user = self.clientmap[key][1]
    		if user == usr:
    			for o in self.outputs:
    				if o == key:
    					o.send('you have been added to group - {} - feel free to join'.format(group))
    					return    			
    						
    def errorMessage(self, client, data, errorMsg=''):
    	error = '"{}" is not a valid command. Press help for valid commands.'.format(data)
    	if errorMsg != '':
    		error = errorMsg
    	for o in self.outputs:
    		if o == client:
    			o.send(error)
    			
    def isUserOnline(self, userName):
    	for key in self.clientmap:
    		usr = self.clientmap[key][1]
    		if usr == userName:
    			return True
    	return False
    		   
    def handleClientData(self, data, client):
    	instructions = data.split(' ')
    	cmd = instructions[0].strip()
    	arguments = []
    	if len(instructions) > 1:
    		for i in range(1, len(instructions)):
    			arguments.append(instructions[i])
    	if cmd == 'help': self.getHelp(client); return;
    	if cmd == 'list': self.getListOfUsers(client); return;
    	if cmd == 'sendall': self.sendMessageToAll(client, arguments); return;
    	if cmd == 'send': self.sendMessage(client, arguments); return;
    	if cmd == 'kick': self.adminKick(client, arguments); return;
    	if cmd == 'creategroup': self.adminCreateGroup(client, arguments); return;
    	if cmd == 'listgroups': self.listGroups(client, arguments); return;
    	if cmd == 'removegroup': self.removeGroup(client, arguments); return;
    	if cmd == 'sendgroup': self.sendGroupMessage(client, arguments); return;
    	if cmd == 'joingroup': self.joinGroup(client, arguments); return;
    	if cmd == 'addgroupuser': self.addUserToGroup(client, arguments); return;
    	self.errorMessage(client, data)
    	
    def serve(self):
        
        self.inputs = [self.server,sys.stdin]
        self.outputs = []

        running = 1

        while running:

            try:
                inputready,outputready,exceptready = select.select(self.inputs, self.outputs, [])
            except select.error, e:
                break
            except socket.error, e:
                break

            for s in inputready:

                if s == self.server:
                    # handle the server socket
                    client, address = self.server.accept()
                    print 'chatserver: got connection {} from {}'.format(client.fileno(), address)
                    # Read the login name
                    cname = client.recv(BUFSIZ).split('NAME: ')[1]
                    
                    	
                    
                    # Compute client name and send back
                    self.clients += 1
                    client.send('CLIENT: ' + str(address[0]))
                    self.inputs.append(client)

                    self.clientmap[client] = (address, cname)
                    # Send joining information to other clients
                    msg = 'Connected a new client'
                    for o in self.outputs:
                        o.send(msg)
                    
                    self.outputs.append(client)
                    	

                elif s == sys.stdin:
                    # handle standard input
                    junk = sys.stdin.readline()
                    running = 0
                else:
                    # handle all other sockets
                    try:
                        data = s.recv(BUFSIZ)
                        if data:
                            self.handleClientData(data, s)
                        else:
                            print 'chatserver: %d hung up' % s.fileno()
                            self.clients -= 1
                            s.close()
                            self.inputs.remove(s)
                            self.outputs.remove(s)

                            # Send client leaving information to others
                            msg = 'A client has hung up'
                            usr = self.clientmap[s][1]
                            for key in self.groupmap:
                            	if usr in self.groupmap[key]:
                            		self.groupmap[key].remove(usr)
                            self.clientmap.pop(s) 
                            for o in self.outputs:
                                # o.send(msg)
                                o.send(msg)
                                
                    except socket.error, e:
                        # Remove
                        self.inputs.remove(s)
                        self.outputs.remove(s)
                        


        self.server.close()

if __name__ == "__main__":
    ChatServer().serve()
    