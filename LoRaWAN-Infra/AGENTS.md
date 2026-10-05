# AGENTS.md

## Structure

The root files define and document the deployment: `docker-compose.yml` orchestrates the services, `Makefile` provides helper commands, `Caddyfile` configures the reverse proxy, and `.env.example` documents the required environment variables.
The `configuration/` directory contains ChirpStack, Gateway Bridge, Mosquitto, and PostgreSQL configuration files for the supported regions and integrations.
The `uplink-collector/` directory contains the MQTT-to-PostgreSQL collector application (uplinks, device events and gateway traffic), its Dockerfile, and Python dependencies.
The `configuration/postgresql/migrations/` directory contains SQL migrations to apply manually to existing databases; `initdb/` holds the full schema for fresh installs.

## Stack

This directory contains a Docker Compose stack for LoRaWAN experiments:

- **ChirpStack**: LoRaWAN network server.
- **Gateway Bridge**: Semtech UDP and Basic Station gateway integrations.
- **REST API**: ChirpStack REST interface.
- **PostgreSQL**: application database.
- **Redis**: ChirpStack cache and session backend.
- **Mosquitto**: MQTT broker.
- **Uplink Collector**: MQTT-to-PostgreSQL collector for uplinks, all device events and gateway traffic.
- **Grafana**: metrics and dashboard visualization.
- **Caddy**: HTTP/HTTPS reverse proxy.