-- Regime 1a monitoring: mote journals pulled from the Pis, exclusion windows
-- and hourly PDR counts, filled by the regime 1a job (LoRaWAN-Infra/regime1a/).
-- Run with psql as the chirpstack superuser (uses \connect).
-- grafana_reader reads these tables through the default privileges of
-- migration 003. The writer role is created without a password, so it cannot
-- log in until one is set with: ALTER ROLE regime1a_writer WITH PASSWORD '...';

\connect postgres

create role regime1a_writer login;
grant connect on database lorawan_experiments to regime1a_writer;

\connect lorawan_experiments

begin;

-- One row per emission logged by a mote (event=tx in its journal). The payload
-- (cycle, DR, 0x1A marker) is unique per mote and matches uplinks.payload_base64.
create table regime_1a_tx (
    id bigserial primary key,
    host text not null,
    dev_eui text not null,
    utc timestamptz not null,
    utc_tx_start timestamptz,
    cycle bigint not null,
    slot integer,
    dr integer not null,
    sf integer not null,
    upctr bigint,
    payload_hex text not null,
    attempts integer,
    immediate text,
    async_response text,
    airtime_ms real,
    loaded_at timestamptz not null default now(),
    unique (dev_eui, payload_hex)
);
create index regime_1a_tx_dev_eui_start_idx on regime_1a_tx (dev_eui, utc_tx_start);

-- Every other journal line (config, join, channels, skip, error, recover,
-- pwridx, adr, stop), kept for traceability and for the dashboard.
create table regime_1a_events (
    id bigserial primary key,
    host text not null,
    dev_eui text,
    utc timestamptz not null,
    event text not null,
    cycle bigint,
    dr integer,
    sf integer,
    immediate text,
    async_response text,
    detail text,
    loaded_at timestamptz not null default now(),
    unique (host, utc, event)
);
create index regime_1a_events_host_utc_idx on regime_1a_events (host, utc);

-- Exclusion windows of the rule in docs/plan-experimental.md (section 10):
-- E1 to E3 detected by the job, E4 from docs/exclusions-e4.csv.
create table regime_1a_exclusions (
    id bigserial primary key,
    rule text not null check (rule in ('E1', 'E2', 'E3', 'E4')),
    start_at timestamptz not null,
    end_at timestamptz not null check (end_at > start_at),
    detail text,
    computed_at timestamptz not null default now()
);
create index regime_1a_exclusions_start_idx on regime_1a_exclusions (start_at);

-- Hourly counts per mote and SF; PDR over any period = sum(received) / sum(sent).
-- sent/received exclude every rule; the *_without_e3 columns keep E3 hours.
create table regime_1a_hourly (
    hour timestamptz not null,
    dev_eui text not null,
    host text not null,
    sf integer not null,
    sent integer not null,
    received integer not null,
    excluded integer not null,
    sent_without_e3 integer not null,
    received_without_e3 integer not null,
    computed_at timestamptz not null default now(),
    primary key (hour, dev_eui, sf)
);

-- One row per Pi and per pull (copy of /srv/regime1a/etat-collecte.csv).
create table regime_1a_collection (
    utc timestamptz not null,
    host text not null,
    ip text,
    status text not null,
    rsync_code integer,
    bytes bigint,
    primary key (utc, host)
);

grant select, insert, update, delete on
    regime_1a_tx, regime_1a_events, regime_1a_exclusions, regime_1a_hourly, regime_1a_collection
    to regime1a_writer;
grant usage on sequence
    regime_1a_tx_id_seq, regime_1a_events_id_seq, regime_1a_exclusions_id_seq
    to regime1a_writer;
-- The job reads the existing tables to match receptions and detect windows.
grant select on uplinks, gateway_events to regime1a_writer;

commit;
