-- PPK2 energy bench: per-message results of the series versioned in
-- Mote/banc-ppk2/ (CSV and JSON written by Mote/src/banc_ppk2.py), loaded by
-- LoRaWAN-Infra/banc-ppk2/chargement.py for the Grafana dashboard.
-- The versioned files remain the reference: these tables are a copy, replaced
-- as a whole at each load. Raw samples (100 kS/s) are not loaded.
-- Run with psql as the chirpstack superuser (uses \connect).
-- grafana_reader reads the tables and the view through the default privileges
-- of migration 003. The writer role is created without a password, so it
-- cannot log in until one is set with:
-- ALTER ROLE banc_ppk2_writer WITH PASSWORD '...';

\connect postgres

create role banc_ppk2_writer login;
grant connect on database lorawan_experiments to banc_ppk2_writer;

\connect lorawan_experiments

begin;

-- One row per series (one CSV and one JSON in Mote/banc-ppk2/).
create table ppk2_series (
    name text primary key,
    started_at timestamptz not null,
    hweui text,
    firmware text,
    mode text not null check (mode in ('uncnf', 'cnf')),
    payload_bytes integer not null,
    reps integer not null,
    rx1_delay_ms integer not null,
    rx2_sf integer not null,
    sleep_ms integer,
    source_mv integer not null,
    no_duty_cycle boolean not null,
    warmup integer not null,
    label text not null,
    -- false for method checks (validation, no-duty-cycle control): kept out
    -- of the result panels, see Mote/banc-ppk2/README.md.
    in_results boolean not null,
    -- Commit at launch; null for the series older than this field, whose
    -- provenance is documented in Mote/banc-ppk2/README.md.
    acquisition_git text,
    loaded_at timestamptz not null default now()
);

-- One row per attempt (one CSV line). Columns as in the CSV, see
-- Mote/banc-ppk2/README.md; rx1_ms and rx2_ms split rx_windows_ms when the
-- analysis found exactly two reception windows.
create table ppk2_messages (
    series text not null references ppk2_series (name) on delete cascade,
    attempt integer not null,
    rep integer not null,
    sf integer not null,
    mode text not null,
    payload_bytes integer not null,
    upctr bigint,
    immediate text,
    final text,
    reset_seen boolean,
    warmup boolean not null,
    i_sleep_ma real,
    i_idle_ma real,
    tx_start_ms real,
    duration_ms real,
    charge_mc real,
    tx_ms real,
    energy_mj real,
    rx_windows_ms text,
    rx1_ms real,
    rx2_ms real,
    gap_samples_error integer,
    marker_samples_error integer,
    valid boolean not null,
    primary key (series, attempt)
);

-- Messages kept in the statistics of the result series, with the settings of
-- their series: the only source of the result panels.
create view ppk2_results as
select m.series, m.attempt, m.rep, m.sf, m.mode, m.payload_bytes,
       s.rx2_sf, s.rx1_delay_ms, s.source_mv,
       m.energy_mj, m.duration_ms, m.tx_ms, m.rx1_ms, m.rx2_ms,
       m.i_sleep_ma, m.i_idle_ma
from ppk2_messages m
join ppk2_series s on s.name = m.series
where m.valid and s.in_results;

grant select, insert, update, delete on ppk2_series, ppk2_messages to banc_ppk2_writer;

commit;
