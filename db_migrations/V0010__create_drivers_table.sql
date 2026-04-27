CREATE TABLE IF NOT EXISTS t_p16564901_site_launch_bot.drivers (
    chat_id bigint NOT NULL PRIMARY KEY,
    username varchar(255),
    name varchar(255),
    first_seen_at timestamptz NOT NULL DEFAULT now()
);