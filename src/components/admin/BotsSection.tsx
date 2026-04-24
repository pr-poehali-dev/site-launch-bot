import { useState } from "react";
import Icon from "@/components/ui/icon";

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
  lastDeploy: string;
  environment: string;
}

const initialBots: Bot[] = [
  { id: "bot-001", name: "MarketBot Alpha", status: "active", version: "v2.4.1", uptime: "12д 4ч", requests: 48320, cpu: 12, memory: 34, lastDeploy: "20.04.2026", environment: "production" },
  { id: "bot-002", name: "SupportBot X", status: "active", version: "v1.9.3", uptime: "3д 18ч", requests: 12440, cpu: 8, memory: 21, lastDeploy: "22.04.2026", environment: "production" },
  { id: "bot-003", name: "AnalyticsBot", status: "stopped", version: "v3.1.0", uptime: "—", requests: 0, cpu: 0, memory: 0, lastDeploy: "15.04.2026", environment: "staging" },
  { id: "bot-004", name: "NewsParser Pro", status: "error", version: "v1.2.7", uptime: "0ч 12м", requests: 220, cpu: 2, memory: 5, lastDeploy: "23.04.2026", environment: "production" },
  { id: "bot-005", name: "CryptoTracker", status: "active", version: "v4.0.0", uptime: "7д 2ч", requests: 91200, cpu: 22, memory: 48, lastDeploy: "17.04.2026", environment: "production" },
  { id: "bot-006", name: "ReportBot", status: "stopped", version: "v2.0.5", uptime: "—", requests: 0, cpu: 0, memory: 0, lastDeploy: "10.04.2026", environment: "staging" },
];

const statusConfig: Record<BotStatus, { label: string; color: string; dot: string }> = {
  active: { label: "Активен", color: "text-green-400", dot: "bg-green-500 status-dot-active" },
  stopped: { label: "Остановлен", color: "text-muted-foreground", dot: "bg-muted-foreground" },
  error: { label: "Ошибка", color: "text-red-400", dot: "bg-red-500 status-dot-error" },
  deploying: { label: "Деплой...", color: "text-blue-400", dot: "bg-blue-400" },
};

export default function BotsSection() {
  const [bots, setBots] = useState<Bot[]>(initialBots);
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);
  const [filter, setFilter] = useState<BotStatus | "all">("all");

  const filtered = filter === "all" ? bots : bots.filter((b) => b.status === filter);

  const handleAction = (botId: string, action: "start" | "stop" | "deploy" | "restart") => {
    setBots((prev) =>
      prev.map((b) => {
        if (b.id !== botId) return b;
        if (action === "start") return { ...b, status: "active", uptime: "0ч 1м" };
        if (action === "stop") return { ...b, status: "stopped", uptime: "—" };
        if (action === "restart") return { ...b, status: "active", uptime: "0ч 0м" };
        if (action === "deploy") return { ...b, status: "deploying" };
        return b;
      })
    );
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
                filter === f
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {f === "all" ? "Все" : f === "active" ? "Активные" : f === "stopped" ? "Остановленные" : "Ошибки"}
              <span className="ml-1.5 mono opacity-60">{counts[f] ?? counts.all}</span>
            </button>
          ))}
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-all">
          <Icon name="Plus" size={14} />
          Добавить бота
        </button>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
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
              const s = statusConfig[bot.status];
              return (
                <tr
                  key={bot.id}
                  className={`border-b border-border/50 hover:bg-muted/30 transition-colors cursor-pointer
                    ${selectedBot?.id === bot.id ? "bg-blue-500/5" : ""}`}
                  onClick={() => setSelectedBot(bot === selectedBot ? null : bot)}
                  style={{ animationDelay: `${i * 40}ms` }}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded bg-muted flex items-center justify-center">
                        <Icon name="Bot" size={14} className="text-muted-foreground" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-foreground">{bot.name}</div>
                        <div className="text-[10px] text-muted-foreground mono">{bot.id}</div>
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
                    <span className={`text-[10px] mono uppercase px-2 py-0.5 rounded border
                      ${bot.environment === "production"
                        ? "border-green-500/30 text-green-400 bg-green-500/5"
                        : "border-yellow-500/30 text-yellow-400 bg-yellow-500/5"}`}>
                      {bot.environment}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs mono text-muted-foreground">{bot.uptime}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs mono text-foreground">{bot.requests.toLocaleString("ru")}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] mono text-muted-foreground w-8">CPU</span>
                        <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${bot.cpu}%` }} />
                        </div>
                        <span className="text-[10px] mono text-muted-foreground w-6">{bot.cpu}%</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] mono text-muted-foreground w-8">RAM</span>
                        <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-purple-500 rounded-full transition-all" style={{ width: `${bot.memory}%` }} />
                        </div>
                        <span className="text-[10px] mono text-muted-foreground w-6">{bot.memory}%</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-1">
                      {bot.status !== "active" && (
                        <button
                          onClick={() => handleAction(bot.id, "start")}
                          className="p-1.5 rounded hover:bg-green-500/10 text-muted-foreground hover:text-green-400 transition-all"
                          title="Запустить"
                        >
                          <Icon name="Play" size={13} />
                        </button>
                      )}
                      {bot.status === "active" && (
                        <button
                          onClick={() => handleAction(bot.id, "stop")}
                          className="p-1.5 rounded hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all"
                          title="Остановить"
                        >
                          <Icon name="Square" size={13} />
                        </button>
                      )}
                      <button
                        onClick={() => handleAction(bot.id, "restart")}
                        className="p-1.5 rounded hover:bg-yellow-500/10 text-muted-foreground hover:text-yellow-400 transition-all"
                        title="Перезапустить"
                      >
                        <Icon name="RotateCcw" size={13} />
                      </button>
                      <button
                        onClick={() => handleAction(bot.id, "deploy")}
                        className="p-1.5 rounded hover:bg-blue-500/10 text-muted-foreground hover:text-blue-400 transition-all"
                        title="Задеплоить"
                      >
                        <Icon name="Upload" size={13} />
                      </button>
                      <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-all" title="Настройки">
                        <Icon name="MoreVertical" size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Последний деплой", value: selectedBot.lastDeploy },
              { label: "Среда", value: selectedBot.environment },
              { label: "Аптайм", value: selectedBot.uptime },
              { label: "Запросов всего", value: selectedBot.requests.toLocaleString("ru") },
              { label: "CPU", value: selectedBot.cpu + "%" },
              { label: "Память", value: selectedBot.memory + "%" },
            ].map((item) => (
              <div key={item.label} className="bg-muted/30 rounded-lg p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mono mb-1">{item.label}</div>
                <div className="text-sm font-medium text-foreground mono">{item.value}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-4">
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-all">
              <Icon name="Upload" size={14} />
              Задеплоить
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground text-sm font-medium rounded-lg transition-all border border-border">
              <Icon name="FileText" size={14} />
              Логи
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground text-sm font-medium rounded-lg transition-all border border-border">
              <Icon name="Settings" size={14} />
              Параметры
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
