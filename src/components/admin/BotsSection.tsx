import { useState, useEffect } from "react";
import Icon from "@/components/ui/icon";

const API_URL = "https://functions.poehali.dev/346876f7-a09c-441f-9d67-515210f60fa7";

type BotStatus = "active" | "stopped" | "error" | "deploying";

interface Bot {
  id: string;
  name: string;
  status: BotStatus;
  version: string;
  uptime: string;
  requests: number;
  cpu: number;
  memory: number;
  last_deploy: string;
  environment: string;
  description: string;
}

const statusConfig: Record<BotStatus, { label: string; color: string; dot: string }> = {
  active: { label: "Активен", color: "text-green-400", dot: "bg-green-500 status-dot-active" },
  stopped: { label: "Остановлен", color: "text-muted-foreground", dot: "bg-muted-foreground" },
  error: { label: "Ошибка", color: "text-red-400", dot: "bg-red-500 status-dot-error" },
  deploying: { label: "Деплой...", color: "text-blue-400", dot: "bg-blue-400" },
};

const emptyForm = { name: "", version: "v1.0.0", environment: "production", description: "" };

export default function BotsSection() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);
  const [filter, setFilter] = useState<BotStatus | "all">("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const fetchBots = async () => {
    setLoading(true);
    try {
      const res = await fetch(API_URL);
      const data = await res.json();
      setBots(data.bots || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBots(); }, []);

  const filtered = filter === "all" ? bots : bots.filter((b) => b.status === filter);

  const handleAction = async (botId: string, action: "start" | "stop" | "deploy" | "restart") => {
    const statusMap: Record<string, BotStatus> = {
      start: "active",
      stop: "stopped",
      restart: "active",
      deploy: "deploying",
    };
    const uptimeMap: Record<string, string> = {
      start: "0ч 1м",
      stop: "—",
      restart: "0ч 0м",
      deploy: "—",
    };
    setBots((prev) =>
      prev.map((b) =>
        b.id === botId ? { ...b, status: statusMap[action], uptime: uptimeMap[action] } : b
      )
    );
    await fetch(API_URL, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: botId, status: statusMap[action], uptime: uptimeMap[action] }),
    });
  };

  const handleDelete = async (botId: string) => {
    setBots((prev) => prev.filter((b) => b.id !== botId));
    setSelectedBot(null);
    await fetch(API_URL, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: botId }),
    });
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (data.bot) {
        setBots((prev) => [data.bot, ...prev]);
        setForm(emptyForm);
        setShowForm(false);
      }
    } finally {
      setSaving(false);
    }
  };

  const counts = {
    all: bots.length,
    active: bots.filter((b) => b.status === "active").length,
    stopped: bots.filter((b) => b.status === "stopped").length,
    error: bots.filter((b) => b.status === "error").length,
  };

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Всего ботов", value: counts.all, icon: "Bot", color: "text-blue-400", bg: "bg-blue-500/10" },
          { label: "Активных", value: counts.active, icon: "Play", color: "text-green-400", bg: "bg-green-500/10" },
          { label: "Остановлено", value: counts.stopped, icon: "Square", color: "text-muted-foreground", bg: "bg-muted/50" },
          { label: "С ошибками", value: counts.error, icon: "AlertTriangle", color: "text-red-400", bg: "bg-red-500/10" },
        ].map((card) => (
          <div key={card.label} className="bg-card border border-border rounded-lg p-4 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg ${card.bg} flex items-center justify-center flex-shrink-0`}>
              <Icon name={card.icon} size={18} className={card.color} />
            </div>
            <div>
              <div className={`text-2xl font-bold mono ${card.color}`}>{card.value}</div>
              <div className="text-xs text-muted-foreground">{card.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filter + Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 bg-muted/50 border border-border rounded-lg p-1">
          {(["all", "active", "stopped", "error"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-all ${
                filter === f ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f === "all" ? "Все" : f === "active" ? "Активные" : f === "stopped" ? "Остановленные" : "Ошибки"}
              <span className="ml-1.5 mono opacity-60">{counts[f] ?? counts.all}</span>
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-all"
        >
          <Icon name="Plus" size={14} />
          Добавить бота
        </button>
      </div>

      {/* Add bot form */}
      {showForm && (
        <div className="bg-card border border-blue-500/30 rounded-lg p-5 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold text-foreground">Новый бот</div>
            <button onClick={() => { setShowForm(false); setForm(emptyForm); }} className="text-muted-foreground hover:text-foreground">
              <Icon name="X" size={16} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-[10px] mono uppercase tracking-wider text-muted-foreground block mb-1.5">Название *</label>
              <input
                className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-blue-500/60"
                placeholder="MyBot"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div>
              <label className="text-[10px] mono uppercase tracking-wider text-muted-foreground block mb-1.5">Версия</label>
              <input
                className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-blue-500/60 mono"
                placeholder="v1.0.0"
                value={form.version}
                onChange={(e) => setForm({ ...form, version: e.target.value })}
              />
            </div>
            <div>
              <label className="text-[10px] mono uppercase tracking-wider text-muted-foreground block mb-1.5">Среда</label>
              <div className="flex gap-2">
                {["production", "staging", "development"].map((env) => (
                  <button
                    key={env}
                    onClick={() => setForm({ ...form, environment: env })}
                    className={`flex-1 py-2 rounded-lg text-xs mono font-medium transition-all border ${
                      form.environment === env
                        ? "bg-blue-500/10 border-blue-500/40 text-blue-400"
                        : "bg-muted/30 border-border text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {env}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-[10px] mono uppercase tracking-wider text-muted-foreground block mb-1.5">Описание</label>
              <input
                className="w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-blue-500/60"
                placeholder="Краткое описание"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={saving || !form.name.trim()}
              className="flex items-center gap-2 px-5 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-all"
            >
              <Icon name={saving ? "Loader" : "Plus"} size={14} className={saving ? "animate-spin" : ""} />
              {saving ? "Создаю..." : "Создать бота"}
            </button>
            <button onClick={() => { setShowForm(false); setForm(emptyForm); }} className="px-5 py-2 bg-muted border border-border text-foreground text-sm rounded-lg hover:bg-muted/80 transition-all">
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 gap-3 text-muted-foreground">
            <Icon name="Loader" size={18} className="animate-spin" />
            <span className="text-sm">Загрузка ботов...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-14 h-14 rounded-full bg-muted/50 flex items-center justify-center mb-4">
              <Icon name="Bot" size={24} className="text-muted-foreground" />
            </div>
            <div className="text-sm font-medium text-foreground mb-1">
              {filter === "all" ? "Нет ботов" : `Нет ботов со статусом «${statusConfig[filter as BotStatus]?.label}»`}
            </div>
            <div className="text-xs text-muted-foreground mb-4">
              {filter === "all" ? "Нажмите «Добавить бота», чтобы создать первого" : "Попробуйте выбрать другой фильтр"}
            </div>
            {filter === "all" && (
              <button
                onClick={() => setShowForm(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-all"
              >
                <Icon name="Plus" size={14} />
                Добавить бота
              </button>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                {["Бот", "Статус", "Версия", "Среда", "Аптайм", "Запросы", "CPU / RAM", "Действия"].map((h) => (
                  <th key={h} className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-4 py-3 mono">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((bot, i) => {
                const s = statusConfig[bot.status] ?? statusConfig.stopped;
                return (
                  <tr
                    key={bot.id}
                    className={`border-b border-border/50 hover:bg-muted/30 transition-colors cursor-pointer ${selectedBot?.id === bot.id ? "bg-blue-500/5" : ""}`}
                    onClick={() => setSelectedBot(bot.id === selectedBot?.id ? null : bot)}
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded bg-muted flex items-center justify-center">
                          <Icon name="Bot" size={14} className="text-muted-foreground" />
                        </div>
                        <div>
                          <div className="text-sm font-medium text-foreground">{bot.name}</div>
                          <div className="text-[10px] text-muted-foreground mono">{bot.id.slice(0, 8)}...</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                        <span className={`text-xs font-medium ${s.color}`}>{s.label}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs mono text-muted-foreground bg-muted px-2 py-0.5 rounded">{bot.version}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] mono uppercase px-2 py-0.5 rounded border ${
                        bot.environment === "production"
                          ? "border-green-500/30 text-green-400 bg-green-500/5"
                          : "border-yellow-500/30 text-yellow-400 bg-yellow-500/5"
                      }`}>
                        {bot.environment}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs mono text-muted-foreground">{bot.uptime || "—"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs mono text-foreground">{(bot.requests || 0).toLocaleString("ru")}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] mono text-muted-foreground w-8">CPU</span>
                          <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${bot.cpu || 0}%` }} />
                          </div>
                          <span className="text-[10px] mono text-muted-foreground w-6">{bot.cpu || 0}%</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] mono text-muted-foreground w-8">RAM</span>
                          <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${bot.memory || 0}%` }} />
                          </div>
                          <span className="text-[10px] mono text-muted-foreground w-6">{bot.memory || 0}%</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        {bot.status !== "active" && (
                          <button onClick={() => handleAction(bot.id, "start")} className="p-1.5 rounded hover:bg-green-500/10 text-muted-foreground hover:text-green-400 transition-all" title="Запустить">
                            <Icon name="Play" size={13} />
                          </button>
                        )}
                        {bot.status === "active" && (
                          <button onClick={() => handleAction(bot.id, "stop")} className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all" title="Остановить">
                            <Icon name="Square" size={13} />
                          </button>
                        )}
                        <button onClick={() => handleAction(bot.id, "restart")} className="p-1.5 rounded hover:bg-yellow-500/10 text-muted-foreground hover:text-yellow-400 transition-all" title="Перезапустить">
                          <Icon name="RotateCcw" size={13} />
                        </button>
                        <button onClick={() => handleAction(bot.id, "deploy")} className="p-1.5 rounded hover:bg-blue-500/10 text-muted-foreground hover:text-blue-400 transition-all" title="Деплой">
                          <Icon name="Upload" size={13} />
                        </button>
                        <button onClick={() => handleDelete(bot.id)} className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all" title="Удалить">
                          <Icon name="Trash2" size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Bot detail panel */}
      {selectedBot && (
        <div className="bg-card border border-border rounded-lg p-5 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Icon name="Bot" size={18} className="text-blue-400" />
              </div>
              <div>
                <div className="font-semibold text-foreground">{selectedBot.name}</div>
                <div className="text-xs text-muted-foreground mono">{selectedBot.id} · {selectedBot.version}</div>
              </div>
            </div>
            <button onClick={() => setSelectedBot(null)} className="text-muted-foreground hover:text-foreground p-1">
              <Icon name="X" size={16} />
            </button>
          </div>
          {selectedBot.description && (
            <p className="text-xs text-muted-foreground mb-4 bg-muted/30 rounded-lg px-3 py-2">{selectedBot.description}</p>
          )}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Последний деплой", value: selectedBot.last_deploy || "—" },
              { label: "Среда", value: selectedBot.environment },
              { label: "Аптайм", value: selectedBot.uptime || "—" },
              { label: "Запросов всего", value: (selectedBot.requests || 0).toLocaleString("ru") },
              { label: "CPU", value: (selectedBot.cpu || 0) + "%" },
              { label: "Память", value: (selectedBot.memory || 0) + "%" },
            ].map((item) => (
              <div key={item.label} className="bg-muted/30 rounded-lg p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mono mb-1">{item.label}</div>
                <div className="text-sm font-medium text-foreground mono">{item.value}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={() => handleAction(selectedBot.id, "deploy")} className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-all">
              <Icon name="Upload" size={14} />
              Задеплоить
            </button>
            <button onClick={() => handleAction(selectedBot.id, "restart")} className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground text-sm font-medium rounded-lg transition-all border border-border">
              <Icon name="RotateCcw" size={14} />
              Рестарт
            </button>
            <button onClick={() => handleDelete(selectedBot.id)} className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium rounded-lg transition-all border border-red-500/30 ml-auto">
              <Icon name="Trash2" size={14} />
              Удалить
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
