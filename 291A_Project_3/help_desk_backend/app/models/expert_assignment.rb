class ExpertAssignment < ApplicationRecord
  belongs_to :conversation
  belongs_to :expert, class_name: 'User', foreign_key: 'expert_id'
  STATUS_VALUES = %w[active resolved].freeze

  validates :conversation, :expert, :status, :assigned_at, presence: true
  validates :status, inclusion: {in: STATUS_VALUES}
  validates :rating,numericality: {only_integer: true, in: 1..5},allow_nil: true
  validate :req_time_for_resolve
  validate :rate_after_resolve

  before_validation :defaultstat, on: :create
  before_validation :assigned_at_time, on: :create

  private

  def defaultstat
    self.status ||= 'active'
  end

  def assigned_at_time
    self.assigned_at ||= Time.current
  end

  def req_time_for_resolve
    if status == 'resolved' && resolved_at.blank?
      errors.add(:resolved_at, 'time not set for resolved')
    end
  end

  def rate_after_resolve
    if rating.present? && status != 'resolved'
      errors.add(:rating, 'there shouldnt be a rating without being resolved')
    end
  end
end
