Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "health", to: "application#health"
  get "up" => "rails/health#show", as: :rails_health_check

  # Defines the root path route ("/")
  # root "posts#index"

  # Simple health endpoint used by load balancers and uptime checks
  get '/health', to: 'health#index'

  scope :expert do
    get "queue", to: "expert#queue"
    get "profile", to: "expert#profile"
    put "profile", to: "expert#update_profile"
    get "assignments/history", to: "expert#assignments_history"
    post "conversations/:conversation_id/claim", to: "expert#claim"
    post "conversations/:conversation_id/unclaim", to: "expert#unclaim"
  end

   # Polling/Update endpoints
  namespace :api do
    get "conversations/updates", to: "updates#conversations"  
    get "messages/updates", to: "updates#messages"
    get "expert-queue/updates", to: "updates#expert_queue"
  end


  scope :auth do
    post "register", to: "auth#register"
    post "login", to: "auth#login"
    post "logout", to: "auth#logout"
    post "refresh", to: "auth#refresh"
    get  "me", to: "auth#me"
  end

  resources :conversations, only:[:index, :show, :create] do
    resources :messages, only:[:index]
  end

  resources :messages, only:[:create] do
    member do
      put "read", to: "messages#mark_read"
    end
  end


  root to: proc { [200, {}, ['{"status":"ok"}']] }

end
