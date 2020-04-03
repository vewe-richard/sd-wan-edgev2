# User
For example, the thinedge which run vpn node is 172.16.2.119
. set the thinedge as default gateway
. set dns server as the thinedge

For example, in ubuntu
case 1: netplan
  after modify run netplay apply
case 2: NetworkManager
  change /etc/network/interface
  systemctl restart NetworkManager

check dns use systemd-resolve --status
if dns doesn't work, you can change /etc/resolv.conf 127.0.0.53 to thinedge directly
