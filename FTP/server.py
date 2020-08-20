import os
from time import *
from socket import *
import threading
import re
import pymysql
import json
import atexit
import copy
import random
root_dir=os.getcwd()+"/../root/"
alloc_port_start=50000
alloc_port_end=60000
alloc_port=[i for i in range(alloc_port_start,alloc_port_end)]
send_client_ip="122.51.252.101"
bind_ip="0.0.0.0"
bind_port=7777
read_file_size=300
recv_data_size=10000
database_user="root"
database_pass="abcABC1870178261!"
database_ip="127.0.0.1"
database="ftp"
response='{"type":"","filename":"","md5":"","content":"","id":"","startflag":"","endflag":"","showlist":"","username":"","password":"","statusflag":"","binaryflag":"","errortype":"","ip_port":"","isclose":"","cookie":""}'
cookie=[]					#存放每个用户的cookie
send_to_client_error_port=60000


def verify_login(sql):		#用户登录时验证密码和账号
	global database_pass,database_user
	db = pymysql.connect(database_ip,database_user,database_pass,database)		#连接数据库
	cursor = db.cursor()					#创建一个数据库游标
	result=cursor.execute(sql)						#执行sql语句
	cursor.close()
	db.close()
	return result							#返回是否连接成功   返回个数




def deal_request(deal_client_sock,client_addr):
	while True:
		recv_buf,client_addr=deal_client_sock.recvfrom(recv_data_size)
		recv_buf=recv_buf.decode("utf-8")
		recv_buf=json.loads(recv_buf)
		if recv_buf["cookie"] not in cookie:										#cookie错误
			error_msg="error"
			deal_client_sock.sendto(error_msg.encode("utf-8"),(client_addr[0],send_to_client_error_port))			#发送错误消息	   终止客户端
			alloc_port.append(int(client_addr[1]))									#回收分配的端口号
			return 0																#释放线程
		if recv_buf["type"]=="end":
			alloc_port.append(int(client_addr[1]))									#回收分配的端口号
			cookie.remove(recv_buf["cookie"])										#移除cookie
			print(client_addr," disconnect")
			return 0																#释放线程
		if recv_buf["type"]=="showlist":
			deal_show_list(deal_client_sock,client_addr)
		elif recv_buf["type"]=="upload":
			deal_file_upload(deal_client_sock,client_addr,recv_buf)						#recv_buf已经是字典形式
		elif recv_buf["type"]=="download":
			deal_file_download(deal_client_sock,client_addr,recv_buf)


def create_thread_for_client(addr):
	global alloc_port,cookie,response
	index=random.randint(alloc_port_start,alloc_port_end)-alloc_port_start
	port=alloc_port[index]		#随机生成一个端口号和客户端进行通信
	client_addr=copy.copy(addr)				#客户端地址
	send_buf=copy.copy(response)
	send_buf=json.loads(send_buf)
	send_buf["ip_port"]=[send_client_ip,port]
	deal_client_sock=socket(AF_INET,SOCK_DGRAM)
	deal_client_sock.bind((bind_ip,port))    						#绑定到处理客户端的port
	listen_sock.sendto((json.dumps(send_buf)).encode("utf-8"),client_addr)					#告知客户端新的地址即port
	while True:
		recv_buf,client_addr=deal_client_sock.recvfrom(recv_data_size)
		recv_buf=recv_buf.decode("utf-8")
		recv_buf=json.loads(recv_buf)
		username=recv_buf["username"]
		password=recv_buf["password"]
		sql="select * from ftp where username='{}' and password='{}'".format(username,password)
		result=verify_login(sql)
		if result==0:									#表示登录失败
			return_msg="no"
			deal_client_sock.sendto(return_msg.encode("utf-8"),client_addr)
		else:
			client_cookie=str(hash(time()))   	#获取当前时间作为cookie
			cookie.append(client_cookie)
			send_buf=copy.copy(response)
			send_buf=json.loads(send_buf)
			send_buf["cookie"]=client_cookie
			send_buf=json.dumps(send_buf)
			deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
			break

	deal_request(deal_client_sock,client_addr)

