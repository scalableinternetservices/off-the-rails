class Item < ApplicationRecord
    belongs_to :user
    has_one :order 

    validates :price, presence: true
    validates :name, presence: true, length: {minimum: 5, maximum: 50}
    validates :condition, presence: true
end
