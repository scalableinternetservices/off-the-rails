class ItemsController < ApplicationController
  before_action :check_logged_in 
  
  def index
    @items = Item.order(created_at: :desc)
  end

  def show
    @item = Item.find(params[:id])
  end

  def new
    @item = Item.new
  end

  def create
    @item = Item.new(item_params)
    @item.user_id = current_user.id

    if @item.save
      #redirect_to @item
      redirect_to root_path
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @item = Item.find(params[:id])
  end

  private
    def item_params
      params.require(:item).permit(:name, :description, :price, :condition)
    end
  
    private

    def render_not_found
      render file: "#{Rails.root}/public/404.html", status: :not_found
    end
end
