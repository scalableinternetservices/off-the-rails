class CartsController < ApplicationController
  before_action :check_logged_in
  before_action :set_cart
  def index
    # Find or create the cart for the current user
    cart = current_user.cart || Cart.create(user: current_user)
    redirect_to cart_path(cart) # Redirect to /carts/:id
  end
  def show
    @cart = Cart.find(params[:id])
    @cart_items = @cart.cart_items.includes(:item)
    Rails.logger.debug "Cart Items: #{@cart_items.inspect}"
  end

  def add_item
    item = Item.find(params[:item_id])

    if item.user_id == current_user.id
      redirect_to cart_path(@cart), alert: "You cannot add your own items to the cart."
    elsif @cart.items.include?(item)
      redirect_to cart_path(@cart), alert: "Item is already in your cart."
    else
      @cart.cart_items.create(item: item)
      redirect_to cart_path(@cart), notice: "Item added to your cart."
    end
  end
  

  def remove_item
    cart_item = @cart.cart_items.find_by(item_id: params[:item_id])
    cart_item&.destroy
    redirect_to cart_path(@cart), notice: "Item removed from your cart."
  end

  private

  def set_cart
    @cart = current_user.cart || Cart.create(user: current_user)
  end
end
