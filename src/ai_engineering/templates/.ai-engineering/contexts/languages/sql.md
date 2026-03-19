## SQL Injection Prevention

**Critical security:**

- Always use parameterized queries
- Never concatenate user input into SQL
- Use ORM query builders when possible
- Validate/sanitize all inputs before queries

**Example (unsafe vs safe):**

```sql
-- UNSAFE: SQL injection vulnerability
SELECT * FROM users WHERE id = ${userId};

-- SAFE: Parameterized query
SELECT * FROM users WHERE id = $1;
```text

## N+1 Query Problems

**Performance issues:**

- Loading records in a loop (use joins)
- Multiple queries where one would work
- Missing `SELECT` with joins for related data

**Fix with joins:**

```sql
-- Bad: Triggers N+1 queries in application code
SELECT * FROM orders;
-- Then for each order: SELECT * FROM customers WHERE id = ?

-- Good: Single query with join
SELECT o.*, c.* FROM orders o
JOIN customers c ON o.customer_id = c.id;
```text

## Indexing

**Missing indexes cause:**

- Slow `WHERE` clause queries
- Slow `JOIN` operations
- Slow `ORDER BY` operations

**Index best practices:**

- Index foreign keys
- Index frequently queried columns
- Compound indexes for multi-column queries
- Don't over-index (slows writes)

## Query Optimization

**Common inefficiencies:**

- `SELECT *` instead of specific columns
- Missing `LIMIT` on large result sets
- Subqueries instead of joins
- Functions in WHERE clause (breaks index usage)
- Comparing with `LIKE '%term%'` (can't use index)

**Better patterns:**

```sql
-- Bad: Full table scan
SELECT * FROM users WHERE YEAR(created_at) = 2024;

-- Good: Uses index
SELECT id, name FROM users
WHERE created_at >= '2024-01-01'
  AND created_at < '2025-01-01'
LIMIT 100;
```text

## Transaction Management

**ACID principles:**

- Use transactions for multi-step operations
- Handle rollback on errors
- Be aware of isolation levels
- Avoid long-running transactions

**Deadlock prevention:**

- Access tables in consistent order
- Keep transactions short
- Use appropriate isolation levels
- Handle deadlock retry logic

## Data Integrity

**Constraints:**

- Use `NOT NULL` for required fields
- Add `UNIQUE` constraints where appropriate
- Use `CHECK` constraints for validation
- Foreign keys with `ON DELETE`/`ON UPDATE` actions

**Common mistakes:**

- Missing foreign key constraints
- Nullable columns that shouldn't be
- No default values where appropriate

## Schema Design

**Normalization:**

- Avoid duplicate data
- Use junction tables for many-to-many
- Don't store calculated values (use views)

**When to denormalize:**

- For performance on read-heavy tables
- For aggregated data that's expensive to calculate
- Document why denormalization was needed

## PostgreSQL Specific

**Common patterns:**

- Use `RETURNING` clause for insert/update results
- JSON columns (`jsonb`) for flexible data
- Array columns for lists
- Use `EXPLAIN ANALYZE` to check query plans

**Avoid:**

- Using `text` when `varchar(n)` is appropriate
- Missing indexes on `jsonb` fields you query
- Not using partial indexes when appropriate

## Anti-Patterns

**Performance killers:**

- Queries without WHERE clauses on large tables
- `COUNT(*)` on entire tables (use estimates)
- Cursor iteration instead of set-based operations
- `DISTINCT` as a fix for duplicate results (fix join instead)

**Maintainability:**

- Complex nested subqueries (use CTEs)
- Business logic in database (use application code)
- Stored procedures for simple operations
