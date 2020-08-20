import os
from time import *
from socket import *
import threading
import re
import pymysql
import json
import atexit
import copy
root_dir=os.getcwd()+"/../root/"
server_ip="122.51.252.101"
server_port=7777
read_file_size=300
recv_size=10000
deal_error_port=60000
local_ip="0.0.0.0"
request='{"type":"","filename":"","md5":"","content":"","id":"","startflag":"","endflag":"","showlist":"","username":"","password":"","statusflag":"","binaryflag":"","errortype":"","ip_port":"","isclose":"","cookie":""}'

def menu():
	print("----------------------------------------------------------------")
	print("----------------------------------------------------------------")
	print("------                                                    ------")
	print("------                   	list                         ------")
	print("------                                                    ------")
	print("------                    1.显示文件列表                	 ------")
	print("------                    2.上传文件                       ------")
	print("------                    3.下载文件                       ------")
	print("------                    4.退出                          ------")
	print("------                                                    ------")
	print("------                                                    ------")
	print("----------------------------------------------------------------")
	print("----------------------------------------------------------------")

def login(sock):
	global request,server_ip,server_port
	temp_msg=""
	sock.sendto(temp_msg.encode("utf-8"),(server_ip,server_port))
	recv_buf,server_new_addr=sock.recvfrom(recv_size)
	recv_buf=recv_buf.decode("utf-8")
	recv_buf=json.loads(recv_buf)
	server_new_addr=(recv_buf["ip_port"][0],recv_buf["ip_port"][1])				#构造成元祖
	while True:
		username=input("username>>:").strip()
		password=input("password>>:").strip()
		request=json.loads(request)
		request["username"]=username
		request["password"]=password
		request=json.dumps(request)
		sock.sendto(request.encode("utf-8"),server_new_addr)
		recv_buf,server_new_addr=sock.recvfrom(recv_size)
		if recv_buf!=b"no":
			recv_buf=recv_buf.decode("utf-8")
			recv_buf=json.loads(recv_buf)
			request=json.loads(request)
			request["cookie"]=recv_buf["cookie"]
			request=json.dumps(request)
			return server_new_addr
		else:
			pass


def show_list():
	global sock,server_new_addr
	send_buf=copy.copy(request)
	send_buf=json.loads(send_buf)
	send_buf["type"]="showlist"
	send_buf=json.dumps(send_buf)
	sock.sendto(send_buf.encode("utf-8"),server_new_addr)
	recv_buf,server_new_addr=sock.recvfrom(recv_size)
	recv_buf=recv_buf.decode("utf-8")
	recv_buf=json.loads(recv_buf)
	print(recv_buf["showlist"])

def md5_digest(content,send_buf,file_id,endflag,filename):
	send_buf=json.loads(send_buf)
	send_buf["content"]=content
	send_buf["md5"]=str(hash(content))
	send_buf["id"]=str(file_id)
	send_buf["endflag"]=str(endflag)
	send_buf["type"]="upload"
	send_buf["filename"]=filename
	send_buf=json.dumps(send_buf)
	return send_buf



def upload_file():
	global sock,server_new_addr,request
	listdir=os.listdir(root_dir)
	while True:
		file_path=input("input file name>>:").strip()
		filename=re.findall(r'[^\\/:*?"<>|\r\n]+$',file_path)[0]				#获取文件名   在网上搜的
		if filename not in listdir:
			continue
		elif not os.path.isfile(root_dir+file_path):
			print("please input file name,not folder")
		else:
			break
	fp=open(root_dir+filename,"r",encoding = 'ISO-8859-1')
	file_id=0									#标志是否出现错误   表示一个文件第几次传输
	while True:
		file_id+=1
		send_buf=copy.copy(request)
		content=fp.read(read_file_size)
		if content=="":															#表示传输完成
			endflag=1
			send_buf=md5_digest(content,send_buf,file_id,endflag,filename)
			sock.sendto(send_buf.encode("utf-8"),server_new_addr)
			recv_buf,server_new_addr=sock.recvfrom(recv_size)						#每次传输都会有一个确认机制     在应用层保证传输的正确性
			recv_buf=recv_buf.decode("utf-8")
			recv_buf=json.loads(recv_buf)
			print(recv_buf["content"])
			if recv_buf["errortype"]=="error":
				print("file transfer error,please renew transfer")
				upload_file()
				return 0
			break
		else:
			endflag=0
			send_buf=md5_digest(content,send_buf,file_id,endflag,filename)
			sock.sendto(send_buf.encode("utf-8"),server_new_addr)
			recv_buf,server_new_addr=sock.recvfrom(recv_size)						#每次传输都会有一个确认机制     在应用层保证传输的正确性
			recv_buf=recv_buf.decode("utf-8")
			recv_buf=json.loads(recv_buf)
			if recv_buf["errortype"]=="error":
				print("file transfer error,please renew transfer")
				upload_file()
				return 0
	#recv_buf,server_new_addr=sock.recvfrom(recv_size)
	#recv_buf=recv_buf.decode("utf-8")
	#recv_buf=json.loads(recv_buf)
	#print(recv_buf["content"])


