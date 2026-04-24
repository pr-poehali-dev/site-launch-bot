import { useState } from "react";
import Icon from "@/components/ui/icon";
import BotsSection from "@/components/admin/BotsSection";
import OrderForm from "@/components/admin/OrderForm";
import OrdersList from "@/components/admin/OrdersList";

const ORDERS_API = "https://functions.poehali.dev/55980dcf-a1ce-4d33-acc5-93fea15cb52c";
const TG_API = "https://functions.poehali.dev/ed779d34-4d03-4202-baa8-7d25732d1aaa";

type Section = "orders_new" | "orders_list" | "bots";

const navItems: { id: Section; label: string; icon: string }[] = [
  { id: "orders_new", label: "Новая заявка", icon: "Plus" },
  { id: "orders_list", label: "Заявки", icon: "ClipboardList" },
  { id: "bots", label: "Боты", icon: "Bot" },
];

export default function Index() {
  const [section, setSection] = useState<Section>("orders_new");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [saving, setSaving] = useState<null | "now" | "moderation">(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const showToast = (type: "success" | "error", text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSaveOrder = async (form: Record<string, unknown>, mode: "now" | "moderation") => {
    setSaving(mode);
    try {
      const body = {
        from_city: form.from,
        to_city: form.to,
        pickup: form.pickup,
        dropoff: form.dropoff,
        stops: form.stops,
        trip_date: form.date,
        trip_time: form.time,
        price: form.price,
        tariff: form.tariff,
        commission: form.commission,
        phone: form.phone,
        passengers: form.passengers,
        luggage: form.luggage,
        booster: form.booster,
        child_seat: form.childSeat,
        animal: form.animal,
        comment: form.comment,
      };

      // Сохраняем в БД
      const res = await fetch(ORDERS_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();

      if (!data.order?.id) {
        showToast("error", "Ошибка сохранения заявки");
        return;
      }

      // Отправляем в Telegram
      await fetch(TG_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, order: { ...body, id: data.order.id } }),
      });

      const modeLabel = mode === "now" ? "отправлена в работу" : "отправлена на модерацию";
      showToast("success", `Заявка ${modeLabel}!`);
      setTimeout(() => setSection("orders_list"), 1500);
    } catch {
      showToast("error", "Ошибка отправки в Telegram");
    } finally {
      setSaving(null);
    }
  };

  const sectionLabel = navItems.find((n) => n.id === section)?.label ?? "";

  return (
    <div className="flex h-screen bg-background overflow-hidden grid-bg">
      {/* Sidebar */}
      <aside className={`flex flex-col border-r border-border bg-[hsl(220,20%,6%)] transition-all duration-300 ${sidebarOpen ? "w-60" : "w-16"}`}>
        <div className="flex items-center gap-3 px-4 py-5 border-b border-border">
          <div className="w-8 h-8 rounded bg-[hsl(213,90%,55%)] flex items-center justify-center flex-shrink-0 pulse-blue">
            <Icon name="Cpu" size={16} className="text-white" />
          </div>
          {sidebarOpen && (
            <div className="animate-fade-in overflow-hidden">
              <div className="text-sm font-bold text-foreground tracking-wide">Диспетчер</div>
              <div className="text-[10px] text-muted-foreground mono uppercase tracking-widest">Admin Panel</div>
            </div>
          )}
        </div>

        <nav className="flex-1 py-4 space-y-0.5 px-2">
          {navItems.map((item) => {
            const isActive = section === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setSection(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition-all duration-150 relative
                  ${isActive
                    ? "bg-blue-500/10 text-blue-400"
                    : "text-[hsl(215,15%,55%)] hover:bg-[hsl(220,15%,12%)] hover:text-[hsl(210,20%,85%)]"
                  }`}
              >
                {isActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-400 rounded-r" />}
                <Icon name={item.icon} size={18} className="flex-shrink-0" />
                {sidebarOpen && <span className="text-sm font-medium flex-1 text-left animate-fade-in">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-3 border-t border-border space-y-1">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-muted-foreground hover:text-foreground hover:bg-[hsl(220,15%,12%)] transition-all"
          >
            <Icon name={sidebarOpen ? "PanelLeftClose" : "PanelLeftOpen"} size={18} className="flex-shrink-0" />
            {sidebarOpen && <span className="text-sm animate-fade-in">Свернуть</span>}
          </button>
          {sidebarOpen && (
            <div className="flex items-center gap-2.5 px-3 py-2 animate-fade-in">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center">
                <Icon name="User" size={12} className="text-blue-400" />
              </div>
              <div>
                <div className="text-xs font-medium text-foreground">Администратор</div>
                <div className="text-[10px] text-muted-foreground">admin@system.local</div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm flex-shrink-0">
          <div>
            <h1 className="text-base font-semibold text-foreground">{sectionLabel}</h1>
            <p className="text-xs text-muted-foreground mono">
              {new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
            </p>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-muted/50">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500 status-dot-active" />
            <span className="text-xs text-muted-foreground mono">Система онлайн</span>
          </div>
        </header>

        {/* Toast */}
        {toast && (
          <div className={`mx-6 mt-4 flex items-center gap-3 px-4 py-3 border rounded-lg animate-slide-up ${
            toast.type === "success"
              ? "bg-green-500/10 border-green-500/30"
              : "bg-red-500/10 border-red-500/30"
          }`}>
            <Icon
              name={toast.type === "success" ? "CheckCircle" : "AlertCircle"}
              size={16}
              className={toast.type === "success" ? "text-green-400" : "text-red-400"}
            />
            <span className={`text-sm font-medium ${toast.type === "success" ? "text-green-400" : "text-red-400"}`}>
              {toast.text}
            </span>
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          <div className="animate-slide-up">
            {section === "orders_new" && (
              <OrderForm onSave={handleSaveOrder} saving={saving} />
            )}
            {section === "orders_list" && (
              <OrdersList apiUrl={ORDERS_API} />
            )}
            {section === "bots" && <BotsSection />}
          </div>
        </main>
      </div>
    </div>
  );
}
