import socket
 
target_host = "192.168.56.1"
target_port = 80
 
# create socket
# AF_INET 代表使用標準 IPv4 位址或主機名稱
# SOCK_STREAM 代表這會是一個 TCP client
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
# client 建立連線
client.connect((target_host, target_port))

while True:
    # 傳送資料給 target
    msg = input('Message: ')
    client.sendall(msg.encode('utf-8'))
 
    # 接收資料
    response = client.recv(1024)
 
    # 印出資料信息
    print (response.decode('utf-8'))
