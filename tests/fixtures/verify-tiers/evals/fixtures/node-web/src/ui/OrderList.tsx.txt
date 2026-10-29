import * as React from "react";

export interface Order {
  id: string;
  reference: string;
  total: string;
  status: "open" | "paid" | "cancelled";
}

export function OrderList({
  orders,
  onDelete,
}: {
  orders: Order[];
  onDelete: (id: string) => void;
}) {
  if (orders.length === 0) {
    return <p className="empty">No orders yet.</p>;
  }

  return (
    <table>
      <caption>Orders</caption>
      <thead>
        <tr>
          <th scope="col">Reference</th>
          <th scope="col">Status</th>
          <th scope="col">Total</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        {orders.map((order) => (
          <tr key={order.id}>
            <td>{order.reference}</td>
            <td>
              <span className={`badge badge--${order.status}`}>{order.status}</span>
            </td>
            <td>{order.total}</td>
            <td>
              <button type="button" aria-label={`Delete order ${order.reference}`} onClick={() => onDelete(order.id)}>
                <TrashIcon aria-hidden="true" />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TrashIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" focusable="false" {...props}>
      <path d="M3 4h10l-1 9H4L3 4Zm3-2h4v2H6V2Z" fill="currentColor" />
    </svg>
  );
}