def deal_show_list(deal_client_sock,client_addr):
	global root_dir,response
	listdir=os.listdir(root_dir)
	showlist=""
	for i in listdir:
		showlist=showlist+i+"\n"
	send_buf=copy.copy(response)
	send_buf=json.loads(send_buf)
	send_buf["showlist"]=showlist
	send_buf=json.dumps(send_buf)
	deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)

def verify_md5(deal_client_sock,client_addr,recv_buf):
	content=recv_buf["content"]
	md5=recv_buf["md5"]
	endflag=recv_buf["endflag"]
	filename=recv_buf["filename"]
	file_id=recv_buf["id"]

def deal_file_upload(deal_client_sock,client_addr,recv_buf):
	filename=recv_buf["filename"]
	listdir=os.listdir(root_dir)
	while True:
		if filename in listdir:
			filename+="1"
		else:
			break
	fp=open(root_dir+filename,"w",encoding = 'ISO-8859-1')
	s_file_id=0
	while True:
		send_buf=copy.copy(response)
		send_buf=json.loads(send_buf)
		content=recv_buf["content"]
		md5=recv_buf["md5"]
		endflag=recv_buf["endflag"]
		c_file_id=recv_buf["id"]
		if int(endflag) !=1:				#表示没有结束
			if 0 or int(c_file_id)!=s_file_id+1:			#表示文件传输错误	md5!=str(hash(content))
				fp.close()
				os.remove(root_dir+filename)
				send_buf["errortype"]="error"
				send_buf=json.dumps(send_buf)
				deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
				return 0
			else:	
				send_buf["errortype"]="success"
				send_buf=json.dumps(send_buf)
				deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)														#表示文件没有错误
				fp.write(content)
				s_file_id+=1												#表示成功传输的次数
		else:								#表示发送结束
			fp.close()
			send_buf["content"]=filename+" upload success"
			send_buf=json.dumps(send_buf)
			deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
			break

		recv_buf,client_addr=deal_client_sock.recvfrom(recv_data_size)
		recv_buf=recv_buf.decode("utf-8")
		recv_buf=json.loads(recv_buf)
	print(client_addr," upload "+filename," success")

def md5_digest(content,send_buf,file_id,endflag,filename):
	send_buf=json.loads(send_buf)
	send_buf["content"]=content
	send_buf["md5"]=str(hash(content))
	send_buf["id"]=str(file_id)
	send_buf["endflag"]=str(endflag)
	send_buf["type"]="download"
	send_buf["filename"]=filename
	send_buf=json.dumps(send_buf)
	return send_buf

def deal_file_download(deal_client_sock,client_addr,recv_buf):
	filename=recv_buf["filename"]
	listdir=os.listdir(root_dir)
	send_buf=copy.copy(response)
	send_buf=json.loads(send_buf)
	if filename not in listdir:
		send_buf["errortype"]="error"
		send_buf=json.dumps(send_buf)
		deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
		return 0
	send_buf["errortype"]="sccess"
	send_buf=json.dumps(send_buf)
	deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
	fp=open(root_dir+filename,"r",encoding = 'ISO-8859-1')
	file_id=0
	while True:
		file_id+=1
		send_buf=copy.copy(response)
		content=fp.read(read_file_size)
		if content=="":								#表示文件读取完成
			endflag=1								#表示文件读取完
			send_buf=md5_digest(content,send_buf,file_id,endflag,filename)
			deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
			print(filename+" transfer finish")
			fp.close()
			break
		else:
			endflag=0								#表示文件没有传输完
			send_buf=md5_digest(content,send_buf,file_id,endflag,filename)
			deal_client_sock.sendto(send_buf.encode("utf-8"),client_addr)
			recv_buf,client_addr=deal_client_sock.recvfrom(recv_data_size)
			recv_buf=recv_buf.decode("utf-8")
			recv_buf=json.loads(recv_buf)
			if recv_buf["errortype"]=="error":					#表示文件传输出错
				print(filename+" transfer error")
				fp.close()
				return 0
	print(client_addr," download ",filename," success")



listen_sock=socket(AF_INET,SOCK_DGRAM)
listen_sock.bind((bind_ip,bind_port))
while True:
	recvmsg,client_addr=listen_sock.recvfrom(recv_data_size)
	print(client_addr," connected")
	t=threading.Thread(target=create_thread_for_client,args=(client_addr,))
	t.start()
