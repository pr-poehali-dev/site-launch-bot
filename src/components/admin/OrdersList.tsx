import { useState, useEffect } from "react";
import Icon from "@/components/ui/icon";

const TG_API = "https://functions.poehali.dev/ed779d34-4d03-4202-baa8-7d25732d1aaa";

interface Order {
  id: string;
  from_city: string;
  to_city: string;
  pickup: string;
  dropoff: string;
  trip_date: string;
  trip_time: string;
  price: string;
  tariff: string;
  commission: string;
  driver_amount: string;
  phone: string;
  passengers: number;
  luggage: number;
  booster: boolean;
  child_seat: boolean;
  animal: boolean;
  comment: string;
  status: string;
  created_at: string;
}

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  new: { label: "Новая", color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/30" },
  assigned: { label: "Назначена", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/30" },
  in_progress: { label: "В пути", color: "text-green-400", bg: "bg-green-500/10 border-green-500/30" },
  done: { label: "Выполнена", color: "text-muted-foreground", bg: "bg-muted/30 border-border" },
  cancelled: { label: "Отменена", color: "text-red-400", bg: "bg-red-500/10 border-red-500/30" },
};

const STATUSES = ["new", "assigned", "in_progress", "done", "cancelled"];

interface Props { apiUrl: string }

export default function OrdersList({ apiUrl }: Props) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Order | null>(null);
  const [filterStatus, setFilterStatus] = useState("all");
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

  useEffect(() => { fetchOrders(); }, []);

  const updateStatus = async (id: string, status: string) => {
    setOrders((prev) => prev.map((o) => o.id === id ? { ...o, status } : o));
    if (selected?.id === id) setSelected((s) => s ? { ...s, status } : null);
    await fetch(apiUrl, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, status }),
    });
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

  const sendToTelegram = async (order: Order) => {
    setSending(true);
    try {
      const res = await fetch(TG_API, {
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
        // Обновляем статус на "assigned"
        await updateStatus(order.id, "assigned");
      } else {
        showToast("error", `Ошибка: ${data.error || "не удалось отправить"}`);
      }
    } catch {
      showToast("error", "Ошибка отправки в Telegram");
    } finally {
      setSending(false);
    }
  };

  const filtered = filterStatus === "all" ? orders : orders.filter((o) => o.status === filterStatus);

  const formatDate = (d: string) => {
    if (!d) return "—";
    const [y, m, day] = d.split("-");
    return `${day}.${m}.${y}`;
  };

  return (
    <div className="space-y-4">
      {/* Toast */}
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

      {/* Filter */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 bg-muted/50 border border-border rounded-lg p-1">
          <button
            onClick={() => setFilterStatus("all")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${filterStatus === "all" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
          >
            Все <span className="ml-1 mono opacity-60">{orders.length}</span>
          </button>
          {STATUSES.map((s) => {
            const cfg = statusConfig[s];
            const cnt = orders.filter((o) => o.status === s).length;
            return (
              <button
                key={s}
                onClick={() => setFilterStatus(s)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${filterStatus === s ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                {cfg.label} <span className="ml-1 mono opacity-60">{cnt}</span>
              </button>
            );
          })}
        </div>
        <button onClick={fetchOrders} className="p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all">
          <Icon name="RefreshCw" size={14} />
        </button>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 gap-3 text-muted-foreground">
            <Icon name="Loader" size={18} className="animate-spin" />
            <span className="text-sm">Загрузка заявок...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Icon name="ClipboardList" size={32} className="text-muted-foreground mb-3" />
            <div className="text-sm font-medium text-foreground mb-1">Нет заявок</div>
            <div className="text-xs text-muted-foreground">Создайте первую заявку в разделе «Новая заявка»</div>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {["Маршрут", "Дата / Время", "Тариф / Цена", "Клиент", "Статус", ""].map((h) => (
                  <th key={h} className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3 mono">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((order) => {
                const cfg = statusConfig[order.status] ?? statusConfig.new;
                return (
                  <tr
                    key={order.id}
                    onClick={() => setSelected(order.id === selected?.id ? null : order)}
                    className={`border-b border-border/50 hover:bg-muted/20 transition-colors cursor-pointer ${selected?.id === order.id ? "bg-blue-500/5" : ""}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
                        <div>
                          <div className="text-sm text-foreground font-medium truncate max-w-[180px]">{order.pickup}</div>
                          <div className="flex items-center gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                            <div className="text-xs text-muted-foreground truncate max-w-[180px]">{order.dropoff}</div>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm mono text-foreground">{formatDate(order.trip_date)}</div>
                      <div className="text-xs mono text-muted-foreground">{order.trip_time || "—"}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm text-foreground">{order.tariff}</div>
                      <div className="text-xs mono text-green-400 font-semibold">{Number(order.price || 0).toLocaleString("ru")} ₽</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm mono text-foreground">{order.phone}</div>
                      <div className="text-xs text-muted-foreground">{order.passengers} чел · {order.luggage} баг.</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.color}`}>
                        {cfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => deleteOrder(order.id)} className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all">
                        <Icon name="Trash2" size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail panel */}
      {selected && (
        <div className="bg-card border border-border rounded-xl p-5 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Icon name="MapPin" size={15} className="text-blue-400" />
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground">{selected.pickup} → {selected.dropoff}</div>
                <div className="text-[10px] text-muted-foreground mono">{selected.id.slice(0, 16)}...</div>
              </div>
            </div>
            <button onClick={() => setSelected(null)} className="text-muted-foreground hover:text-foreground p-1">
              <Icon name="X" size={16} />
            </button>
          </div>

          <div className="grid grid-cols-4 gap-3 mb-4">
            {[
              { label: "Дата", value: formatDate(selected.trip_date) },
              { label: "Время", value: selected.trip_time || "—" },
              { label: "Стоимость", value: `${Number(selected.price || 0).toLocaleString("ru")} ₽` },
              { label: "Водитель получит", value: `${Number(selected.driver_amount || 0).toLocaleString("ru")} ₽` },
              { label: "Клиент", value: selected.phone },
              { label: "Пассажиры", value: `${selected.passengers} чел.` },
              { label: "Багаж", value: `${selected.luggage} мест` },
              { label: "Тариф", value: selected.tariff },
            ].map((item) => (
              <div key={item.label} className="bg-muted/30 rounded-lg p-3">
                <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">{item.label}</div>
                <div className="text-sm font-medium text-foreground mono">{item.value}</div>
              </div>
            ))}
          </div>

          {(selected.booster || selected.child_seat || selected.animal) && (
            <div className="flex gap-2 mb-4">
              {selected.booster && <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Бустер</span>}
              {selected.child_seat && <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Детское кресло</span>}
              {selected.animal && <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Животное</span>}
            </div>
          )}

          {selected.comment && (
            <div className="mb-4 p-3 bg-muted/30 rounded-lg text-xs text-muted-foreground">{selected.comment}</div>
          )}

          {/* Отправить в Telegram */}
          <div className="mb-4 pb-4 border-b border-border">
            <button
              onClick={() => sendToTelegram(selected)}
              disabled={sending}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-all"
            >
              <Icon name={sending ? "Loader" : "Send"} size={15} className={sending ? "animate-spin" : ""} />
              {sending ? "Отправляю..." : "Отправить в группу"}
            </button>
          </div>

          {/* Status change */}
          <div>
            <div className="text-[10px] mono text-muted-foreground uppercase tracking-wider mb-2">Изменить статус</div>
            <div className="flex flex-wrap gap-2">
              {STATUSES.map((s) => {
                const cfg = statusConfig[s];
                return (
                  <button
                    key={s}
                    onClick={() => updateStatus(selected.id, s)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      selected.status === s ? `${cfg.bg} ${cfg.color}` : "bg-muted/30 border-border text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {cfg.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
