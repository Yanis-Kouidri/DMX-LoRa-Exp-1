# DMX-LoRa-Exp-1

## Experimental Setup & Objectives

This repository presents a comparative performance analysis of wireless sensor data harvesting in a LoRaWAN architecture, evaluating the performance of a mobile gateway versus a fixed (static) gateway. The primary objective of this experiment is to measure and compare key network performance metrics and RF signal characteristics across both deployment scenarios, including:

- Packet Delivery Ratio (PDR)
- Received Signal Strength Indicator (RSSI)
- Signal-to-Noise Ratio (SNR)
- Dynamic Adaptation of Spreading Factor (SF) and Coding Rate (CR)

## Hardware

### Mote (sensor)

This project targets the **Microchip RN2483 LoRa Technology Mote**, an evaluation board for experimenting with **LoRa** and **LoRaWAN** networks.

**LoRa modem:** Microchip RN2483A (868 MHz, EU868)

**Firmware:** RN2483 **1.0.6 RC4** (EU868, LoRaWAN 1.0.2), the latest firmware Microchip publishes for the RN2483.

- Source: [MicrochipTech/RN2xx3_LORAWAN_FIRMWARE](https://github.com/MicrochipTech/RN2xx3_LORAWAN_FIRMWARE), file `software/firmware/RN2483EU_1.0.6_RC4/Binary/offset/RN2483_Parser.production.hex` (git blob `46f6913c06273d5d8a7fcdd86519c1cc72402def`). A local copy is kept in `Mote/firmware/` (git-ignored).
- `sys get ver` reports `RN2483 1.0.6 RC3 May 18 2021 18:35:00`. This is expected: Microchip did not update the version string in the RC4 build, so the official RC4 binary still contains "1.0.6 RC3".
- New motes ship with an older firmware (1.0.1 seen out of the box) and must be flashed before use:

```bash
cd Mote && uv run python src/flash_firmware.py firmware/RN2483EU_1.0.6_RC4/RN2483_Parser.production.hex
```

### Gateway

- Model: MikroTik wAP LoRa8
- Version: MikroTik RouterOS 7.24

Network setup, administration access and known issues: see [gateway.md](gateway.md).

## WSL 2 Mote connection

To work on WSL and connect to the mote you need to run on Windows PowerShell:

```bash
usbipd list
```

and, with the correct busid

```bash
usbipd attach --wsl --busid 6-2
```

Or better

```bash
usbipd attach --hardware-id 04d8:000a --wsl
```
