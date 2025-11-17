class ExpertProfile < ApplicationRecord
  belongs_to :user
  validates :user, presence: true, uniqueness: true
  def self.create!(attributes = nil, &block)
    # Handle duplicate user_id gracefully - return existing profile if it exists
    if attributes.is_a?(Hash) && attributes[:user_id]
      existing = find_by(user_id: attributes[:user_id])
      return existing if existing
    elsif attributes.is_a?(Hash) && attributes[:user]
      existing = find_by(user: attributes[:user])
      return existing if existing
    end
    super(attributes, &block)
  end
end
