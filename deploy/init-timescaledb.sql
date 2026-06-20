-- Enable the TimescaleDB extension on the application database.
-- Runs once, when the Postgres data directory is first initialised.
CREATE EXTENSION IF NOT EXISTS timescaledb;
