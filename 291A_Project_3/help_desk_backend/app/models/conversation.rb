class Conversation < ApplicationRecord
  belongs_to :initiator, class_name: 'User', foreign_key: 'initiator_id'
  belongs_to :assigned_expert, class_name: 'User', foreign_key: 'assigned_expert_id', optional: true
  has_many :messages, dependent: :destroy
  has_many :expert_assignments, dependent: :destroy
  STATUS_VALUES = %w[waiting active resolved].freeze

  validates :title, presence: true, length: { maximum: 255 }
  validates :status, presence: true, inclusion: {in: STATUS_VALUES}
  validates :initiator, presence: true
  before_validation :defaultstat, on: :create
  private

  def defaultstat
    self.status ||= 'waiting'
  end
  
  
end
