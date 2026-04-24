import { useState } from "react";
import Icon from "@/components/ui/icon";

export default function SettingsSection() {
  const [autoRestart, setAutoRestart] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [autoScale, setAutoScale] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [maxCpu, setMaxCpu] = useState(80);
  const [maxMemory, setMaxMemory] = useState(70);
  const [deployEnv, setDeployEnv] = useState("production");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="max-w-3xl space-y-5">
      {/* System */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2">
          <Icon name="Server" size={15} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Системные параметры</span>
        </div>
        <div className="divide-y divide-border">
          {[
            { label: "Автоперезапуск при ошибке", desc: "Боты автоматически перезапускаются при падении", value: autoRestart, set: setAutoRestart },
            { label: "Push-уведомления", desc: "Получать оповещения об ошибках и событиях", value: notifications, set: setNotifications },
            { label: "Автомасштабирование", desc: "Автоматически увеличивать ресурсы при высокой нагрузке", value: autoScale, set: setAutoScale },
            { label: "Режим отладки", desc: "Расширенное логирование для всех ботов", value: debugMode, set: setDebugMode },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between px-5 py-4">
              <div>
                <div className="text-sm font-medium text-foreground">{item.label}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{item.desc}</div>
              </div>
              <button
                onClick={() => item.set(!item.value)}
                className={`relative w-11 h-6 rounded-full transition-all duration-200 flex-shrink-0 ${
                  item.value ? "bg-blue-500" : "bg-muted"
                }`}
              >
                <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200 ${
                  item.value ? "left-[22px]" : "left-0.5"
                }`} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Limits */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2">
          <Icon name="Sliders" size={15} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Лимиты ресурсов</span>
        </div>
        <div className="p-5 space-y-5">
          {[
            { label: "Максимальный CPU (%)", value: maxCpu, set: setMaxCpu, color: "bg-blue-500" },
            { label: "Максимальная память (%)", value: maxMemory, set: setMaxMemory, color: "bg-purple-500" },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-foreground">{item.label}</span>
                <span className="text-sm mono font-semibold text-foreground">{item.value}%</span>
              </div>
              <div className="relative h-2 bg-muted rounded-full">
                <div className={`absolute left-0 top-0 h-full ${item.color} rounded-full transition-all`} style={{ width: `${item.value}%` }} />
                <input
                  type="range"
                  min={20}
                  max={100}
                  value={item.value}
                  onChange={(e) => item.set(Number(e.target.value))}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-[10px] mono text-muted-foreground">20%</span>
                <span className="text-[10px] mono text-muted-foreground">100%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Deploy settings */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center gap-2">
          <Icon name="Upload" size={15} className="text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">Настройки деплоя</span>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider mono block mb-2">Среда по умолчанию</label>
            <div className="flex gap-2">
              {["production", "staging", "development"].map((env) => (
                <button
                  key={env}
                  onClick={() => setDeployEnv(env)}
                  className={`px-4 py-2 rounded-lg text-xs mono font-medium transition-all border ${
                    deployEnv === env
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
            <label className="text-xs text-muted-foreground uppercase tracking-wider mono block mb-2">Registry URL</label>
            <div className="flex items-center gap-2 px-3 py-2 bg-muted/30 border border-border rounded-lg">
              <Icon name="Link" size={14} className="text-muted-foreground flex-shrink-0" />
              <span className="text-sm mono text-muted-foreground">registry.internal.company.io</span>
            </div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground uppercase tracking-wider mono block mb-2">Webhook URL для оповещений</label>
            <div className="flex gap-2">
              <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-muted/30 border border-border rounded-lg">
                <Icon name="Webhook" size={14} className="text-muted-foreground flex-shrink-0" />
                <span className="text-sm mono text-muted-foreground">https://hooks.slack.com/services/***</span>
              </div>
              <button className="px-3 py-2 bg-muted/30 border border-border rounded-lg text-muted-foreground hover:text-foreground transition-all">
                <Icon name="Edit2" size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Danger zone */}
      <div className="bg-card border border-red-500/20 rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-red-500/20 flex items-center gap-2">
          <Icon name="AlertTriangle" size={15} className="text-red-400" />
          <span className="text-sm font-semibold text-red-400">Опасная зона</span>
        </div>
        <div className="p-5 space-y-3">
          {[
            { label: "Остановить все боты", icon: "Square", desc: "Немедленно остановить все запущенные боты" },
            { label: "Очистить все логи", icon: "Trash2", desc: "Удалить все логи старше 7 дней" },
            { label: "Сбросить настройки", icon: "RotateCcw", desc: "Вернуть все параметры к заводским" },
          ].map((action) => (
            <div key={action.label} className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium text-foreground">{action.label}</div>
                <div className="text-xs text-muted-foreground">{action.desc}</div>
              </div>
              <button className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-sm rounded-lg transition-all">
                <Icon name={action.icon} size={13} />
                {action.label.split(" ")[0]}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
            saved
              ? "bg-green-500 text-white"
              : "bg-blue-500 hover:bg-blue-600 text-white"
          }`}
        >
          <Icon name={saved ? "Check" : "Save"} size={15} />
          {saved ? "Сохранено!" : "Сохранить настройки"}
        </button>
        <span className="text-xs text-muted-foreground">Изменения вступят в силу немедленно</span>
      </div>
    </div>
  );
}
