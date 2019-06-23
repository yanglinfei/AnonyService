import httplib  
import json
import os
import sys
import io
import time
import re
import subprocess
import commands  
      
class StaticFlowPusher(object):  

    def __init__(self, server, ip_list_file_path):  
        self.server = server  
        self.ip_list_file_path = ip_list_file_path
        self.flow_entry_init_time_dict = {}
        self.flow_entry_dict = {}
        self.init_ip_list()
      
    def get(self, data):  
        ret = self.rest_call({}, 'GET')  
        return json.loads(ret[2])  
      
    def set(self, data):  
        ret = self.rest_call(data, 'POST')  
        return ret[0] == 200  
      
    def remove(self, data):  
        ret = self.rest_call(data, 'DELETE')  
        return ret[0] == 200  
      
    def rest_call(self, data, action):  
        path = '/wm/staticflowpusher/json'  
        headers = {  
            'Content-type': 'application/json',  
            'Accept': 'application/json',  
            }  
        body = json.dumps(data)  
        conn = httplib.HTTPConnection(self.server, 8080)  
        conn.request(action, path, body, headers)  
        response = conn.getresponse()  
        ret = (response.status, response.reason, response.read())  
        print ret  
        conn.close()  
        return ret  

    def init_ip_list():
    	f = open(self.ip_list_file_path,'r')
		ip_set_tmp = list()
		for line in open('poem.txt'):
		    line = f.readline()
		    print line
		    ip_list_tmp.append(line)
		self.ip_list = ip_list_tmp

    def getIp(self, srcIp):
    	index = (hash(srcIp) + time.time() * 1000) % len(self.ip_list)
    	ip = self.ip_list[index]
    	self.ip_list.remove(ip)
     	return ip

 	def getSize(self):
 		return len(self.flow_entry_init_time_dict)

    def add_flow_entry(self, flow_entry_name_list, src_ip):
    	timestamp = time.time() * 1000
    	self.flow_entry_init_time_dict[src_ip] = timestamp
    	self.flow_entry_dict[src_ip] = flow_entry_name_list

    def remove_flow_endty_expired(self, expired_threshold):
    	min_timestamp = time.time() * 1000 - expired_threshold
    	for src_ip in flow_entry_init_time_dict:
    		if flow_entry_init_time_dict[src_ip] < min_timestamp:
    			self.flow_entry_init_time_dict.pop(src_ip)
    			flow_entry_name_list = self.flow_entry_dict.pop(src_ip)
    			for entry_name in flow_entry_name_list:
    				self.remove({'name': entry_name})
    				
    def clear_flow_entry_dict(self):
    	self.flow_entry_init_time_dict.clear()
    	self.flow_entry_dict.clear()
    	self.init_ip_list()

# ip池文件地址
ip_set_file_path = "/Users/yanglinfei/ip_set"
# 映射表阈值
threshold = 100
# 映射流表失效时间，单位ms
expired_threshold = 10000

count = 0

pusher = StaticFlowPusher('127.0.0.1', ip_set_file_path)   

def addAnonyItem(src_ip, pusher):
	# 流表项防溢出处理
	if pusher.getSize() > threshold:
		pusher.remove_flow_endty_expired(expired_threshold)

	# 防溢出
	if pusher.getSize() > threshold:
		pusher.clear_flow_entry_dict()

	# 拓扑信息获取
	command = "curl http://127.0.0.1:8080/wm/device/"
	result = commands.getoutput(command)
	#print result
	device = re.search('.*({"devices")(.*}).*',result) 
	topo = device.group(2)
	#print (topo)
	topo='{"devices"'+topo
	print (topo)
	topo = eval(topo)
	#print(type(topo))
	context = topo["devices"]

	j=0

	for i in context:
		if not i["ipv4"]:
			continue
		if i["ipv4"][0]==src_ip:
			src_sw=i["attachmentPoint"][0]["switch"]
			src_port=i["attachmentPoint"][0]["port"]
			print (src_sw)
			src_mac=i["mac"][0]

	# 匿名处理
	neip=pusher.getIp(src_ip)

	# 生成匿名流表
	flow_entry_name_list = []
	flow1_arp = {
		        'switch':"00:00:00:00:00:00:00:01",  
	   		"name":"flow-mod-%s-1" %(count),  
	    		"cookie":"0",  
	    		"priority":"32768",  
	    		"in_port":"2" , 
			"eth_type":"0x806",
			"eth_src":"%s" % (src_mac) ,
	    		"active":"true",  
	    		"actions":"set_field=arp_spa->%s,output=1" %(neip)   
			  }

	flow1_arp_reverse = {
	        'switch':"00:00:00:00:00:00:00:01",  
	   		"name":"flow-mod-%s-2" %(count),  
    		"cookie":"0",  
    		"priority":"32768",  
    		"in_port":"1" , 
		"eth_type":"0x806",
		"eth_dst":"%s" % (src_mac) ,
    		"active":"true",  
    		"actions":"set_field=arp_tpa->%s,output=2" % (src_ip)  
		  }

	flow1 = {  
	    	'switch':"00:00:00:00:00:00:00:01",  
		"name":"flow-mod-%s-3" %(count),  
		"cookie":"0",  
		"priority":"32768",  
		"in_port":"2" , 
		"eth_type":"0x800",
		"ipv4_src":"%s", %(src_ip) 
		"active":"true",  
		"actions":"set_field=ipv4_src->%s,output=1" %(neip)
	    }

	flow1_reverse = {  
	    	'switch':"00:00:00:00:00:00:00:01", 
	   		"name":"flow-mod-%s-4" %(count),  
	  		"cookie":"0",  
		"priority":"32768",  
		"in_port":"1" , 
		"eth_type":"0x800",
		"ipv4_src":"10.0.0.2",
		"ipv4_dst":"%s" %(neip),  
		"active":"true",  
		"actions":"set_field=ipv4_dst->%s,output=2" % (src_ip)
	    }

	flow1_arp_broadcast = {
		        'switch':"00:00:00:00:00:00:00:01", 
	   		"name":"flow-mod-%s-5" %(count),   
	    		"cookie":"0",  
	    		"priority":"32768",  
	    		"in_port":"1" , 
			"eth_type":"0x806",
			"eth_src":"%s" % (dst_mac) ,
			#"eth_dst":"aa:aa:aa:aa:aa:aa" ,
	    		"active":"true",  
	    		"actions":"set_field=arp_tpa->%s,output=2" % (src_ip)  
			  }

	# 流表下发
	pusher.set(flow1_arp)
	pusher.set(flow1)
	pusher.set(flow1_arp_reverse)
	pusher.set(flow1_reverse)
	pusher.set(flow1_arp_broadcast)

	# 流表项缓存
	flow_entry_name_list.append(flow1_arp['name'])
	flow_entry_name_list.append(flow1['name'])
	flow_entry_name_list.append(flow1_arp_reverse['name'])
	flow_entry_name_list.append(flow1_reverse['name'])
	flow_entry_name_list.append(flow1_arp_broadcast['name'])
	pusher.add_flow_entry(flow_entry_name_list, src_ip)

	count = count + 1
	return neip


if __name__ == '__main__':
    while true:
    	src_ip = input("输入需要匿名化的服务端IP:")

    	neip = addAnonyItem(src_ip, pusher)

    	print(neip)