def download_file():
	global sock,server_new_addr,request
	filename=input("filename>>:").strip()
	send_buf=copy.copy(request)
	send_buf=json.loads(send_buf)
	send_buf["filename"]=filename
	send_buf["type"]="download"
	send_buf=json.dumps(send_buf)
	sock.sendto(send_buf.encode("utf-8"),server_new_addr)
	recv_buf,server_new_addr=sock.recvfrom(recv_size)
	recv_buf=recv_buf.decode("utf-8")
	recv_buf=json.loads(recv_buf)
	if recv_buf["errortype"]=="error":					#验证文件是否存在    不存在时文件传输结束
		print(filename+" not exist")
		return 0
	listdir=os.listdir(root_dir)
	while True:
		if filename in listdir:
			filename="1"+filename
		else:
			break
	fp=open(root_dir+filename,"w",encoding = 'ISO-8859-1')
	file_id=0
	while True:
		send_buf=copy.copy(request)
		send_buf=json.loads(send_buf)								#字典类型
		recv_buf,server_new_addr=sock.recvfrom(recv_size)
		recv_buf=recv_buf.decode("utf-8")
		recv_buf=json.loads(recv_buf)
		s_file_id=recv_buf["id"]
		content=recv_buf["content"]
		endflag=recv_buf["endflag"]
		md5=recv_buf["md5"]
		if int(endflag) == 0:												#表示文件传输没有结束
			if file_id+1 !=int(s_file_id):								#md5!=str(hash(content))			表示文件传输出错
				fp.close()
				os.remove(root_dir+filename)
				send_buf["errortype"]="error"
				send_buf=json.dumps(send_buf)
				sock.sendto(send_buf.encode("utf-8"),server_new_addr)
				return 0												#传输出错退出文件传输
			else:
				file_id+=1
				fp.write(content)
				send_buf["errortype"]="success"							#告知服务器端这个包没有错					确认机制
				send_buf=json.dumps(send_buf)
				sock.sendto(send_buf.encode("utf-8"),server_new_addr)
		else:															#表示文件传输结束    
			print(filename+" transfer finish")							
			fp.close()
			break

def end_deal(sock,server_new_addr):				#注册的程序终止时的处理释放资源的函数
	global request
	send_buf=copy.copy(request)
	send_buf=json.loads(send_buf)
	send_buf["type"]="end"
	send_buf=json.dumps(send_buf)
	sock.sendto(send_buf.encode("utf-8"),server_new_addr)


def deal_error():
	error_deal_sock=socket(AF_INET,SOCK_DGRAM)
	error_deal_sock.bind((local_ip,deal_error_port))
	recv_buf,server_new_addr=error_deal_sock.recvfrom(recv_size)
	if recv_buf==b"error":
		exit(0)											#终止程序
sock=socket(AF_INET,SOCK_DGRAM)
server_new_addr=login(sock)
menu()
atexit.register(end_deal,sock,server_new_addr)
#t=threading.Thread(target=deal_error,args=())
#t.start()
while True:
	num=input("choose>>").strip()	#选择的编号
	if (num)=="1":
		show_list()
	elif (num)=="2":
		upload_file()
	elif (num)=="3":
		download_file()
	elif (num)=="4":
		break
	else:
		print("tip:\n\tinput error pleace input number\n")