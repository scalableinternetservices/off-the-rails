class ApplicationController < ActionController::Base
  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  helper_method :current_user, :log_in, :log_out, :check_logged_in
  rescue_from ActiveRecord::RecordNotFound, with: :render_not_found
  helper_method :current_cart

  def current_cart
    current_user.cart || current_user.create_cart
  end

  private

  def render_not_found
    render file: "#{Rails.root}/public/404.html", status: :not_found
  end
  
  def check_logged_in
      unless !current_user.nil?
        #store_location
        puts "=== user needs to log in ==="
        redirect_to login_url
      end
  end

  def log_in(user)
    session[:user_id] = user.id
  end

  def current_user
    @current_user ||= User.find_by(id: session[:user_id]) if session[:user_id]
  end

  def log_out
    session.delete(:user_id)
    @current_user = nil
  end
end