class Item < ApplicationRecord
    belongs_to :user
    belongs_to :order, optional: true
    has_many :ratings, dependent: :destroy

    validates :price, presence: true, numericality: { greater_than_or_equal_to: 0, message: "must be a non-negative number" }
    validates :name, presence: true, length: {minimum: 3, maximum: 50}
    validates :condition, presence: true
    validates :description, length: {maximum: 500}
    # Validate price is present, is a number, and is non-negative
  
end
