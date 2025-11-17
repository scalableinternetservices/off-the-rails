class JwtService
  SECRET_KEY = Rails.application.credentials.secret_key_base || 'dev_key'

  def self.encode(user, exp = 24.hours.from_now)
    payload = {
      user_id: user.id,
      iat: Time.current.to_i,
      exp: exp.to_i
    }
    JWT.encode(payload, SECRET_KEY, 'HS256')
  end

  def self.decode(token)
    begin
      decoded = JWT.decode(token, SECRET_KEY, true, { algorithm: 'HS256' }).first
      { user_id: decoded['user_id'], exp: decoded['exp'], iat: decoded['iat'] }
    rescue JWT::DecodeError
      nil
    end
  end
end
