CREATE TABLE IF NOT EXISTS t_p16564901_site_launch_bot.order_queue (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL,
    driver_chat_id bigint NOT NULL,
    driver_username varchar(255) NOT NULL DEFAULT '',
    driver_name varchar(255) NOT NULL DEFAULT '',
    position integer NOT NULL,
    status varchar(50) NOT NULL DEFAULT 'waiting',
    payment_id varchar(255),
    payment_url text,
    payment_expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_order_queue_order_id ON t_p16564901_site_launch_bot.order_queue(order_id);
CREATE INDEX IF NOT EXISTS idx_order_queue_driver ON t_p16564901_site_launch_bot.order_queue(driver_chat_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_order_queue_unique ON t_p16564901_site_launch_bot.order_queue(order_id, driver_chat_id);

ALTER TABLE t_p16564901_site_launch_bot.orders ADD COLUMN IF NOT EXISTS tg_group_message_id bigint;
ALTER TABLE t_p16564901_site_launch_bot.orders ADD COLUMN IF NOT EXISTS active_queue_driver_chat_id bigint;
