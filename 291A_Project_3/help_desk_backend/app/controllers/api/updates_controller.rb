module Api
  class UpdatesController < ApplicationController

    # GET /api/conversations/updates?userId=<id>&since=<timestamp>
    def conversations
      since = params[:since].present? ? Time.parse(params[:since]) : 1.hour.ago

      # Authenticate via JWT token or session
      current_user = current_user_from_auth
      return render json: { error: 'Unauthorized' }, status: :unauthorized unless current_user

      # Use authenticated user's ID, not the parameter
      user_id = current_user.id

      # Get conversations where user is initiator OR assigned expert
      conversations = Conversation.where(
        "initiator_id = ? OR assigned_expert_id = ?",
        user_id,
        user_id
      ).where("updated_at >= ?", since)

      # Build response with unreadCount for each conversation
      response_data = conversations.map do |conv|
        ConversationSerializer.for_user(conv, viewer_id: user_id)
      end

      render json: response_data, status: :ok
    end

    # GET /api/messages/updates?userId=<id>&since=<timestamp>
    def messages
      since = params[:since].present? ? Time.parse(params[:since]) : 1.hour.ago

      # Authenticate via JWT token or session
      current_user = current_user_from_auth
      return render json: { error: 'Unauthorized' }, status: :unauthorized unless current_user

      # Use authenticated user's ID
      user_id = current_user.id

      # Get conversations where user is involved
      user_conversations = Conversation.where(
        "initiator_id = ? OR assigned_expert_id = ?",
        user_id,
        user_id
      ).pluck(:id)

      # Get messages in those conversations since timestamp
      messages_data = Message.where(
        conversation_id: user_conversations
      ).where("created_at >= ?", since).map do |msg|
        sender = User.find(msg.sender_id)
        {
          id: msg.id.to_s,
          conversationId: msg.conversation_id.to_s,
          senderId: msg.sender_id.to_s,
          senderUsername: sender.username,
          senderRole: msg.sender_role,
          content: msg.content,
          timestamp: msg.created_at.iso8601,
          isRead: msg.is_read
        }
      end

      render json: messages_data, status: :ok
    end

    # GET /api/expert-queue/updates?expertId=<id>&since=<timestamp>
    def expert_queue
      since = params[:since].present? ? Time.parse(params[:since]) : 1.hour.ago

      # Authenticate via JWT token or session
      current_user = current_user_from_auth
      return render json: { error: 'Unauthorized' }, status: :unauthorized unless current_user

      # Use authenticated user's ID
      expert_id = current_user.id

      # Get waiting conversations (no assigned expert)
      waiting_conversations = Conversation.where(status: 'waiting')
                                          .where("updated_at >= ?", since)

      # Get assigned conversations for this expert (status = 'active' and assigned to this expert)
      assigned_conversations = Conversation.where(
        status: 'active',
        assigned_expert_id: expert_id
      ).where("updated_at >= ?", since)

      # Build response
      waiting_data = waiting_conversations.map { |conv| build_conversation_response(conv, expert_id) }
      assigned_data = assigned_conversations.map { |conv| build_conversation_response(conv, expert_id) }

      response_data = {
        waitingConversations: waiting_data,
        assignedConversations: assigned_data
      }

      render json: response_data, status: :ok
    end

    private

    def build_conversation_response(conv, expert_id)
      ConversationSerializer.for_user(conv, viewer_id: expert_id)
    end
  end
end
