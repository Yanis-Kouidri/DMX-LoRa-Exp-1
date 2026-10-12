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
