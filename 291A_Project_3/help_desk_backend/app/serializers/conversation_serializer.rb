class ConversationSerializer
  def self.for_user(conversation, viewer_id:)
    questioner = conversation.initiator
    assigned_expert = conversation.assigned_expert

    # Get or generate summary
    summary = get_or_generate_summary(conversation)

    {
      id: conversation.id.to_s,
      title: conversation.title,
      status: conversation.status,
      questionerId: conversation.initiator_id.to_s,
      questionerUsername: questioner&.username,
      assignedExpertId: assigned_expert&.id&.to_s,
      assignedExpertUsername: assigned_expert&.username,
      createdAt: conversation.created_at&.iso8601,
      updatedAt: conversation.updated_at&.iso8601,
      lastMessageAt: conversation.last_message_at&.iso8601,
      unreadCount: Message.where(
        conversation_id: conversation.id,
        is_read: false
      ).where.not(sender_id: viewer_id).count,
      summary: summary,
      # message_count_at_summary: conversation.messages.count
    }
  end

  private

  ## NOTE Here is a refrence to summary generation logic for bullet point three
  def self.get_or_generate_summary(conversation)
    current_message_count = conversation.messages.count

    # Not enough messages yet
    if current_message_count < 1
      return "Not enough messages for summary"
    end

    # Check if we need to generate/regenerate
    needs_generation = should_generate_summary?(conversation, current_message_count)

    if needs_generation
      # Queue job to generate new summary
      GenerateSummaryJob.perform_later(conversation.id)
      
      # Return existing summary if available, otherwise placeholder
      return conversation.summary.presence || "Generating summary..."
    end

    # Return cached summary
    conversation.summary.presence || "Summary not available"
  end

  def self.should_generate_summary?(conversation, current_message_count)
    # No summary exists yet
    return true if conversation.summary.blank?

    # Check if there have been 5+ new messages since last summary
    messages_since_summary = current_message_count - (conversation.message_count_at_summary || 0)
    
    messages_since_summary >= 5
  end
end