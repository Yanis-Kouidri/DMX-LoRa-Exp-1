-- Identify regime_1a_events rows by their line in the mote journal: two lines
-- can share host, utc and event (pi-mote-5 logged two 'error' lines in the same
-- millisecond on 2026-11-07), so the unique key of migration 004 lost lines.
-- Applied while the table was still empty.

begin;

alter table regime_1a_events drop constraint regime_1a_events_host_utc_event_key;
alter table regime_1a_events add column line_no integer not null;
alter table regime_1a_events add constraint regime_1a_events_host_line_no_key unique (host, line_no);

commit;
