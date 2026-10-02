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
EOSQL
