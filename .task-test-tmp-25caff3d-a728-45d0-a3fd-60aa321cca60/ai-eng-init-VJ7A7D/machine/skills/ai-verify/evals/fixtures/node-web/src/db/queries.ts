export interface Row {
  [column: string]: unknown;
}

export interface Db {
  query(sql: string, params?: unknown[]): Promise<Row[]>;
}

export async function findOrderById(db: Db, id: string): Promise<Row | null> {
  const rows = await db.query("select * from orders where id = $1", [id]);
  return rows[0] ?? null;
}

export async function findOrdersByCustomer(db: Db, customerId: string): Promise<Row[]> {
  return db.query("select * from orders where customer_id = $1 order by created_at desc", [
    customerId,
  ]);
}

export async function searchOrders(db: Db, term: string): Promise<Row[]> {
  return db.query("select * from orders where reference ilike $1 limit 50", [`%${term}%`]);
}

export async function findCustomer(db: Db, id: string): Promise<Row | null> {
  const rows = await db.query("select id, name, email from customers where id = $1", [id]);
  return rows[0] ?? null;
}

export async function findCustomersByIds(db: Db, ids: string[]): Promise<Row[]> {
  if (ids.length === 0) return [];
  return db.query("select id, name, email from customers where id = any($1)", [ids]);
}

export async function softDeleteOrder(db: Db, id: string): Promise<void> {
  await db.query("update orders set deleted_at = now() where id = $1", [id]);
}
