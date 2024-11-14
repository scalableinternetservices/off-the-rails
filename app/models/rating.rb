class Rating < ApplicationRecord
  belongs_to :user
  belongs_to :item

  validates :rating, presence: true, numericality: {greater_than_or_equal_to: 1, less_than_or_equal_to: 5} 
  validates :review, presence: true, length: {minimum: 5, maximum: 500}
end
