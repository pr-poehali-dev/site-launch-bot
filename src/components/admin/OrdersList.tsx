import { useState, useEffect } from "react";
import Icon from "@/components/ui/icon";
import { Order } from "./orderTypes";
import OrdersTable from "./OrdersTable";
import OrderDetailPanel from "./OrderDetailPanel";

interface Props {
  apiUrl: string;
  tgApiUrl: string;
  filterStatus: string;
}

export default function OrdersList({ apiUrl, tgApiUrl, filterStatus }: Props) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Order | null>(null);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<Order>>({});
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const showToast = (type: "success" | "error", text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl);
      const data = await res.json();
      setOrders(data.orders || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
    setSelected(null);
  }, [filterStatus]);

  const updateStatus = async (id: string, status: string) => {
    setOrders((prev) => prev.map((o) => o.id === id ? { ...o, status } : o));
    if (selected?.id === id) setSelected((s) => s ? { ...s, status } : null);
    await fetch(apiUrl, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status }),
    });
  };

  const sendToTelegram = async (order: Order) => {
    setSending(true);
    try {
      const res = await fetch(tgApiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "now",
          order: {
            from_city: order.from_city,
            to_city: order.to_city,
            pickup: order.pickup,
            dropoff: order.dropoff,
            trip_date: order.trip_date,
            trip_time: order.trip_time,
            price: order.price,
            tariff: order.tariff,
            commission: order.commission,
            phone: order.phone,
            passengers: order.passengers,
            luggage: order.luggage,
            booster: order.booster,
            child_seat: order.child_seat,
            animal: order.animal,
            comment: order.comment,
            id: order.id,
          },
        }),
      });
      const data = await res.json();
      if (data.ok) {
        showToast("success", "Заявка отправлена в группу!");
        await updateStatus(order.id, "on_sale");
      } else {
        showToast("error", `Ошибка: ${data.error || "не удалось отправить"}`);
      }
    } catch {
      showToast("error", "Ошибка отправки в Telegram");
    } finally {
      setSending(false);
    }
  };

  const markOnSale = async (order: Order) => {
    await sendToTelegram(order);
  };

  const startEdit = (order: Order) => {
    setEditForm({ ...order });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await fetch(apiUrl, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...editForm, id: selected.id }),
      });
      const updated = { ...selected, ...editForm } as Order;
      setOrders((prev) => prev.map((o) => o.id === selected.id ? updated : o));
      setSelected(updated);
      setEditing(false);
      showToast("success", "Заказ сохранён!");
    } catch {
      showToast("error", "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  const deleteOrder = async (id: string) => {
    setOrders((prev) => prev.filter((o) => o.id !== id));
    setSelected(null);
    await fetch(apiUrl, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
  };

  const filtered = filterStatus === "all"
    ? orders
    : orders.filter((o) => o.status === filterStatus);

  return (
    <div className="space-y-4">
      {toast && (
        <div className={`flex items-center gap-3 px-4 py-3 border rounded-lg animate-slide-up ${
          toast.type === "success" ? "bg-green-500/10 border-green-500/30" : "bg-red-500/10 border-red-500/30"
        }`}>
          <Icon name={toast.type === "success" ? "CheckCircle" : "AlertCircle"} size={16}
            className={toast.type === "success" ? "text-green-400" : "text-red-400"} />
          <span className={`text-sm font-medium ${toast.type === "success" ? "text-green-400" : "text-red-400"}`}>
            {toast.text}
          </span>
        </div>
      )}

      <OrdersTable
        orders={filtered}
        loading={loading}
        selectedId={selected?.id ?? null}
        onSelect={(order) => setSelected(order.id === selected?.id ? null : order)}
        onSell={markOnSale}
        onDelete={deleteOrder}
        onRefresh={fetchOrders}
      />

      {selected && (
        <OrderDetailPanel
          selected={selected}
          editing={editing}
          editForm={editForm}
          saving={saving}
          sending={sending}
          onClose={() => { setSelected(null); setEditing(false); }}
          onStartEdit={() => startEdit(selected)}
          onCancelEdit={() => setEditing(false)}
          onEditChange={(patch) => setEditForm((f) => ({ ...f, ...patch }))}
          onSave={saveEdit}
          onSendToTelegram={() => sendToTelegram(selected)}
          onSell={() => markOnSale(selected)}
          onUpdateStatus={(s) => updateStatus(selected.id, s)}
        />
      )}
    </div>
  );
}
