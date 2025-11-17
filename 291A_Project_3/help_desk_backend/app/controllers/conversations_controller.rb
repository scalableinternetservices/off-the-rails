class ConversationsController < ApplicationController
  before_action :authenticate_user!
  before_action :set_conversation, only: [:show]

  def index
    @conversations = @current_user.initiated_conversations.or(@current_user.assigned_conversations).order(created_at: :desc)
    render json: @conversations.map { |c| ConversationSerializer.for_user(c, viewer_id: @current_user.id) }, status: :ok
  end

  def show
    if @conversation
      # Verify user is part of this conversation
      unless @conversation.initiator_id == @current_user.id || @conversation.assigned_expert_id == @current_user.id
        return render json: { error: 'Not found' }, status: :not_found
      end
      render json: ConversationSerializer.for_user(@conversation, viewer_id: @current_user.id), status: :ok
    else
      render json: { error: 'Conversation not found' }, status: :not_found
    end
  end

  def create
    @conversation = Conversation.new(
      title: params[:title],
      initiator: @current_user,
      status: 'waiting'
    )
    if @conversation.save
      render json: ConversationSerializer.for_user(@conversation, viewer_id: @current_user.id), status: :created
    else
      render json: { errors: @conversation.errors.full_messages }, status: :unprocessable_entity
    end
  end

  private

  def authenticate_user!
    authenticate_user_with_token_or_session!
  end

  def set_conversation
    @conversation = Conversation.find_by(id: params[:id])
  end

  def conversation_params
    params.require(:conversation).permit(:title, :status, :initiator_id, :assigned_expert_id)
  end

end
