-- PostgreSQL initialization script for SonarQube
-- Create database and user for SonarQube

-- Create the sonarqube user
CREATE USER sonarqube WITH PASSWORD 'sonarqube_password';

-- Create the sonarqube database
CREATE DATABASE sonarqube WITH 
    OWNER = sonarqube
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Grant all privileges on the database to the user
GRANT ALL PRIVILEGES ON DATABASE sonarqube TO sonarqube;

-- Connect to the sonarqube database and set up schema
\c sonarqube;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO sonarqube;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sonarqube;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sonarqube;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sonarqube;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO sonarqube;