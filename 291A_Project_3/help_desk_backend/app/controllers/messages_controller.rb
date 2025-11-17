class MessagesController < ApplicationController
  before_action :authenticate_user_with_token_or_session!
  before_action :set_conversation_from_params, only: [:index, :create]
  before_action :authorize_conversation_access!, only: [:index, :create]
  before_action :set_message, only: [:mark_read]
  before_action :authorize_message_access!, only: [:mark_read]

  def index
    messages = @conversation.messages.order(:created_at)
    render json: messages.map { |msg| message_json(msg) }, status: :ok
  end

  def create
    content = extracted_message_content
    return render json: { errors: ['Content can\'t be blank'] }, status: :unprocessable_entity if content.blank?

    message = @conversation.messages.build(
      sender: @current_user,
      sender_role: sender_role_for(@conversation),
      content: content,
      is_read: false,
      read_at: nil
    )

    if message.save
      @conversation.update(last_message_at: message.created_at)
      render json: message_json(message), status: :created
    else
      render json: { errors: message.errors.full_messages }, status: :unprocessable_entity
    end
  end

  def mark_read
    if @message.sender_id == @current_user.id
      return render json: { error: 'Cannot mark your own messages as read' }, status: :forbidden
    end

    if @message.update(is_read: true, read_at: Time.current)
      render json: { success: true }, status: :ok
    else
      render json: { error: 'Unable to mark message as read' }, status: :unprocessable_entity
    end
  end

  private

  def set_conversation_from_params
    conversation_id = params[:conversation_id] ||
                      params[:conversationId] ||
                      params.dig(:message, :conversation_id) ||
                      params.dig(:message, :conversationId)
    @conversation = Conversation.find_by(id: conversation_id)
    unless @conversation
      render json: { error: 'Conversation not found' }, status: :not_found
      return
    end
  end

  def authorize_conversation_access!
    return if @conversation.nil?

    unless conversation_participant?(@conversation)
      render json: { error: 'Unauthorized' }, status: :forbidden
      return
    end
  end

  def set_message
    @message = Message.find_by(id: params[:id])
    unless @message
      render json: { error: 'Message not found' }, status: :not_found
      return
    end
  end

  def authorize_message_access!
    unless conversation_participant?(@message.conversation)
      render json: { error: 'Unauthorized' }, status: :forbidden
      return
    end
  end

  def conversation_participant?(conversation)
    conversation.initiator_id == @current_user.id || conversation.assigned_expert_id == @current_user.id
  end

  def sender_role_for(conversation)
    conversation.initiator_id == @current_user.id ? 'initiator' : 'expert'
  end

  def extracted_message_content
    params[:content] ||
      params[:message]&.[](:content)
  end

  def message_json(message)
    {
      id: message.id.to_s,
      conversationId: message.conversation_id.to_s,
      senderId: message.sender_id.to_s,
      senderUsername: message.sender.username,
      senderRole: message.sender_role,
      content: message.content,
      timestamp: message.created_at.iso8601,
      isRead: message.is_read
    }
  end
end
