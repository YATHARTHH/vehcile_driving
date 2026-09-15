-- Migration: 001_core_schema.up.sql
-- Description: Core multi-tenant and relational domain tables

CREATE TABLE tenants (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    tier VARCHAR(20) DEFAULT 'standard',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fleets (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehicles (
    id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    fleet_id VARCHAR(50) REFERENCES fleets(id) ON DELETE SET NULL,
    vin VARCHAR(17) UNIQUE,
    vehicle_class VARCHAR(50) DEFAULT 'passenger_car',
    powertrain VARCHAR(50) DEFAULT 'ice_petrol',
    profile_config JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    vehicle_number VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trips (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trip_date VARCHAR(50),
    distance_km DOUBLE PRECISION,
    avg_speed_kmph DOUBLE PRECISION,
    max_speed DOUBLE PRECISION,
    max_rpm INTEGER,
    fuel_consumed DOUBLE PRECISION,
    brake_events INTEGER,
    steering_angle DOUBLE PRECISION,
    angular_velocity DOUBLE PRECISION,
    gps_path JSONB,
    distance DOUBLE PRECISION,
    avg_speed DOUBLE PRECISION,
    score VARCHAR(20),
    acceleration DOUBLE PRECISION,
    gear_position INTEGER,
    tire_pressure DOUBLE PRECISION,
    engine_load DOUBLE PRECISION,
    throttle_position DOUBLE PRECISION,
    brake_pressure DOUBLE PRECISION,
    trip_duration DOUBLE PRECISION,
    start_location VARCHAR(255),
    end_location VARCHAR(255)
);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    trip_id INTEGER REFERENCES trips(id) ON DELETE SET NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(100) NOT NULL,
    message VARCHAR(255) NOT NULL,
    icon VARCHAR(50),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
);

CREATE TABLE saved_routes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    route_name VARCHAR(100) NOT NULL,
    start_location VARCHAR(255) NOT NULL,
    end_location VARCHAR(255) NOT NULL,
    route_type VARCHAR(50),
    distance_km DOUBLE PRECISION,
    travel_time_minutes INTEGER,
    fuel_consumption DOUBLE PRECISION,
    fuel_cost DOUBLE PRECISION,
    efficiency_score INTEGER,
    saved_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Foreign key and lookup indexes
CREATE INDEX ix_fleets_tenant_id ON fleets(tenant_id);
CREATE INDEX ix_vehicles_tenant_id ON vehicles(tenant_id);
CREATE INDEX ix_vehicles_fleet_id ON vehicles(fleet_id);
CREATE INDEX ix_trips_user_id ON trips(user_id);
CREATE INDEX ix_alerts_user_id ON alerts(user_id);
CREATE INDEX ix_alerts_trip_id ON alerts(trip_id);
CREATE INDEX ix_saved_routes_user_id ON saved_routes(user_id);
