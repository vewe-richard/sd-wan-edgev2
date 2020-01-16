# Baicells SD-WAN v0.2 User Guide  
  
## I. Installation  

### A. Requirements
The SD-WAN system is composed of two parts, Controller and Edges, which both should be installed in 
debian similar linux system, the Ubuntu18.04 is recommended.  

Controller present a web interface for administrator to manage the edge devices.  

Edge is the service installed in Baicells edge gateway.

### B. Controller
###### First time install
```
sudo apt install python3-pip
git clone https://github.com/vewe-richard/sd-wan-controller.git
```

###### Run it or Update it
```
cd sd-wan-controller
git pull

sudo su
pip3 install flask
python3 controllerv2/install.py
```
Note:  
Through `sudo su` to enter root shell, and run `pip3 install flask` under this shell.

###### Check Controller is running
*  Open `http://xx.xx.xx.xx:8080/index.htm` in web browser to be sure Controller is running.
*  If Controller is not running,   
   `systemctl status controllerv2` to check service status   
   `tail -n 100 /var/log/syslog` to check service log information

### C. Edge  
###### First time Install
```
git clone https://github.com/vewe-richard/sd-wan-edgev2.git
cd sd-wan-edgev2
sudo python3 install.py
edit /etc/sdwan/edge/config.json
sudo systemctl restart edgepoll
```
Note:  
The next section "II. Configuration" will give more details about how to configure edge device.

###### Run it or Update it
```
cd sd-wan-edgev2
git pull
sudo systemctl restart edgepoll
```

###### Check Edge is running
*  'systemctl status edgepoll' to check service status
*  'tail -n 100 /var/log/sdwan/edge/log' to check service log information

## II. Configuration
Location of configuration file in `/etc/sdwan/edge/config.json`
Note, please all letters should be lowercase.

```
{
  "sn": "00010001",     # device's serial number, it should be unique
  "type": "fatedge",    # type of edge, fatedge or thinedge
  "name": "sz-fatedge",
  "spec": "baicells-sd-wan-fatedge.hw.v01",  # hardware spec
  "sw": "fatedge.v01",  # software version
  "sms": "127.0.0.1",   # IP of Controller
  "smsport": 8080,      # Port of Controller
  "publicip": "",       # For fatedge device, if it has a public ip, present it here, it can fasten configuring
  "inputport": 11012,   # Keep it
  "timeout": 6,          # Edge poll actions from controller, it's the interval
  ""map": {"enp7s0f1": "200.100.100.200"}"  # mapping of public ip to nic interface, for fatedge device
}
```

After change configuration file,  `sudo systemctl restart edgepoll` to restart the edgepoll service,
and open `http://xx.xx.xx.xx:8080/procedureorchestration` to check if the edge device is registered.


### III. Network/Tunnels Orchestration
The link is `http://xx.xx.xx.xx:8080/orchestration`, after create the tunnel, refresh link 
`http://xx.xx.xx.xx:8080/actions` to check action results.















 