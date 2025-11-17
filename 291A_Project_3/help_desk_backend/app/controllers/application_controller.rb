class ApplicationController < ActionController::API
  private

  def current_user_from_token
    token = request.headers['Authorization']&.split(' ')&.last
    return nil if token.blank?

    decoded = JwtService.decode(token)
    return nil unless decoded

    user = User.find_by(id: decoded[:user_id])
    return nil unless user

    if user.jwt_revoked_at.present?
      issued_at = decoded[:iat]
      return nil if issued_at.nil? || issued_at < user.jwt_revoked_at.to_i
    end

    user
  rescue ActiveRecord::RecordNotFound
    nil
  end

  def current_user_from_session
    return nil unless session[:user_id]

    User.find_by(id: session[:user_id])
  end

  def current_user_from_auth
    current_user_from_token || current_user_from_session
  end

  def authenticate_user_with_token_or_session!
    @current_user = current_user_from_auth
    render json: { error: 'Unauthorized' }, status: :unauthorized unless @current_user
  end
end
