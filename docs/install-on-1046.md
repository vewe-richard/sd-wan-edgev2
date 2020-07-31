# Guide on install edgepoll on LS1046 board

### Step 1: Run sd-wan-env/1046/setup.py
```
apt-get update
apt install ntpdate  #"dpkg --configure -a" if any error
ntpdate -s cn.pool.ntp.org

git clone https://github.com/vewe-richard/sd-wan-env.git
cd sd-wan-env
python3 1046/setup.py
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


