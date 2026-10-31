-- Public local-demo password only. No V-Market role/database is accessed.
CREATE ROLE ai_app LOGIN PASSWORD 'local-ai-app-only';
CREATE SCHEMA ai AUTHORIZATION ai_owner;
GRANT USAGE ON SCHEMA ai TO ai_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
