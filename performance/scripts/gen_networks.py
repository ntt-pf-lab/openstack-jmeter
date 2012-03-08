#!/usr/bin/env python

"""This script should be run after keystone test plan has been run and tenants CSV file is generated"""

import netaddr
import math
import sys
import ssh

if __name__ == "__main__":
 
  host = sys.argv[1]
  username = sys.argv[2]
  password = sys.argv[3]  
  bridge_interface = sys.argv[4]
  bridge = sys.argv[5]
  tenants_file = sys.argv[6] + '/tenants.csv'
  nova_manage_path = sys.argv[7]

  print "Arguments passed to networks creation script are: ", sys.argv


  nova_manage = nova_manage_path + '/nova-manage'
  tenants = open(tenants_file,'r').readlines() 

  ssh_client = ssh.Client(host, username, password)

  cidr = "10.0.0.0/16";
  num_networks = len(tenants)
  network_size  = 16 
  subnet_bits = int(math.ceil(math.log(network_size, 2)))
  fixed_net_v4 = netaddr.IPNetwork(cidr)
  prefixlen_v4 = 32 - subnet_bits
  subnets_v4 = list(fixed_net_v4.subnet(prefixlen_v4,
                         count=num_networks))

  for tenant_row,subnet in zip(tenants,subnets_v4):
      tenant = tenant_row.split(',')[1]
      command = nova_manage + ' network create --label=jm_net --fixed_range_v4=%s --bridge=%s --bridge_interface=%s --project_id=%s' % (subnet, bridge, bridge_interface, tenant)
      print "Running Command: ",command
      res, out = ssh_client.exec_command(command) 
      if not res:
          print "Network creation successful for tenant '%s'" %tenant
          bridge = 'br' + str(int(bridge.split('br')[1]) + 1)
      else:
          print "Could not create this network...Exiting."
          sys.exit(0)

