class RatingsController < ApplicationController
    def new 
        @rating = Rating.new
        @item = Item.find(params[:item_id])
    end

    def create 
      @rating = Rating.new(rating_params)
      @rating.user_id = current_user.id
      @rating.item_id = params[:item_id]
  
      if @rating.save
        redirect_to orders_path, notice: 'Rating submitted successfully.'
      else
        flash.now[:alert] = 'Failed to submit rating. Please try again.'
        render :new, status: :unprocessable_entity
      end
    end

    def show 
      @ratings = Rating.where(user_id: current_user.id)
    end

    private
  
    def check_purchase
      unless current_user.orders.joins(:items).where(items: { id: @item.id }).exists?
        redirect_to root_path, alert: 'You can only rate items you have purchased.'
      end
    end
  
    def rating_params
      params.require(:rating).permit(:rating, :review)
    end

end