UPDATE t_p16564901_site_launch_bot.orders 
SET status = 'new', 
    active_queue_driver_chat_id = NULL,
    payment_id = NULL,
    payment_url = NULL,
    driver_chat_id = NULL,
    driver_username = NULL,
    driver_name = NULL
WHERE id = '148b711a-4a5d-416b-80cd-23e80e817c10';

UPDATE t_p16564901_site_launch_bot.order_queue 
SET status = 'expired'
WHERE order_id = '148b711a-4a5d-416b-80cd-23e80e817c10' AND status != 'expired';
