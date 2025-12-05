# Redis configuration
redis_config = {
  url: ENV.fetch('REDIS_URL', 'redis://localhost:6379/0'),
  network_timeout: 5
}

# Configure Sidekiq server (the worker process)
Sidekiq.configure_server do |config|
  config.redis = redis_config
end

# Configure Sidekiq client (the Rails app enqueueing jobs)
Sidekiq.configure_client do |config|
  config.redis = redis_config
end