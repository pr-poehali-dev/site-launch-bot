ALTER TABLE t_p16564901_site_launch_bot.orders
  ADD COLUMN IF NOT EXISTS driver_chat_id bigint NULL,
  ADD COLUMN IF NOT EXISTS driver_username varchar(255) NULL,
  ADD COLUMN IF NOT EXISTS driver_name varchar(255) NULL;