export interface Order {
  id: string;
  from_city: string;
  to_city: string;
  pickup: string;
  dropoff: string;
  trip_date: string;
  trip_time: string;
  price: string;
  tariff: string;
  commission: string;
  driver_amount: string;
  phone: string;
  passengers: number;
  luggage: number;
  booster: boolean;
  child_seat: boolean;
  animal: boolean;
  comment: string;
  status: string;
  created_at: string;
  driver_chat_id?: number | null;
  driver_name?: string | null;
  driver_username?: string | null;
  payment_url?: string | null;
}

export const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  new:         { label: "Новая",            color: "text-blue-400",         bg: "bg-blue-500/10 border-blue-500/30" },
  on_sale:     { label: "На продаже",       color: "text-yellow-400",       bg: "bg-yellow-500/10 border-yellow-500/30" },
  in_progress: { label: "Выполняется",      color: "text-green-400",        bg: "bg-green-500/10 border-green-500/30" },
  closed:      { label: "Закрыт",           color: "text-orange-400",       bg: "bg-orange-500/10 border-orange-500/30" },
  done:        { label: "Завершен",         color: "text-muted-foreground", bg: "bg-muted/30 border-border" },
  cancelled:   { label: "Удалён",           color: "text-red-400",          bg: "bg-red-500/10 border-red-500/30" },
  no_driver:   { label: "Нет машин",        color: "text-orange-400",       bg: "bg-orange-500/10 border-orange-500/30" },
  accepted:    { label: "На продаже",       color: "text-yellow-400",       bg: "bg-yellow-500/10 border-yellow-500/30" },
};

export const STATUSES = ["new", "on_sale", "in_progress", "closed", "done"];