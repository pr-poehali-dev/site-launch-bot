CREATE TABLE IF NOT EXISTS t_p16564901_site_launch_bot.subscriptions (
    id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    driver_chat_id bigint NOT NULL,
    driver_name varchar(255) NULL,
    driver_username varchar(255) NULL,
    plan varchar(20) NOT NULL, -- '1m', '6m', '12m'
    amount numeric(10,2) NOT NULL,
    status varchar(30) NOT NULL DEFAULT 'pending', -- pending, active, expired
    payment_id varchar(255) NULL,
    payment_url text NULL,
    started_at timestamp with time zone NULL,
    expires_at timestamp with time zone NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);