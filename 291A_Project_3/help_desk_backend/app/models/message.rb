class Message < ApplicationRecord
  belongs_to :conversation
  belongs_to :sender, class_name: 'User', foreign_key: 'sender_id'

  validates :content, presence: true
  validates :conversation, :sender, presence: true
  validates :sender_role, inclusion: {in: %w[initiator expert]}
end
