import { useState } from "react";
import Icon from "@/components/ui/icon";

const TARIFFS = ["Срочный", "Стандарт", "Комфорт", "Бизнес", "Минивэн"];
const COMMISSION_OPTIONS = ["10%", "15%", "20%", "25%"];

interface Stop {
  id: string;
  address: string;
}

interface OrderForm {
  from: string;
  to: string;
  pickup: string;
  dropoff: string;
  stops: Stop[];
  date: string;
  time: string;
  price: string;
  tariff: string;
  commission: string;
  phone: string;
  passengers: number;
  luggage: number;
  booster: boolean;
  childSeat: boolean;
  animal: boolean;
  comment: string;
}

const today = new Date().toISOString().slice(0, 10);

const empty: OrderForm = {
  from: "",
  to: "",
  pickup: "",
  dropoff: "",
  stops: [],
  date: today,
  time: "",
  price: "",
  tariff: "Комфорт",
  commission: "15%",
  phone: "",
  passengers: 1,
  luggage: 1,
  booster: false,
  childSeat: false,
  animal: false,
  comment: "",
};

const inputCls = (err?: string) =>
  `w-full bg-muted/30 border rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none focus:border-blue-500/60 transition-colors ${err ? "border-red-500/50" : "border-border"}`;

function Field({
  label, required, error, children,
}: { label: string; required?: boolean; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] mono uppercase tracking-wider text-muted-foreground block mb-1.5">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
      {error && <div className="text-xs text-red-400 mt-1">{error}</div>}
    </div>
  );
}

interface Props {
  onSave: (order: OrderForm, mode: "now" | "moderation") => void;
  saving?: "now" | "moderation" | null;
}

