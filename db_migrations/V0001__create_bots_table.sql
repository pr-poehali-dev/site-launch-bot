CREATE TABLE t_p16564901_site_launch_bot.bots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'stopped',
  version VARCHAR(50) NOT NULL DEFAULT 'v1.0.0',
  uptime VARCHAR(100) DEFAULT '—',
  requests INTEGER NOT NULL DEFAULT 0,
  cpu INTEGER NOT NULL DEFAULT 0,
  memory INTEGER NOT NULL DEFAULT 0,
  last_deploy VARCHAR(50) DEFAULT '—',
  environment VARCHAR(50) NOT NULL DEFAULT 'production',
  description TEXT DEFAULT '',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
