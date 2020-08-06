# Guide on install edgepoll on LS1046 board

### Step 1: Run sd-wan-env/1046/setup.py
```
replace us.ports to cn.ports in /etc/apt/source.list
apt-get update
apt install ntpdate  #"dpkg --configure -a" if any error
ntpdate -s cn.pool.ntp.org

git clone https://github.com/vewe-richard/sd-wan-env.git
cd sd-wan-env/1046
python3 1046/setup.py

replace with latest kernel Image, and kernel modules
location: //server://home/richard/PycharmProjects/backup/

# to be check, if the original openvswitch can not work, then do next 
#python3 openvswitch-remove.py
#apt install openvswitch-switch

docker image
first time:
git clone https://gitee.com/vewe-richard/edgegate.git
root@localhost:~/edgegate/dockers/base# docker pull ubuntu
root@localhost:~/edgegate/dockers/base# docker build -t jiangjqian/edgegate:base ./
root@localhost:~/edgegate/dockers/gateway# docker build -t jiangjqian/edgegate:gatewaybase ./

else:
use docker.tar in //server://home/richard/PycharmProjects/backup/

```

Check:
  * WAN port
```
root@localhost:~/sd-wan-env# ls /etc/systemd/network/
eth0.network  fm1-mac9.network  fm1-usb0.network
```
  * clone edgepoll, and setup pyserial, pytuntap
```
cat /etc/sdwan/edge/config.json
cat /root/.sdwan/edgepoll/network.json
cat /root/.sdwan/edgepoll/5g.json
```

### Step 2: run edgepoll
```
try:
export PYTHONPATH=$PWD && python3 edgepoll/__main__.py --loglevel=10
or run:
python3 install.py
```

### Step 3: test
dhcp work, gateway work, dns work, 5G work, web status work, 
remote control work


