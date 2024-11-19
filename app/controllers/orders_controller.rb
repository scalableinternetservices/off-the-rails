class OrdersController < ApplicationController
    def index
      @orders = Order.all
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
        @order = Order.new(status: "PLACED")
        @item = Item.find(params[:item_id])  # Retrieve item_id passed via the form

        @order.user_id = current_user.id
        @order.items << @item
        puts "===CREATING ORDER==="

        if @order.save
            # Optionally, associate item with the order here if needed
            redirect_to @order, notice: 'Order placed successfully!'
        else
            redirect_to root_path
        end
    end


    
end
