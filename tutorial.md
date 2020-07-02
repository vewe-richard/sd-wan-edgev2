# Use edgepoll directly to create a tunnel

#### prepare sourcecode
git clone https://github.com/vewe-richard/sd-wan-edgev2.git
export EDGEPOLL_PATH=$PWD/sd-wan-edgev2

#### prepare tunnel config files
cd $EDGEPOLL_PATH
cp configs/stun-server.json /root/.sdwan/edgepoll/ns/stun.json 
cp configs/stun-client.json /root/.sdwan/edgepoll/stun.json

#### prepare environment
ip link add veth0 type veth peer name veth1
ip netns add ns
ip link set veth0 netns ns

ip netns exec ns ip address add 10.129.31.101/24 dev veth0
ip netns exec ns ip link set veth0 up

ip address add 10.129.31.100/24 dev veth1
ip link set veth1 up
ping 10.129.31.101 -c 1 || echo fail

ip netns exec ns bash
test $(ip netns identify) = "ns" || echo fail
ip route add default via 10.129.31.1
cd $(EDGEPOLL_PATH)
export PYTHONPATH=$PWD && python3 edgepoll/__main__.py --loglevel=10  --config=./config.json

#### create a new shell
test -z $(ip netns identify) || echo fail
cd $(EDGEPOLL_PATH)
export PYTHONPATH=$PWD && python3 edgepoll/__main__.py --loglevel=10 --config=./config.json
ping 10.139.47.1 -c 1 || echo fail


