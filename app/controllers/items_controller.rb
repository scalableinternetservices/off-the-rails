class ItemsController < ApplicationController
  def index
    @items = Item.all
  end

  def show
    @item = Item.find(params[:id])
  end

  def new
    @item = Item.new
  end

  def create
    @item = Item.new(name: "...", price: 0, condition: "NEW", description: "...")

    if @item.save
      redirect_to @item
    else
      render :new, status: :unprocessable_entity
    end
  end
end
