# An example on how edgepoll act as a local cloud agent with vxlan enabled
 
### This example will bring up a local cloud as below
```
VM1     VM2                  ---
 |_______|                      |_ Server 1
     |                          |
  vSwitch                    ---
     |(vxlan)
  vGateway                   ---
     |                          |- Server 2
    VM3                      ---
```
In details,
```
ERP(docker)     AGVS(vm)
 |_______________|
         |
        vSW(vSwitch)
         | (vxlan)
     vGateway
   (10.10.20.1/24)
         |
        LWA(vm)
```
### Install steps
#### Hardware Environment
Preparing two servers and a Gateway, Server should be Linux system, Ubuntu is preferred.
```
Server 1 --- Gateway --- Server 2
```
 
#### Software environment
  1. install openvswitch
  2. install docker
  3. install qemu
  4. install edgepoll, follow docs/sd-wan-v0.2-install.md
  5. prepare  docker images
```
jiangjqian/edgegate:gatewaybase and jiangjqian/edgegate:ubuntu-net
```
  prepare qemu images, for example
```
/var/lib/libvirt/images/ubuntu16.04-20190514-install-nested-kvm.qcow2
```
 
#### Prepare configure file
Assume server 1 ip is 192.168.0.2, server 2 ip is 192.168.0.11
  * Server 1, copy below configure to /root/.sdwan/edgepoll/cloud.json
```
{ "nodes": [
    {
      "name": "AGVS",
      "type": "vm",
      "image": "/home/richard/data/kvm/ubuntu16.04-20190514-install-nested-kvm.qcow2",
      "net": ["vSW"]
    },
    {
      "name": "ERP",
      "type": "docker",
      "image": "jiangjqian/edgegate:ubuntu-net",
      "net": ["vSW"]
    },
    {
      "name": "vSW",
      "type": "gw2",
      "image": "jiangjqian/edgegate:gatewaybase",
      "vxlan": [{"remote": "192.168.0.11", "dstport": 4789, "vni": 42, "map": 14789}],
      "debug": true
    }
  ]}
```
  * server 2, copy below configure to /root/.sdwan/edgepoll/cloud.json
```
{"nodes": [
    {
      "name": "vGW1046-10.10.20.1",
      "type": "gw2",
      "image": "jiangjqian/edgegate:gatewaybase",
      "ip": "10.10.20.1/24",
      "vxlan": [{"remote": "192.168.0.2", "dstport": 4789, "vni": 42, "map": 14789}],
      "debug": true
    },
    {
      "name": "LWA",
      "type": "vm",
      "image": "/var/lib/libvirt/images/ubuntu16.04-20190514-install-nested-kvm.qcow2",
      "net": ["vGW1046-10.10.20.1"]
    }]}
```
#### Run edgepoll in root user
  * Server 1
```
sudo su
export PYTHONPATH=$PWD && python3 edgepoll/__main__.py --loglevel=10
```
  * Server 2
```
sudo su
export PYTHONPATH=$PWD && python3 edgepoll/__main__.py --loglevel=10
```

#### Check link between AGVS and LWA
  * Server 1
```
ps -ef | grep qemu  # find hostfwd=tcp::40535-:22
ssh -p 40535 richard@127.0.0.1 # pwd: xxxxxx
```
After ssh, we enter AGVS,
```
sudo dhclient ens4 # got IP 10.10.20.112 for example
```  

  * Server 2
```
ps -ef | grep qemu  # find hostfwd=tcp::20535-:22
ssh -p 20535 richard@127.0.0.1 # pwd: xxxxxx
```
After ssh, we enter LWA,
```
sudo dhclient ens4 # got IP 10.10.20.100 for example
ping 10.10.20.112 # to check link between LWA and AGVS
```
 