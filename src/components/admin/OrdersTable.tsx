import Icon from "@/components/ui/icon";
import { Order, statusConfig } from "./orderTypes";

interface Props {
  orders: Order[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (order: Order) => void;
  onSell: (order: Order) => void;
  onDelete: (id: string) => void;
  onRefresh: () => void;
}

function formatDate(d: string) {
  if (!d) return "—";
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y}`;
}

export default function OrdersTable({ orders, loading, selectedId, onSelect, onSell, onDelete, onRefresh }: Props) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground mono">{orders.length} заявок</div>
        <button onClick={onRefresh} className="p-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all">
          <Icon name="RefreshCw" size={14} />
        </button>
      </div>

      <div className="bg-card border border-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 gap-3 text-muted-foreground">
            <Icon name="Loader" size={18} className="animate-spin" />
            <span className="text-sm">Загрузка заявок...</span>
          </div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Icon name="ClipboardList" size={32} className="text-muted-foreground mb-3" />
            <div className="text-sm font-medium text-foreground mb-1">Нет заявок</div>
            <div className="text-xs text-muted-foreground">В этом разделе пока пусто</div>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {["Маршрут", "Дата / Время", "Тариф / Цена", "Клиент", "Статус", ""].map((h) => (
                  <th key={h} className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3 mono">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => {
                const cfg = statusConfig[order.status] ?? statusConfig.new;
                return (
                  <tr
                    key={order.id}
                    onClick={() => onSelect(order)}
                    className={`border-b border-border/50 hover:bg-muted/20 transition-colors cursor-pointer ${selectedId === order.id ? "bg-blue-500/5" : ""}`}
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
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.color}`}>
                          {cfg.label}
                        </span>
                        {order.status === "new" && (
                          <button
                            onClick={() => onSell(order)}
                            className="text-[11px] font-medium px-2.5 py-1 rounded-full border bg-yellow-500/10 border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/20 transition-all"
                          >
                            Продать
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => onDelete(order.id)} className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all">
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
    </>
  );
}
