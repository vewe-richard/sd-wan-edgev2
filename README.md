# sd-wan-edgev2
edge for sd-wan

#First time Install
```
git clone https://github.com/vewe-richard/sd-wan-edgev2.git
cd sd-wan-edgev2
sudo python3 install.py
edit /etc/sdwan/edge/config.json
sudo systemctl restart edgepoll
```

# Run it or Update it
```
cd sd-wan-edgev2
git pull
sudo systemctl restart edgepoll
```

# LED  status
Value 3 / 011:          begin of edgepoll
flicking several times: edgepoll initialize complete, enter loop of edgepoll
led bottom:             lan ready
led middle:             wan ready
led up:                 5G connected


