import { requireAdmin, requireUser, Session } from "../auth/session";
import {
  Db,
  Row,
  findCustomersByIds,
  findOrderById,
  findOrdersByCustomer,
  softDeleteOrder,
} from "../db/queries";

const PAGE_SIZE = 20;

export interface ListParams {
  page: number;
  customerId: string;
}

export function paginate<T>(items: T[], page: number): T[] {
  const start = page * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

/** Orders for one customer, with each order's customer record attached. */
export async function listOrders(
  db: Db,
  session: Session,
  params: ListParams,
  now: number
): Promise<Row[]> {
  requireUser(session, now);
  const orders = await findOrdersByCustomer(db, params.customerId);
  const page = paginate(orders, params.page);

  const ids = [...new Set(page.map((o) => String(o.customer_id)))];
  const customers = await findCustomersByIds(db, ids);
  const byId = new Map(customers.map((c) => [String(c.id), c]));

  return page.map((order) => ({ ...order, customer: byId.get(String(order.customer_id)) }));
}

export async function getOrder(
  db: Db,
  session: Session,
  id: string,
  now: number
): Promise<Row | null> {
  const user = requireUser(session, now);
  const order = await findOrderById(db, id);
  if (!order) return null;
  if (order.customer_id !== user.id && user.role !== "admin") {
    throw new Error("forbidden");
  }
  return order;
}

export async function deleteOrder(
  db: Db,
  session: Session,
  id: string,
  now: number
): Promise<void> {
  requireAdmin(session, now);
  await softDeleteOrder(db, id);
}
