class HealthController < ApplicationController
def index
  render json: {
    status: 'ok',
    timestamp: Time.now.iso8601
  }, status: :ok
  end 
end
