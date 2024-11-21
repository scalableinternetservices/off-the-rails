class OrdersController < ApplicationController
    def index
      @orders = Order.where(:user_id => current_user.id)
    end

    def show
        @order = Order.find(params[:id])
        if @order.user_id != current_user.id
            redirect_to root_path
        end
    end
    
    def new
        @order = Order.new
        @item = Item.find(params[:item_id])  # If you want to initialize an order with an item
        puts "===NEW ORDER==="
    end

    def create
        @cart = current_user.cart
        @order = Order.new(status: "PLACED", user_id: current_user.id)
    
        @cart.cart_items.each do |cart_item|
          @order.items << cart_item.item
        end
    
        if @order.save
          # Clear the cart after successful checkout
          @cart.cart_items.destroy_all
          redirect_to @order, notice: 'Order placed successfully!'
        else
          redirect_to cart_path(@cart), alert: 'Order could not be placed. Please try again.'
        end
    end


    
end
