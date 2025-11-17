class ExpertController < ApplicationController
  before_action :require_authenticated_user

  # GET /expert/profile
  def profile
    expert_profile = ExpertProfile.find_by(user_id: @current_user.id)
    return render json: { error: 'Expert profile not found' }, status: :not_found unless expert_profile

    render json: {
      id: expert_profile.id.to_s,
      userId: expert_profile.user_id.to_s,
      bio: expert_profile.bio,
      knowledgeBaseLinks: expert_profile.knowledge_base_links || [],
      createdAt: expert_profile.created_at.iso8601,
      updatedAt: expert_profile.updated_at.iso8601
    }, status: :ok
  end

  # PUT /expert/profile
  def update_profile
    expert_profile = ExpertProfile.find_by(user_id: @current_user.id)
    return render json: { error: 'Expert profile not found' }, status: :not_found unless expert_profile

    if expert_profile.update(bio: params[:bio], knowledge_base_links: params[:knowledgeBaseLinks])
      render json: {
        id: expert_profile.id.to_s,
        userId: expert_profile.user_id.to_s,
        bio: expert_profile.bio,
        knowledgeBaseLinks: expert_profile.knowledge_base_links || [],
        createdAt: expert_profile.created_at.iso8601,
        updatedAt: expert_profile.updated_at.iso8601
      }, status: :ok
    else
      render json: { errors: expert_profile.errors.full_messages }, status: :unprocessable_entity
    end
  end

  # GET /expert/queue
  def queue
    # Get waiting conversations (no assigned expert)
    waiting_conversations = Conversation.where(status: 'waiting')
                                        .order(created_at: :desc)
                                        .map { |conv| ConversationSerializer.for_user(conv, viewer_id: @current_user.id) }

    # Get assigned conversations for this expert
    assigned_conversations = Conversation.where(assigned_expert_id: @current_user.id, status: 'active')
                                         .order(created_at: :desc)
                                         .map { |conv| ConversationSerializer.for_user(conv, viewer_id: @current_user.id) }

    render json: {
      waitingConversations: waiting_conversations,
      assignedConversations: assigned_conversations
    }, status: :ok
  end

  # POST /expert/conversations/:conversation_id/claim
  def claim
    conversation = Conversation.find_by(id: params[:conversation_id])
    return render json: { error: 'Conversation not found' }, status: :not_found unless conversation

    Conversation.transaction do
      conversation.lock!
      if conversation.assigned_expert_id.present?
        return render json: { error: 'Conversation is already assigned to an expert' }, status: :unprocessable_entity
      end

      conversation.update!(assigned_expert_id: @current_user.id, status: 'active')
      conversation.expert_assignments.create!(
        expert: @current_user,
        status: 'active',
        assigned_at: Time.current
      )
    end

    render json: { success: true }, status: :ok
  rescue ActiveRecord::RecordInvalid => e
    render json: { errors: e.record.errors.full_messages }, status: :unprocessable_entity
  end

  # POST /expert/conversations/:conversation_id/unclaim
  def unclaim
    conversation = Conversation.find_by(id: params[:conversation_id])
    return render json: { error: 'Conversation not found' }, status: :not_found unless conversation

    if conversation.assigned_expert_id != @current_user.id
      return render json: { error: 'You are not assigned to this conversation' }, status: :forbidden
    end

    Conversation.transaction do
      conversation.lock!
      if conversation.assigned_expert_id != @current_user.id
        return render json: { error: 'You are not assigned to this conversation' }, status: :forbidden
      end

      conversation.update!(assigned_expert_id: nil, status: 'waiting')

      latest_assignment = conversation.expert_assignments.where(expert_id: @current_user.id).order(assigned_at: :desc).first
      latest_assignment&.update!(status: 'resolved', resolved_at: Time.current)
    end

    render json: { success: true }, status: :ok
  rescue ActiveRecord::RecordInvalid => e
    render json: { errors: e.record.errors.full_messages }, status: :unprocessable_entity
  end

  # GET /expert/assignments/history
  def assignments_history
    assignments = ExpertAssignment.where(expert_id: @current_user.id)
                                  .order(assigned_at: :desc)
                                  .map do |assignment|
      {
        id: assignment.id.to_s,
        conversationId: assignment.conversation_id.to_s,
        expertId: assignment.expert_id.to_s,
        status: assignment.status,
        assignedAt: assignment.assigned_at.iso8601,
        resolvedAt: assignment.resolved_at&.iso8601,
        rating: assignment.rating
      }
    end

    render json: assignments, status: :ok
  end

  private

  def require_authenticated_user
    @current_user = current_user_from_auth
    render json: { error: 'Unauthorized' }, status: :unauthorized unless @current_user
  end
end
