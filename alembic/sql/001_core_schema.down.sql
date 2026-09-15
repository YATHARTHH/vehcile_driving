-- Migration: 001_core_schema.down.sql
-- Description: Reversible downgrade dropping core tables in reverse dependency order

DROP TABLE IF EXISTS saved_routes CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS fleets CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
