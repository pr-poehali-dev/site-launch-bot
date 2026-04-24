import Icon from "@/components/ui/icon";

const weekDays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const requestData = [42000, 58000, 51000, 73000, 88000, 62000, 91200];
const maxRequests = Math.max(...requestData);

const botStats = [
  { name: "CryptoTracker", requests: 91200, success: 99.2, avgMs: 48, color: "bg-blue-500" },
  { name: "MarketBot Alpha", requests: 48320, success: 98.7, avgMs: 120, color: "bg-green-500" },
  { name: "SupportBot X", requests: 12440, success: 97.1, avgMs: 210, color: "bg-purple-500" },
  { name: "NewsParser Pro", requests: 220, success: 44.5, avgMs: 890, color: "bg-red-500" },
];

const totalRequests = botStats.reduce((a, b) => a + b.requests, 0);

export default function StatsSection() {
  return (
    <div className="space-y-5">
      {/* Top metrics */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Запросов сегодня", value: "91,200", change: "+14%", icon: "Activity", up: true },
          { label: "Среднее время ответа", value: "148 мс", change: "-22мс", icon: "Zap", up: true },
          { label: "Успешных запросов", value: "98.4%", change: "+0.3%", icon: "CheckCircle", up: true },
          { label: "Ошибок за сутки", value: "1,456", change: "+320", icon: "XCircle", up: false },
        ].map((m) => (
          <div key={m.label} className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-muted-foreground">{m.label}</span>
              <Icon name={m.icon} size={15} className="text-muted-foreground" />
            </div>
            <div className="text-2xl font-bold mono text-foreground">{m.value}</div>
            <div className={`flex items-center gap-1 mt-1 text-xs mono ${m.up ? "text-green-400" : "text-red-400"}`}>
              <Icon name={m.up ? "TrendingUp" : "TrendingDown"} size={12} />
              {m.change} vs вчера
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Chart */}
        <div className="col-span-2 bg-card border border-border rounded-lg p-5">
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="text-sm font-semibold text-foreground">Запросы за неделю</div>
              <div className="text-xs text-muted-foreground mono">Все боты суммарно</div>
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground mono bg-muted px-2 py-1 rounded">
              <Icon name="Calendar" size={12} />
              18–24 апр
            </div>
          </div>
          <div className="flex items-end gap-3 h-36">
            {requestData.map((val, i) => {
              const height = Math.round((val / maxRequests) * 100);
              const isToday = i === 6;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                  <div className="text-[9px] mono text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                    {(val / 1000).toFixed(0)}k
                  </div>
                  <div className="w-full flex items-end" style={{ height: "112px" }}>
                    <div
                      className={`w-full rounded-t transition-all duration-500 ${isToday ? "bg-blue-500" : "bg-muted hover:bg-blue-500/50"}`}
                      style={{ height: `${height}%` }}
                    />
                  </div>
                  <div className={`text-[10px] mono ${isToday ? "text-blue-400 font-semibold" : "text-muted-foreground"}`}>
                    {weekDays[i]}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bot breakdown */}
        <div className="bg-card border border-border rounded-lg p-5">
          <div className="text-sm font-semibold text-foreground mb-4">Распределение по ботам</div>
          <div className="space-y-3">
            {botStats.map((bot) => {
              const pct = Math.round((bot.requests / totalRequests) * 100);
              return (
                <div key={bot.name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-foreground truncate">{bot.name}</span>
                    <span className="text-xs mono text-muted-foreground">{pct}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className={`h-full ${bot.color} rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Per-bot table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="px-5 py-3 border-b border-border">
          <div className="text-sm font-semibold text-foreground">Статистика по ботам</div>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              {["Бот", "Запросов", "Успешность", "Ср. ответ", "Тренд"].map((h) => (
                <th key={h} className="text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-5 py-3 mono">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {botStats.map((bot) => (
              <tr key={bot.name} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${bot.color}`} />
                    <span className="text-sm text-foreground">{bot.name}</span>
                  </div>
                </td>
                <td className="px-5 py-3 text-sm mono text-foreground">{bot.requests.toLocaleString("ru")}</td>
                <td className="px-5 py-3">
                  <span className={`text-sm mono font-medium ${bot.success > 95 ? "text-green-400" : bot.success > 80 ? "text-yellow-400" : "text-red-400"}`}>
                    {bot.success}%
                  </span>
                </td>
                <td className="px-5 py-3">
                  <span className={`text-sm mono ${bot.avgMs < 200 ? "text-green-400" : bot.avgMs < 500 ? "text-yellow-400" : "text-red-400"}`}>
                    {bot.avgMs} мс
                  </span>
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    {[40, 55, 48, 62, 58, 70, 65].map((v, i) => (
                      <div
                        key={i}
                        className={`w-1 rounded-full ${bot.color} opacity-70`}
                        style={{ height: `${v * 0.4}%`, minHeight: "3px", maxHeight: "20px" }}
                      />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
