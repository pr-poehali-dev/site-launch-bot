import Icon from "@/components/ui/icon";
import { Order } from "./orderTypes";

interface Props {
  editForm: Partial<Order>;
  saving: boolean;
  onChange: (patch: Partial<Order>) => void;
  onSave: () => void;
}

export default function OrderEditForm({ editForm, saving, onChange, onSave }: Props) {
  return (
    <div className="mb-4">
      <div className="grid grid-cols-2 gap-3 mb-3">
        {[
          { label: "Откуда (город)", key: "from_city" },
          { label: "Куда (город)", key: "to_city" },
          { label: "Адрес подачи", key: "pickup" },
          { label: "Адрес назначения", key: "dropoff" },
          { label: "Телефон клиента", key: "phone" },
          { label: "Тариф", key: "tariff" },
        ].map(({ label, key }) => (
          <div key={key}>
            <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">{label}</div>
            <input
              className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
              value={(editForm as Record<string, string>)[key] ?? ""}
              onChange={(e) => onChange({ [key]: e.target.value })}
            />
          </div>
        ))}
        <div>
          <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">Дата</div>
          <input
            type="date"
            className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
            value={editForm.trip_date ?? ""}
            onChange={(e) => onChange({ trip_date: e.target.value })}
          />
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">Время</div>
          <input
            type="time"
            className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
            value={editForm.trip_time ?? ""}
            onChange={(e) => onChange({ trip_time: e.target.value })}
          />
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">Цена ₽</div>
          <input
            type="number"
            className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
            value={editForm.price ?? ""}
            onChange={(e) => onChange({ price: e.target.value })}
          />
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">Пассажиры</div>
          <input
            type="number" min={1} max={20}
            className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
            value={editForm.passengers ?? 1}
            onChange={(e) => onChange({ passengers: Number(e.target.value) })}
          />
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">Багаж</div>
          <input
            type="number" min={0} max={20}
            className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50"
            value={editForm.luggage ?? 0}
            onChange={(e) => onChange({ luggage: Number(e.target.value) })}
          />
        </div>
      </div>
      <div className="mb-3">
        <div className="text-[10px] text-muted-foreground mono uppercase tracking-wider mb-1">Комментарий</div>
        <textarea
          rows={2}
          className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-blue-500/50 resize-none"
          value={editForm.comment ?? ""}
          onChange={(e) => onChange({ comment: e.target.value })}
        />
      </div>
      <div className="flex gap-4 mb-3">
        {[
          { key: "booster", label: "Бустер" },
          { key: "child_seat", label: "Детское кресло" },
          { key: "animal", label: "Животное" },
        ].map(({ key, label }) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={!!(editForm as Record<string, boolean>)[key]}
              onChange={(e) => onChange({ [key]: e.target.checked })}
              className="accent-blue-500"
            />
            {label}
          </label>
        ))}
      </div>
      <button
        onClick={onSave}
        disabled={saving}
        className="flex items-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-40 text-white text-sm font-semibold rounded-lg transition-all"
      >
        <Icon name={saving ? "Loader" : "Save"} size={15} className={saving ? "animate-spin" : ""} />
        {saving ? "Сохраняю..." : "Сохранить изменения"}
      </button>
    </div>
  );
}
