Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  root "items#index"

  get '/login', to: 'sessions#new'
  post '/login', to: 'sessions#create'
  get '/logout', to: 'sessions#destroy'

  get '/profile', to: 'sessions#profile'
  resources :users
  resources :orders
  resources :carts, only: [:show] do
    post 'add_item/:item_id', to: 'carts#add_item', as: 'add_item'
    delete 'remove_item/:item_id', to: 'carts#remove_item', as: 'remove_item'
  end
  resources :items do
    collection do
      get 'user_listings'
    end
    resources :ratings, only: [:new, :create]
  end

  get '*path', to: 'items#index'
  get "up" => "rails/health#show", as: :rails_health_check

  # Defines the root path route ("/")
  # root "posts#index"
end
