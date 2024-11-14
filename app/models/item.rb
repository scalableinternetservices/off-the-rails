class Item < ApplicationRecord
    belongs_to :user
    belongs_to :order, optional: true
    has_many :reviews, dependent: :destroy

    validates :price, presence: true
    validates :name, presence: true, length: {minimum: 3, maximum: 50}
    validates :condition, presence: true
    validates :description, length: {maximum: 500}
end
