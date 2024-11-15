class UsersController < ApplicationController
    def show
        @user = User.find(params[:id])
      end
    
      def new
        @user = User.new
      end
    
      def create
        @user = User.new(user_params)
        if @user.save
          puts "===SAVING USER==="
          redirect_to root_path
        else
          puts "===USER NOT SAVED==="
          render 'new'
        end
      end
    
      private
    
      def user_params
        params.require(:user).permit(:name)
      end
end