class ItemsController < ApplicationController
  before_action :check_logged_in 
  
  def index
    case params[:order_by]
    when 'created_at_desc'
      @items = Item.where(order_id: nil).order(created_at: :desc)  # Sort by date listed, newest first
    when 'created_at_asc'
      @items = Item.where(order_id: nil).order(:created_at)  # Sort by date listed, newest first
    when 'price_asc'
      @items = Item.where(order_id: nil).order(:price)  # Sort by price from lowest to highest
    when 'price_desc'
      @items = Item.where(order_id: nil).order(price: :desc)  # Sort by price from highest to lowest
    else
      @items = Item.where(order_id: nil).order(created_at: :desc)
    end
    
    if params[:min_price].present? && params[:max_price].present?
      @items = @items.where(price: params[:min_price]..params[:max_price])
    elsif params[:min_price].present?
      @items = @items.where("price >= ?", params[:min_price])
    elsif params[:max_price].present?
      @items = @items.where("price <= ?", params[:max_price])
    end
      # Condition filter, ignore "All"
    if params[:condition].present? && params[:condition] != 'ALL'
      @items = @items.where(condition: params[:condition])
    end

    if params[:query].present?
      @items = @items.where("name ILIKE :query OR description ILIKE :query", query: "%#{params[:query]}%")
    end

  end

  def show
    @item = Item.find(params[:id])
    @seller_items = Item.where(user_id: @item.user)
    @ratings = Rating.where(item_id: @seller_items.ids)
    @sum = 0
    @ratings.each { |x| @sum += x.rating}
    @seller_rating = @sum.to_f / @ratings.length()
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

  def update
    @item = Item.find(params[:id])

    if @item.update(item_params)
      redirect_to @item
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def edit
    @item = Item.find(params[:id]) 
  end

  def destroy
    @item = Item.find(params[:id])
    result = @item.destroy!
    puts result

    redirect_to root_path, status: :see_other
  end

  def user_listings
    @items = current_user.items.order(created_at: :desc)
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
