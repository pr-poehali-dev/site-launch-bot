import Icon from "@/components/ui/icon";
import { Order, STATUSES, statusConfig } from "./orderTypes";
import OrderEditForm from "./OrderEditForm";

interface Props {
  selected: Order;
  editing: boolean;
  editForm: Partial<Order>;
  saving: boolean;
  sending: boolean;
  onClose: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onEditChange: (patch: Partial<Order>) => void;
  onSave: () => void;
  onSendToTelegram: () => void;
  onSell: () => void;
  onUpdateStatus: (status: string) => void;
}

function formatDate(d: string) {
  if (!d) return "—";
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y}`;
}

export default function OrderDetailPanel({
  selected, editing, editForm, saving, sending,
  onClose, onStartEdit, onCancelEdit, onEditChange, onSave,
  onSendToTelegram, onSell, onUpdateStatus,
}: Props) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 animate-slide-up">
      {/* Header */}
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
        <div className="flex items-center gap-2">
          {!editing ? (
            <button onClick={onStartEdit} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted/40 hover:bg-muted/70 text-muted-foreground hover:text-foreground text-xs font-medium transition-all">
              <Icon name="Pencil" size={13} />
              Редактировать
            </button>
          ) : (
            <button onClick={onCancelEdit} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-muted/40 hover:bg-muted/70 text-muted-foreground text-xs transition-all">
              Отмена
            </button>
          )}
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground p-1">
            <Icon name="X" size={16} />
          </button>
        </div>
      </div>

      {/* Edit form or view */}
      {editing ? (
        <OrderEditForm editForm={editForm} saving={saving} onChange={onEditChange} onSave={onSave} />
      ) : (
        <>
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

          {(selected.booster || selected.child_seat || selected.animal || selected.comment) && (
            <div className="mb-4 p-3 bg-muted/30 rounded-lg flex flex-col gap-1.5">
              {selected.booster && <span className="text-xs text-foreground">🪑 Бустер</span>}
              {selected.child_seat && <span className="text-xs text-foreground">👶 Детское кресло</span>}
              {selected.animal && <span className="text-xs text-foreground">🐾 Животное</span>}
              {selected.comment && <span className="text-xs text-muted-foreground">💬 {selected.comment}</span>}
            </div>
          )}
        </>
      )}

      {/* Driver info */}
      {selected.driver_chat_id ? (
        <div className="mb-4 p-3 bg-green-500/5 border border-green-500/20 rounded-lg">
          <div className="text-[10px] mono uppercase tracking-wider text-green-400 mb-2">Водитель принял заказ</div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center flex-shrink-0">
              <Icon name="User" size={15} className="text-green-400" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">{selected.driver_name || "—"}</div>
              {selected.driver_username && (
                <div className="text-xs text-muted-foreground">@{selected.driver_username}</div>
              )}
              <div className="text-[10px] text-muted-foreground mono mt-0.5">ID: {selected.driver_chat_id}</div>
            </div>
            {selected.payment_url && (
              <a
                href={selected.payment_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium hover:bg-green-500/20 transition-all"
              >
                <Icon name="CreditCard" size={13} />
                Ссылка на оплату
              </a>
            )}
          </div>
        </div>
      ) : (
        <div className="mb-4 p-3 bg-muted/20 border border-border rounded-lg">
          <div className="text-[10px] mono uppercase tracking-wider text-muted-foreground mb-1">Водитель</div>
          <div className="text-xs text-muted-foreground">Ещё не принял заказ</div>
        </div>
      )}

      {/* Actions */}
      <div className="mb-4 pb-4 border-b border-border flex flex-wrap gap-2">
        <button
          onClick={onSendToTelegram}
          disabled={sending || selected.status === "on_sale"}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-all"
        >
          <Icon name={sending ? "Loader" : "Send"} size={15} className={sending ? "animate-spin" : ""} />
          {sending ? "Отправляю..." : selected.status === "on_sale" ? "Уже на продаже" : "Отправить в группу"}
        </button>
        <button
          onClick={onSell}
          disabled={selected.status === "on_sale"}
          className="flex items-center gap-2 px-4 py-2.5 bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 disabled:opacity-40 disabled:cursor-not-allowed text-yellow-400 text-sm font-semibold rounded-lg transition-all"
        >
          <Icon name="Tag" size={15} />
          {selected.status === "on_sale" ? "На продаже" : "Продать заказ"}
        </button>
      </div>

      {/* Status switcher */}
      <div>
        <div className="text-[10px] mono text-muted-foreground uppercase tracking-wider mb-2">Изменить статус</div>
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => {
            const cfg = statusConfig[s];
            return (
              <button
                key={s}
                onClick={() => onUpdateStatus(s)}
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
  );
}