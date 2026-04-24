import { useState } from "react";
import Icon from "@/components/ui/icon";

type Priority = "critical" | "warning" | "info";
type NotifStatus = "new" | "read" | "resolved";

interface Notification {
  id: string;
  title: string;
  message: string;
  bot: string;
  priority: Priority;
  status: NotifStatus;
  time: string;
}

const initialNotifs: Notification[] = [
  { id: "n1", title: "Критическая ошибка деплоя", message: "NewsParser Pro не смог запуститься после деплоя. Ошибка: ModuleNotFoundError", bot: "NewsParser Pro", priority: "critical", status: "new", time: "2 мин назад" },
  { id: "n2", title: "Высокая нагрузка CPU", message: "CryptoTracker превысил 85% CPU в течение 10 минут", bot: "CryptoTracker", priority: "warning", status: "new", time: "18 мин назад" },
  { id: "n3", title: "Успешный деплой", message: "SupportBot X v1.9.3 успешно задеплоен в production", bot: "SupportBot X", priority: "info", status: "read", time: "1ч назад" },
  { id: "n4", title: "Превышен лимит запросов", message: "MarketBot Alpha превысил плановый лимит на 120%", bot: "MarketBot Alpha", priority: "warning", status: "read", time: "3ч назад" },
  { id: "n5", title: "Автоматический рестарт", message: "AnalyticsBot был перезапущен по расписанию (03:00)", bot: "AnalyticsBot", priority: "info", status: "resolved", time: "6ч назад" },
  { id: "n6", title: "Сертификат истекает", message: "SSL-сертификат для API-эндпоинта истекает через 7 дней", bot: "Система", priority: "warning", status: "new", time: "8ч назад" },
];

const priorityConfig: Record<Priority, { label: string; icon: string; color: string; bg: string; border: string }> = {
  critical: { label: "Критично", icon: "AlertCircle", color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/30" },
  warning: { label: "Внимание", icon: "AlertTriangle", color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/30" },
  info: { label: "Инфо", icon: "Info", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/30" },
};

const statusLabel: Record<NotifStatus, string> = { new: "Новое", read: "Прочитано", resolved: "Решено" };

export default function NotificationsSection() {
  const [notifs, setNotifs] = useState<Notification[]>(initialNotifs);
  const [filter, setFilter] = useState<Priority | "all">("all");
  const [showResolved, setShowResolved] = useState(false);

  const visible = notifs.filter((n) => {
    if (!showResolved && n.status === "resolved") return false;
    if (filter !== "all" && n.priority !== filter) return false;
    return true;
  });

  const markRead = (id: string) => {
    setNotifs((prev) => prev.map((n) => n.id === id ? { ...n, status: "read" } : n));
  };

  const resolve = (id: string) => {
    setNotifs((prev) => prev.map((n) => n.id === id ? { ...n, status: "resolved" } : n));
  };

  const newCount = notifs.filter((n) => n.status === "new").length;

  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {(["critical", "warning", "info"] as Priority[]).map((p) => {
          const cfg = priorityConfig[p];
          const count = notifs.filter((n) => n.priority === p && n.status !== "resolved").length;
          return (
            <div key={p} className={`bg-card border ${cfg.border} rounded-lg p-4 flex items-center gap-4`}>
              <div className={`w-10 h-10 rounded-lg ${cfg.bg} flex items-center justify-center`}>
                <Icon name={cfg.icon} size={18} className={cfg.color} />
              </div>
              <div>
                <div className={`text-2xl font-bold mono ${cfg.color}`}>{count}</div>
                <div className="text-xs text-muted-foreground">{cfg.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-muted/50 border border-border rounded-lg p-1">
            {(["all", "critical", "warning", "info"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                  filter === f ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {f === "all" ? "Все" : priorityConfig[f].label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowResolved(!showResolved)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs border transition-all ${
              showResolved ? "bg-muted border-border text-foreground" : "border-border/50 text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon name="CheckCheck" size={13} />
            Решённые
          </button>
        </div>
        {newCount > 0 && (
          <button
            onClick={() => setNotifs((prev) => prev.map((n) => n.status === "new" ? { ...n, status: "read" } : n))}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            Отметить все прочитанными ({newCount})
          </button>
        )}
      </div>

      {/* List */}
      <div className="space-y-2">
        {visible.length === 0 && (
          <div className="bg-card border border-border rounded-lg p-12 text-center">
            <Icon name="CheckCircle" size={32} className="text-green-400 mx-auto mb-3" />
            <div className="text-sm text-foreground font-medium">Нет активных уведомлений</div>
            <div className="text-xs text-muted-foreground mt-1">Все системы работают нормально</div>
          </div>
        )}
        {visible.map((n) => {
          const cfg = priorityConfig[n.priority];
          return (
            <div
              key={n.id}
              className={`bg-card border rounded-lg p-4 transition-all animate-fade-in
                ${n.status === "new" ? `${cfg.border} border-l-2` : "border-border"}
                ${n.status === "resolved" ? "opacity-50" : ""}`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-8 h-8 rounded-lg ${cfg.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                  <Icon name={cfg.icon} size={15} className={cfg.color} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-semibold text-foreground">{n.title}</span>
                    {n.status === "new" && (
                      <span className="text-[9px] mono uppercase px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-semibold">Новое</span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">{n.message}</p>
                  <div className="flex items-center gap-3 text-[10px] mono text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Icon name="Bot" size={10} />
                      {n.bot}
                    </span>
                    <span>·</span>
                    <span>{n.time}</span>
                    <span>·</span>
                    <span>{statusLabel[n.status]}</span>
                  </div>
                </div>
                {n.status !== "resolved" && (
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {n.status === "new" && (
                      <button
                        onClick={() => markRead(n.id)}
                        className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
                        title="Отметить прочитанным"
                      >
                        <Icon name="Check" size={13} />
                      </button>
                    )}
                    <button
                      onClick={() => resolve(n.id)}
                      className="p-1.5 rounded hover:bg-green-500/10 text-muted-foreground hover:text-green-400 transition-all"
                      title="Решено"
                    >
                      <Icon name="CheckCheck" size={13} />
                    </button>
                    <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-all" title="Подробнее">
                      <Icon name="ExternalLink" size={13} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
