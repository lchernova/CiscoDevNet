from netmiko import Netmiko
from tkinter import *
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
import netmiko.ssh_exception
import logging
import os
import time
import argparse

#sets cli parameters
def cliparse():

    cliparser = argparse.ArgumentParser(description = 'Cisco config analyzer')
    cliparser.add_argument('-d', metavar='devices', type=str, default='hosts',
                            help='Specify the file with list of hosts. Default filename is "hosts". Specifying hosts explicitly takes precedence over file')
    cliparser.add_argument('-t', metavar='threads', type=int, 
                            help='Specify number of threads while connecting to other devices', default=1)
    cliparser.add_argument('-f', metavar='file', type=str, default='commands',
                            help='Specify the file with list of commands. Default filename is "commands". Specifying the key "-c" takes precedence over the file')
    cliparser.add_argument('-l', metavar='level', type=str, default='INFO',
                            help='Specify severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    args=cliparser.parse_args()
    args.hosts = [line.rstrip('\n') for line in open(args.d)]
    args.c = [line.rstrip('\n') for line in open(args.f)]
    return args

#connecting to the single device, using deviceIP IP, creds{'uname':username, 'pwd':password}, logger object, cli command
#connects to the device, sends single command, writes output to file and returns result    
def parser_sh_cdp(output) :
    peers = 0
    if output.startswith("% CDP is not enabled") :
        cdp = "CDP is OFF"
        peers = 0
    else :
        cdp = "CDP is ON"
        peers = output.count("Device ID")
    return("%s,%s peers" % (cdp, peers))
def parser_sh_ntp(output) :
    ntp_list = output.split(",")
    return("%s-%s" % (ntp_list[0],ntp_list[2]))
def parser_sh_inv(output, SN) :
    inv_list = output.split("\n\n")
    invent = []
    PID = ""
    for inv in inv_list :
        search1 = re.search('NAME: (".*"), DESCR: (".*")',inv)  
        search2 = re.search('PID: (\S+) *, VID: (.*), SN: (\S+)',inv) 
        if search1  and search2 :
            invent = search1.groups() + search2.groups()
        if invent[4] == SN :
            PID = invent[2]
            break
    return(PID)
def parser_ver_ios(output) :
    SN = ver_ios = ""
    if re.search(".*Cisco IOS Software,.*\((\S+)\),", output) :
        ver_ios = re.search(".*Cisco IOS Software,.*\((\S+)\),", output).group(1)
    if re.search(".*Processor board ID (\S+)", output) :
        SN = re.search(".*Processor board ID (\S+)", output).group(1)
    return(SN,ver_ios)
def sshconnect (deviceIP, creds, logger, cli, date_string):
    uname=creds['uname']
    pwd=creds['pwd']
    rezult = ""
    SN = ""
    logger.info("connecting to %s...", deviceIP)
    try:
        net_connect = Netmiko(
            ip=deviceIP,
            username=uname,
            password=pwd,
            device_type="cisco_ios",
        )
        logger.info("connected to %s", deviceIP)      
        if net_connect:
            prompt = net_connect.find_prompt()
            rez_cdp = rez_ntp = PE_NPE = ver_ios = PID = ""
            for command in cli:
                command_lower = command.lower()
                filename_part3 = command_lower.split("|")[0] 
                logger.info("sending %s to %s" % (command, deviceIP)) 
                if re.search("sh\S* run\S*", command_lower) :
                    file_output=open("data\%s-%s.txt" % (prompt.replace("#",""), date_string), "w")
                else :    
                    file_output=open("data\%s-%s - %s.txt" % (prompt.replace("#",""), date_string, filename_part3), "w")
                if command_lower.startswith("sh") :
                    output = net_connect.send_command(command)
                else :
                    output = net_connect.send_config_set(command)
                if command_lower.find("cdp") > 0 :
                    rez_cdp = parser_sh_cdp(output)
                elif command_lower.find("ntp") > 0 :
                    rez_ntp = parser_sh_ntp(output)
                elif command_lower.find("ver") > 0 :
                    PE_NPE = "PE_NPE"
                    SN,ver_ios = parser_ver_ios(output)
                    if ver_ios.find("NPE") > 0 :
                        PE_NPE = "NPE"
                    else :
                        PE_NPE = "PE"
                elif command_lower.find("inv") > 0  :
                    PID = parser_sh_inv(output,SN)
                file_output.write(output)
                file_output.close()
                rezult = "%s|%s|%s|%s|%s|%s|%s" % (prompt.replace("#",""),PID,SN,ver_ios,PE_NPE,rez_cdp,rez_ntp)
            net_connect.disconnect()
        return rezult
    except Exception:
        print ("Cannot connect to the device %s" % deviceIP)
        logger.error("Cannot connect to the device %s" % deviceIP)
        return

#connecting to several devices using multithreading    
def retrieve_result(hosts, creds, logger, cli,  date_string, thlimit=1):
    with ThreadPoolExecutor(max_workers=thlimit) as executor:
        result = executor.map(sshconnect, hosts, repeat(creds), repeat(logger), repeat(cli), repeat(date_string))
    return list(result)
    
#checking folders
def script_init(folder):        
    if not os.path.exists("log"):
        os.makedirs("log")
    if not os.path.exists("data"):
        os.makedirs("data")

        
#setting initial logging parameters          
def log_settings(loggername, filename, severity):     
    logger = logging.getLogger(loggername)
   
    logger.setLevel(logging.INFO)
    logfh=logging.FileHandler("log/%s.txt" % filename)
    logformatter = logging.Formatter('%(asctime)s: %(name)s: %(levelname)s %(message)s')
    logfh.setFormatter(logformatter)
    logger.addHandler(logfh)
    return logger
