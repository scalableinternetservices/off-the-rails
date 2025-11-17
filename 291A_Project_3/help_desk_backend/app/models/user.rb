class User < ApplicationRecord
  has_secure_password #needed this
  has_one :expert_profile, dependent: :destroy
  has_many :initiated_conversations, class_name: 'Conversation', foreign_key: 'initiator_id'
  has_many :assigned_conversations, class_name: 'Conversation', foreign_key: 'assigned_expert_id'
  validates :username, presence: true, uniqueness: true

  after_create :create_expert_profile

  private

  def create_expert_profile
    ExpertProfile.create(user: self)
  rescue ActiveRecord::RecordNotUnique
    # Profile already exists, no action needed
  end
end
