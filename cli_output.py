#send the list of commands to the list of hosts and get output in separate files

from netmiko import Netmiko
from netcheck import script_init, retrieve_result, cliparse, log_settings
from getpass import getpass
from itertools import repeat
import time
import datetime

#parse cli arguments
args = cliparse()   

#check folders and create if they do not exist
script_init('cli_output')

#set logger settings. args.l contains logging level      
logger = log_settings('netmiko','cli_output', args.l)  #set logger 'netmiko' and log to file 'config analyzr'
calogger = log_settings('cli_output','cli_output', args.l) #set calogger 'netmiko' and log to file 'config analyzr
calogger.info("cli_output started")   

#Enter credentials uname and pwd and keep it in creds dictionary
creds = dict(uname = input("username:"),pwd = getpass())

#Check the starttime of the program = system time
start_time = time.time()

now = datetime.datetime.now()
date_string = now.strftime('%Y-%m-%d')
result = retrieve_result(args.hosts, creds, logger, args.c, date_string, args.t)
print ('\n'.join(result))
end_time = time.time()
execution_time = end_time - start_time
calogger.info("cli_output stopped")  
calogger.info("cli_output execution time is %f" % execution_time)  
print("Execution time is ", execution_time)
