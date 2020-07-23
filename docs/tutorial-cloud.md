# An example to use edgepoll to act as a local cloud agent

### This example will bring up a local cloud as below
```
VM1     VM2
 |_______|
     |
  vSwitch
     |
  vGateway
     |
    VM3
```
In this example, 
  * VM1: name is AGVS, system is Ubuntu 20.04
  * VM2: name is ERP, system is Ubuntu 20.04
  * VM3: name is LWA, system is Ubuntu 20.04
  * vSwitch: a virtual switch, name is vSW
  * vGateway: a virtual gateway, ip is 10.10.20.1/24

### Install steps
#### System environment
System: Ubuntu is prefered

  1. install edgepoll, follow docs/sd-wan-v0.2-install.md
  2. install docker
  3. pull dockers, jiangjqian/edgegate:gatewaybase and jiangjqian/edgegate:ubuntu-net
  4.
 
#### Prepare configure file
Refer to configs/cloud.json

Just copy configs/cloud.json to /root/.sdwan/edgepoll/cloud.json

#### Run edgepoll under root
```
sudo su
export PYTHONPATH=$PWD && python3 edgepoll/__main__.py --loglevel=10
```

#### Check link between AGVS and LWA
```
docker exec -it AGVS /bin/bash
dhclient evGW104-293  #get ip address 10.10.20.141/24 for example

docker exec -it LWA /bin/bash
dhclient evSW-668
ping 10.10.20.141

```

