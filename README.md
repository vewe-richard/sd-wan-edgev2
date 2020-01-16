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