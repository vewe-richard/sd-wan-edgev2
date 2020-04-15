# User
For example, the thinedge which run vpn node is 172.16.2.119
. set the thinedge as default gateway
. set dns server as the thinedge

For example, in ubuntu
1. install dnsmasq
https://computingforgeeks.com/install-and-configure-dnsmasq-on-ubuntu-18-04-lts/
for example
/etc/dnsmasq.conf
server=/google.com/100.100.2.136
server=/wikipedia.org/100.100.2.136
server=114.114.114.114

/etc/NetworkManager/NetworkManager.conf
[main]
dns=none
to disable modify of /etc/resolv.conf

change /etc/resolv.conf as 127.0.0.1

case 1: netplan
  after modify run netplay apply
case 2: NetworkManager
  change /etc/network/interface
  systemctl restart NetworkManager

check dns use systemd-resolve --status
if dns doesn't work, you can change /etc/resolv.conf 127.0.0.53 to thinedge directly
