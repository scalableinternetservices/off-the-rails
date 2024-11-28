class SessionsController < ApplicationController
    skip_forgery_protection
    def new
        #render new log in here
    end

    def profile
      @items = current_user.items.order(created_at: :desc)
    end
  
    def create
      puts params

      user = User.find_by(name: params[:name])
      user_params = {name: params[:name]}
      if user == nil
        user = User.create(user_params)
        puts "===CREATING USER==="
      else
        puts "===USER EXISTS==="
      end

      if user 
        log_in user
        @cart = current_cart
        #redirect_back_or user
        redirect_to root_path
      else
        render 'new'
      end
    end
  
    def destroy
      log_out
      redirect_to root_url
    end
end

private
    def user_params
        params.require(:user).permit(:name)
    end