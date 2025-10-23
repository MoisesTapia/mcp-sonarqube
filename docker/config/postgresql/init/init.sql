-- PostgreSQL initialization script for SonarQube MCP
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional databases if needed
-- CREATE DATABASE sonarqube_test;

-- Create additional users if needed
-- CREATE USER sonarqube_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE sonarqube TO sonarqube_readonly;
-- GRANT USAGE ON SCHEMA public TO sonarqube_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO sonarqube_readonly;

-- Set up any additional configuration
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Reload configuration
SELECT pg_reload_conf();