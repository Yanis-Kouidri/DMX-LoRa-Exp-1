# MikroTik gateway: current state

State as of **2026-10-12**, verified end to end: the mote joined over OTAA through
the gateway and its uplinks reach ChirpStack and the Grafana dashboard.

- Model: MikroTik wAP LoRa8 (`RBwAPR-2nD`, board `wAP R`), RouterOS 7.24
- Gateway ID: `323531322A003300`
- Role: **fixed gateway** of the experiment. It stays indoors, in the IRIT office
  (4th floor, next to a north-west facing window), for the whole experiment (no rooftop install). Keep its position and antenna
  orientation unchanged.
- A second, identical wAP LoRa8 is the **mobile gateway** (bike, 4G). It is not
  documented here yet.

## Network topology

```
Campus wall jack ──(DHCP)── ether1 [WAN]   wAP LoRa8   wlan1 [LAN] ── PC (admin)
                                                        Wi-Fi AP "wAP-LoRa-admin"
                                                        192.168.88.1/24
```

| Interface | Role | Addressing |
|---|---|---|
| `ether1` | WAN, Internet access through the campus wall jack | DHCP client (`defconf`), got `192.168.1.143/24`, gateway `192.168.1.1` |
| `wlan1` | LAN, private admin access point `wAP-LoRa-admin` (WPA2-PSK, profile `wap-admin`) | `192.168.88.1/24`, DHCP server `defconf` (pool `192.168.88.10-254`) |

- NAT masquerade on the `WAN` interface list: a PC connected to `wAP-LoRa-admin`
  gets Internet through the gateway.
- Default RouterOS firewall: input is dropped from `WAN`, so the gateway is
  administrable **only from the `wAP-LoRa-admin` Wi-Fi**.
- The `wAP-LoRa-admin` password is not stored here: keep it in `secrets.md`.

Disabled leftovers from the earlier direct PC-to-gateway Ethernet setup (kept to
make a rollback easy):

- static address `192.168.1.60/24` on `ether1`
- static default route via `192.168.1.99` (distance 10)
- DHCP client `client1` on `wlan1`

## LoRa configuration

| Setting | Value |
|---|---|
| Server | `ChirpStack LNS`: `chirpstack.kouidri.fr`, port `3001`, Basics Station (LNS) over TLS |
| Client certificate | `wap-gateway` (signed by `chirpstack-ca`, "LoRaWAN-Infra gateway CA") |
| Channel plan | `eu-868`, public network |
| Antenna | internal, 0 dBi gain |

⚠️ The `wap-gateway` client certificate **expires on 2027-10-07**. Generate a new
one in ChirpStack (Gateway → TLS certificate) before that date.

The other entries in `/lora servers` (TTN, TTS) are RouterOS defaults and are not used.

## Administration access

1. Connect the PC to the `wAP-LoRa-admin` Wi-Fi.
2. WebFig: `http://192.168.88.1`, with the `admin` account.

### Claude Code access

Claude administers the gateway over SSH with a dedicated account. The user asked
to keep this access.

```bash
ssh -i ~/.ssh/claude_wap claude@192.168.88.1
```

- RouterOS user `claude` (group `full`), key-only login (ed25519 key `claude-wap`)
- Private key on the PC: `~/.ssh/claude_wap` (WSL 2 in mirrored networking mode,
  so the Windows Wi-Fi connection is visible from WSL)
- To revoke it: `/user remove claude` on the gateway, then
  `rm ~/.ssh/claude_wap ~/.ssh/claude_wap.pub` on the PC

## Campus Wi-Fi: does not work (open issue)

Connecting the gateway as a Wi-Fi client to the campus networks was tried and failed:

- **eduroam** (INP account, PEAP/MSCHAPv2) and **Poseidon** (IRIT network):
  802.1X authentication succeeds, but DHCP DISCOVERs never get an answer. The PC
  gets a lease on the same access point, band and account, and the gateway gets a
  lease immediately on a phone hotspot and on the wall jack. The most likely cause
  is device filtering by the campus Wi-Fi infrastructure; only the IT department
  (dsi-support.inp-toulouse.fr) can confirm or lift it.
- Do **not** work around it by spoofing or cloning MAC addresses: it bypasses the
  university's access control, and cloning the PC's MAC conflicts with the PC.
- The campus 2.4 GHz access points (`20:9E:F7:*`) use a **TKIP group cipher**: any
  RouterOS security profile for them needs `group-ciphers=tkip,aes-ccm`, otherwise
  the gateway skips them and falls back to distant access points.
- The INP eduroam CA (`rootCA.eduroam.inpt`, profile from cat.eduroam.org) is still
  imported on the gateway. The eduroam, Poseidon and hotspot security profiles were
  removed, so no personal credentials are stored on the gateway.

## Pitfalls

- **Factory default DHCP server bound to `wlan1`**: if `wlan1` is ever switched back
  to station (client) mode, disable the `defconf` DHCP server and the
  `192.168.88.1/24` address on it, and move `wlan1` to the `WAN` interface list.
  Otherwise the gateway acts as a rogue DHCP server on the upstream network and
  exposes its admin interface to it.
- **No battery-backed clock**: the time is wrong after a reboot until NTP syncs
  (NTP client enabled with `pool.ntp.org`). TLS to ChirpStack and uplink timestamps
  depend on it.

## Useful commands

```
/ip dhcp-client print detail where interface=ether1   # WAN lease
/ping 8.8.8.8 count=3                                 # Internet access
/lora print                                           # LoRa status and packet counters
/lora traffic print                                   # last frames (join, uplinks, downlinks)
/log print where topics~"lora"                        # ChirpStack connection log
/interface wireless registration-table print          # clients on wAP-LoRa-admin
```
