-- uplinkId is a short-lived gateway correlation id with very few distinct
-- values, so (gateway_id, uplink_id) collides and silently drops uplinks.
-- Deduplicate on ChirpStack's per-uplink deduplicationId instead.
begin;

alter table uplinks add column deduplication_id uuid;
update uplinks set deduplication_id = (raw_event->>'deduplicationId')::uuid;
alter table uplinks alter column deduplication_id set not null;

alter table uplinks drop constraint uplinks_gateway_id_uplink_id_key;
alter table uplinks add constraint uplinks_deduplication_id_gateway_id_key
    unique (deduplication_id, gateway_id);

commit;
