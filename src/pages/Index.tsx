import { useState } from "react";
import Icon from "@/components/ui/icon";
import BotsSection from "@/components/admin/BotsSection";
import StatsSection from "@/components/admin/StatsSection";
import NotificationsSection from "@/components/admin/NotificationsSection";
import SettingsSection from "@/components/admin/SettingsSection";

type Section = "bots" | "stats" | "notifications" | "settings";

const navItems = [
  { id: "bots" as Section, label: "Боты", icon: "Bot", badge: 12 },
  { id: "stats" as Section, label: "Статистика", icon: "BarChart3" },
  { id: "notifications" as Section, label: "Уведомления", icon: "Bell", badge: 3 },
  { id: "settings" as Section, label: "Настройки", icon: "Settings" },
];

export default function Index() {
  const [activeSection, setActiveSection] = useState<Section>("bots");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const currentSection = navItems.find((n) => n.id === activeSection);

  return (
    <div className="flex h-screen bg-background overflow-hidden grid-bg">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-border bg-[hsl(220,20%,6%)] transition-all duration-300 ${sidebarOpen ? "w-60" : "w-16"}`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-border">
          <div className="w-8 h-8 rounded bg-[hsl(213,90%,55%)] flex items-center justify-center flex-shrink-0 pulse-blue">
            <Icon name="Cpu" size={16} className="text-white" />
          </div>
          {sidebarOpen && (
            <div className="animate-fade-in overflow-hidden">
              <div className="text-sm font-bold text-foreground tracking-wide">BotControl</div>
              <div className="text-[10px] text-muted-foreground mono uppercase tracking-widest">Admin Panel</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-0.5 px-2">
          {navItems.map((item) => {
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition-all duration-150 group relative
                  ${isActive
                    ? "bg-blue-500/10 text-blue-400"
                    : "text-[hsl(215,15%,55%)] hover:bg-[hsl(220,15%,12%)] hover:text-[hsl(210,20%,85%)]"
                  }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-400 rounded-r" />
                )}
                <Icon name={item.icon} size={18} className="flex-shrink-0" />
                {sidebarOpen && (
                  <span className="text-sm font-medium flex-1 text-left animate-fade-in">{item.label}</span>
                )}
                {sidebarOpen && item.badge && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded mono
                    ${isActive ? "bg-blue-500/20 text-blue-400" : "bg-[hsl(220,15%,14%)] text-muted-foreground"}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-border space-y-1">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded text-muted-foreground hover:text-foreground hover:bg-[hsl(220,15%,12%)] transition-all duration-150"
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
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/50 backdrop-blur-sm flex-shrink-0">
          <div>
            <h1 className="text-base font-semibold text-foreground">{currentSection?.label}</h1>
            <p className="text-xs text-muted-foreground mono">
              {new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border bg-muted/50">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 status-dot-active" />
              <span className="text-xs text-muted-foreground mono">Система онлайн</span>
            </div>
            <button className="relative p-2 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-all">
              <Icon name="Bell" size={16} />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-red-500" />
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          <div className="animate-slide-up">
            {activeSection === "bots" && <BotsSection />}
            {activeSection === "stats" && <StatsSection />}
            {activeSection === "notifications" && <NotificationsSection />}
            {activeSection === "settings" && <SettingsSection />}
          </div>
        </main>
      </div>
    </div>
  );
}
