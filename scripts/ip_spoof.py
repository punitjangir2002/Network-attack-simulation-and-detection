"""
ip_spoof.py
-----------
Crafts and sends ICMP echo-request packets with a forged source IP
address using Scapy, for the IP Spoofing demonstration (Section 4.3
of the report).

WARNING: Run this only inside an isolated, host-only lab network that
you own. Spoofing the source address of packets sent to a host you do
not control, or on a network you do not own, is illegal in most
jurisdictions.

Usage:
    sudo python3 ip_spoof.py
"""

from scapy.all import IP, ICMP, send

# Spoof the source IP: claims to be 192.168.30.130 (monitor VM),
# sent to the victim 192.168.30.129
packet = IP(src="192.168.30.130", dst="192.168.30.129") / ICMP()
send(packet, count=5, verbose=True)
