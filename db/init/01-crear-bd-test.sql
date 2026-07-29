-- Corre automáticamente la PRIMERA vez que se inicializa el volumen de Postgres.
-- Crea la base de datos que usa la suite de pytest (separada de la de la app).
CREATE DATABASE monitor_test OWNER monitor;
ALTER ROLE monitor CREATEDB;
