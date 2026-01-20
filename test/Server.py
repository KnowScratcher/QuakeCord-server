import socket
import threading
 
bind_ip = "192.168.56.1"
bind_port = 80
 
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
server.bind((bind_ip, bind_port))
            
server.listen(5)
 
print ("[*] Listening on %s:%d" % (bind_ip, bind_port))
 
def handle_client(client_socket):
    
    request = client_socket.recv(1024)
    print ("[*] Received: %s" % request)

    msg = input('Message: ')
    client_socket.send(msg.encode('utf-8'))
    #client_socket.close()
    
while True:
    client, addr = server.accept()
    print ("[*] Acepted connection from: %s:%d" % (addr[0],addr[1]))


    client_handler = threading.Thread(target=handle_client, args=(client,))
    client_handler.start()
