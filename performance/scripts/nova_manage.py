import sys
import ssh
import datetime

host = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]
command = sys.argv[4]

print host, username, password, command

client = ssh.Client(host, username, password)
status, output = client.exec_command(command)
print status, output


