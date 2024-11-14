class User < ApplicationRecord
    has_many :items, dependent: :destroy
    has_many :orders, dependent: :destroy
    has_many :reviews, dependent: :destroy

    validates :name, presence: true, uniqueness: true
end
