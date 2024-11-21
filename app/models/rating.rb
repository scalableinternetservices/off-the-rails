class Rating < ApplicationRecord
  belongs_to :user
  belongs_to :item

  validates :rating, presence: true, numericality: {greater_than_or_equal_to: 1, less_than_or_equal_to: 5} 
  validates :review, presence: true, length: {minimum: 5, maximum: 500}
  validate :user_must_have_purchased_item

  private

  def user_must_have_purchased_item
    unless user.orders.joins(:items).where(items: { id: item.id }).exists?
      errors.add(:base, 'You can only rate items you have purchased.')
    end
  end
end
