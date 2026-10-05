#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$POSTGRES_DB" <<-EOSQL
    create database lorawan_experiments;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=lorawan_experiments <<-EOSQL
    create table uplinks (
        id bigserial primary key,
        received_at timestamptz not null,
        collected_at timestamptz not null default now(),
        deduplication_id uuid not null,
        dev_eui text not null,
        gateway_id text,
        uplink_id bigint,
        f_cnt bigint,
        f_port integer,
        confirmed boolean,
        data_rate integer,
        frequency_hz bigint,
        bandwidth_hz integer,
        spreading_factor integer,
        coding_rate text,
        channel integer,
        rssi_dbm real,
        snr_db real,
        gw_time timestamptz,
        ns_time timestamptz,
        payload_base64 text,
        raw_event jsonb not null,
        unique (deduplication_id, gateway_id)
    );
    create index uplinks_dev_eui_received_at_idx on uplinks (dev_eui, received_at);
    create index uplinks_gateway_received_at_idx on uplinks (gateway_id, received_at);
    create index uplinks_received_at_idx on uplinks (received_at);

    create table device_events (
        id bigserial primary key,
        event_type text not null,
        time timestamptz,
        collected_at timestamptz not null default now(),
        deduplication_id uuid,
        application_id text,
        dev_eui text,
        device_name text,
        f_cnt bigint,
        log_level text,
        log_code text,
        log_description text,
        raw_event jsonb not null,
        message_sha256 text not null unique
    );
    create index device_events_dev_eui_time_idx on device_events (dev_eui, time);
    create index device_events_type_time_idx on device_events (event_type, time);

    create table gateway_events (
        id bigserial primary key,
        region text not null,
        gateway_id text not null,
        direction text not null,
        event_type text not null,
        time timestamptz,
        collected_at timestamptz not null default now(),
        frequency_hz bigint,
        bandwidth_hz integer,
        spreading_factor integer,
        rssi_dbm real,
        snr_db real,
        crc_status text,
        m_type text,
        dev_addr text,
        dev_eui text,
        f_cnt bigint,
        phy_payload_base64 text,
        raw_event jsonb not null
    );
    create index gateway_events_gateway_time_idx on gateway_events (gateway_id, time);
    create index gateway_events_type_time_idx on gateway_events (event_type, time);
    create index gateway_events_dev_addr_time_idx on gateway_events (dev_addr, time);
EOSQL
