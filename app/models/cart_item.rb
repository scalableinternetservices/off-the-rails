class CartItem < ApplicationRecord
  belongs_to :cart
  belongs_to :item

  validates :item_id, uniqueness: { scope: :cart_id, message: "is already in your cart" }
end
