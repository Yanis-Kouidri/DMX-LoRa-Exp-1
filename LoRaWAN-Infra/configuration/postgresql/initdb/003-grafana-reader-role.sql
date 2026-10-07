-- Read-only role for Grafana, limited to the lorawan_experiments database.
-- Run with psql as the chirpstack superuser (uses \connect).
-- The role is created without a password, so it cannot log in until one is
-- set with: ALTER ROLE grafana_reader WITH PASSWORD '...';

\connect postgres

create role grafana_reader login;
alter role grafana_reader set default_transaction_read_only = on;

-- Only the owner and explicitly granted roles may connect to each database.
revoke connect on database postgres, chirpstack, lorawan_experiments from public;
grant connect on database lorawan_experiments to grafana_reader;

\connect chirpstack

-- PostgreSQL < 15 lets every role create objects in the public schema.
revoke create on schema public from public;

\connect lorawan_experiments

revoke create on schema public from public;
grant usage on schema public to grafana_reader;
grant select on all tables in schema public to grafana_reader;
-- Tables created later by the chirpstack role (future migrations) too.
alter default privileges for role chirpstack in schema public
    grant select on tables to grafana_reader;