export default function OrderForm({ onSave, saving }: Props) {
  const [form, setForm] = useState<OrderForm>(empty);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (key: keyof OrderForm, val: unknown) =>
    setForm((prev) => ({ ...prev, [key]: val }));

  const addStop = () =>
    setForm((prev) => ({
      ...prev,
      stops: [...prev.stops, { id: Date.now().toString(), address: "" }],
    }));

  const updateStop = (id: string, address: string) =>
    setForm((prev) => ({
      ...prev,
      stops: prev.stops.map((s) => (s.id === id ? { ...s, address } : s)),
    }));

  const removeStop = (id: string) =>
    setForm((prev) => ({ ...prev, stops: prev.stops.filter((s) => s.id !== id) }));

  const commission = parseInt(form.commission) / 100;
  const price = parseFloat(form.price) || 0;
  const driverAmount = Math.round(price * (1 - commission));

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.pickup.trim()) e.pickup = "Обязательное поле";
    if (!form.dropoff.trim()) e.dropoff = "Обязательное поле";
    if (!form.price.trim()) e.price = "Укажите стоимость";
    if (!form.phone.trim()) e.phone = "Укажите номер";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (mode: "now" | "moderation") => {
    if (validate()) onSave(form, mode);
  };

  const reset = () => {
    setForm(empty);
    setErrors({});
  };

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <Icon name="MapPin" size={16} className="text-blue-400" />
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">Новая заявка</div>
            <div className="text-[10px] text-muted-foreground mono">Заполните данные поездки</div>
          </div>
        </div>
        <button onClick={reset} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-colors">
          <Icon name="RotateCcw" size={13} />
          Сбросить
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* Маршрут */}
        <div>
          <div className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="Navigation" size={14} className="text-blue-400" />
            Маршрут
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Откуда">
                <input className={inputCls()} placeholder="Город или регион" value={form.from} onChange={(e) => set("from", e.target.value)} />
              </Field>
              <Field label="Куда">
                <input className={inputCls()} placeholder="Город или регион" value={form.to} onChange={(e) => set("to", e.target.value)} />
              </Field>
            </div>

            {/* Pickup + Dropoff */}
            <div className="relative pl-6">
              <div className="absolute left-2 top-3 bottom-3 w-px bg-border" />
              <div className="absolute left-[5px] top-3 w-2.5 h-2.5 rounded-full bg-green-500 border-2 border-background" />
              <div className="absolute left-[5px] bottom-3 w-2.5 h-2.5 rounded-full bg-red-500 border-2 border-background" />

              <div className="space-y-2">
                <Field label="Откуда забрать" required error={errors.pickup}>
                  <input
                    className={inputCls(errors.pickup)}
                    placeholder="Точный адрес подачи"
                    value={form.pickup}
                    onChange={(e) => { set("pickup", e.target.value); setErrors((p) => ({ ...p, pickup: "" })); }}
                  />
                </Field>

                {form.stops.map((stop) => (
                  <div key={stop.id} className="flex gap-2">
                    <input
                      className={inputCls() + " flex-1"}
                      placeholder="Промежуточный адрес"
                      value={stop.address}
                      onChange={(e) => updateStop(stop.id, e.target.value)}
                    />
                    <button onClick={() => removeStop(stop.id)} className="p-2.5 rounded-lg border border-border text-muted-foreground hover:text-red-400 hover:border-red-500/30 transition-all">
                      <Icon name="X" size={13} />
                    </button>
                  </div>
                ))}

                <Field label="Куда довести" required error={errors.dropoff}>
                  <input
                    className={inputCls(errors.dropoff)}
                    placeholder="Точный адрес назначения"
                    value={form.dropoff}
                    onChange={(e) => { set("dropoff", e.target.value); setErrors((p) => ({ ...p, dropoff: "" })); }}
                  />
                </Field>
              </div>
            </div>

            <button
              onClick={addStop}
              className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              <Icon name="Plus" size={13} />
              Добавить промежуточный адрес
            </button>
          </div>
        </div>

        {/* Время */}
        <div>
          <div className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="Clock" size={14} className="text-blue-400" />
            Время и дата
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Дата поездки" required>
              <input
                type="date"
                className={inputCls() + " mono"}
                value={form.date}
                onChange={(e) => set("date", e.target.value)}
              />
            </Field>
            <Field label="Время начала поездки">
              <input
                type="time"
                className={inputCls() + " mono"}
                value={form.time}
                onChange={(e) => set("time", e.target.value)}
              />
            </Field>
          </div>
        </div>

        {/* Тариф и стоимость */}
        <div>
          <div className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="CreditCard" size={14} className="text-blue-400" />
            Тариф и стоимость
          </div>
          <div className="space-y-3">
            <Field label="Тариф" required>
              <div className="flex flex-wrap gap-2">
                {TARIFFS.map((t) => (
                  <button
                    key={t}
                    onClick={() => {
                      set("tariff", t);
                      if (t === "Срочный") {
                        const now = new Date();
                        now.setMinutes(now.getMinutes() + 30);
                        const hh = String(now.getHours()).padStart(2, "0");
                        const mm = String(now.getMinutes()).padStart(2, "0");
                        const yyyy = now.getFullYear();
                        const mo = String(now.getMonth() + 1).padStart(2, "0");
                        const dd = String(now.getDate()).padStart(2, "0");
                        setForm((prev) => ({ ...prev, tariff: t, date: `${yyyy}-${mo}-${dd}`, time: `${hh}:${mm}` }));
                      }
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      form.tariff === t
                        ? "bg-blue-500/10 border-blue-500/40 text-blue-400"
                        : "bg-muted/30 border-border text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Стоимость (₽)" required error={errors.price}>
                <div className="relative">
                  <input
                    type="number"
                    className={inputCls(errors.price) + " pr-8 mono"}
                    placeholder="0"
                    value={form.price}
                    onChange={(e) => { set("price", e.target.value); setErrors((p) => ({ ...p, price: "" })); }}
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">₽</span>
                </div>
              </Field>
              <Field label="Процент комиссии" required>
                <div className="flex gap-2">
                  {COMMISSION_OPTIONS.map((c) => (
                    <button
                      key={c}
                      onClick={() => set("commission", c)}
                      className={`flex-1 py-2.5 rounded-lg text-xs font-medium mono border transition-all ${
                        form.commission === c
                          ? "bg-blue-500/10 border-blue-500/40 text-blue-400"
                          : "bg-muted/30 border-border text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </Field>
            </div>

            {price > 0 && (
              <div className="flex items-center justify-between bg-muted/30 border border-border rounded-lg px-4 py-3">
                <span className="text-xs text-muted-foreground">Водитель получит:</span>
                <span className="text-sm font-bold mono text-green-400">{driverAmount.toLocaleString("ru")} ₽</span>
              </div>
            )}
          </div>
        </div>

        {/* Клиент */}
        <div>
          <div className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="User" size={14} className="text-blue-400" />
            Клиент
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Номер клиента" required error={errors.phone}>
              <input
                type="tel"
                className={inputCls(errors.phone)}
                placeholder="+7 (999) 000-00-00"
                value={form.phone}
                onChange={(e) => { set("phone", e.target.value); setErrors((p) => ({ ...p, phone: "" })); }}
              />
            </Field>
            <Field label="Кол-во человек" required>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => set("passengers", Math.max(1, form.passengers - 1))}
                  className="w-9 h-9 rounded-lg border border-border bg-muted/30 text-foreground hover:bg-muted transition-all flex items-center justify-center flex-shrink-0"
                >
                  <Icon name="Minus" size={13} />
                </button>
                <div className="flex-1 text-center text-sm font-semibold mono text-foreground">{form.passengers}</div>
                <button
                  onClick={() => set("passengers", form.passengers + 1)}
                  className="w-9 h-9 rounded-lg border border-border bg-muted/30 text-foreground hover:bg-muted transition-all flex items-center justify-center flex-shrink-0"
                >
                  <Icon name="Plus" size={13} />
                </button>
              </div>
            </Field>
            <Field label="Кол-во багажа" required>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => set("luggage", Math.max(0, form.luggage - 1))}
                  className="w-9 h-9 rounded-lg border border-border bg-muted/30 text-foreground hover:bg-muted transition-all flex items-center justify-center flex-shrink-0"
                >
                  <Icon name="Minus" size={13} />
                </button>
                <div className="flex-1 text-center text-sm font-semibold mono text-foreground">{form.luggage}</div>
                <button
                  onClick={() => set("luggage", form.luggage + 1)}
                  className="w-9 h-9 rounded-lg border border-border bg-muted/30 text-foreground hover:bg-muted transition-all flex items-center justify-center flex-shrink-0"
                >
                  <Icon name="Plus" size={13} />
                </button>
              </div>
            </Field>
          </div>
        </div>

        {/* Опции */}
        <div>
          <div className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Icon name="Settings2" size={14} className="text-blue-400" />
            Дополнительно
          </div>
          <div className="flex gap-3 flex-wrap mb-3">
            {[
              { key: "booster", label: "Бустер" },
              { key: "childSeat", label: "Детское кресло" },
              { key: "animal", label: "Животное" },
            ].map((opt) => {
              const val = form[opt.key as keyof OrderForm] as boolean;
              return (
                <button
                  key={opt.key}
                  onClick={() => set(opt.key as keyof OrderForm, !val)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm transition-all ${
                    val
                      ? "bg-blue-500/10 border-blue-500/40 text-blue-400"
                      : "bg-muted/30 border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <div className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${val ? "bg-blue-500 border-blue-500" : "border-muted-foreground/40"}`}>
                    {val && <Icon name="Check" size={10} className="text-white" />}
                  </div>
                  {opt.label}
                </button>
              );
            })}
          </div>
          <Field label="Комментарий">
            <textarea
              className={inputCls() + " resize-none"}
              placeholder="Пожелания клиента, особые условия..."
              rows={2}
              value={form.comment}
              onChange={(e) => set("comment", e.target.value)}
            />
          </Field>
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-border bg-muted/10">
        <div className="text-xs text-muted-foreground mb-3">
          {form.pickup && form.dropoff ? (
            <span className="text-foreground mono">{form.pickup} → {form.dropoff}</span>
          ) : (
            "Заполните обязательные поля"
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => handleSubmit("moderation")}
            disabled={!!saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-muted/50 hover:bg-muted border border-border disabled:opacity-50 text-foreground text-sm font-semibold rounded-lg transition-all"
          >
            <Icon name={saving === "moderation" ? "Loader" : "Clock"} size={15} className={saving === "moderation" ? "animate-spin" : "text-yellow-400"} />
            {saving === "moderation" ? "Отправляю..." : "На модерацию"}
          </button>
          <button
            onClick={() => handleSubmit("now")}
            disabled={!!saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-all"
          >
            <Icon name={saving === "now" ? "Loader" : "Zap"} size={15} className={saving === "now" ? "animate-spin" : ""} />
            {saving === "now" ? "Отправляю..." : "Отправить сейчас"}
          </button>
        </div>
      </div>
    </div>
  );
}