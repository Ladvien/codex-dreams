# Database Setup Scripts

These scripts initialize the database structure required for the Codex Dreams biological memory system.

## Setup Order

1. **`create_dreams_schema.sql`** - Main schema creation (REQUIRED)
   - Creates `dreams` schema with all biological memory tables
   - Sets up working memory, episodes, long-term storage, semantic networks
   - Configures proper permissions for `codex_user`

2. **`test_connection.sql`** - Basic connection setup (OPTIONAL)
   - Simple PostgreSQL connection configuration
   - Basic connectivity validation

3. **`test_postgres_connection.sql`** - Connection testing (UTILITY)
   - Validates database connectivity
   - Tests basic query functionality

## Usage

```bash
# Set up main schema (required before running dbt)
psql $POSTGRES_DB_URL -f create_dreams_schema.sql

# Test connectivity
psql $POSTGRES_DB_URL -f test_postgres_connection.sql
```

## Dependencies

- PostgreSQL database with `codex_user` created
- Environment variables: `POSTGRES_DB_URL` or individual components