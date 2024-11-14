class User < ApplicationRecord
    has_many :items, dependent: :destroy
    has_many :orders, dependent: :destroy
end
