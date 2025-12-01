# class ConversationSerializer
#   def self.for_user(conversation, viewer_id:)
#     questioner = conversation.initiator
#     assigned_expert = conversation.assigned_expert

#     {
#       id: conversation.id.to_s,
#       title: conversation.title,
#       status: conversation.status,
#       questionerId: conversation.initiator_id.to_s,
#       questionerUsername: questioner&.username,
#       assignedExpertId: assigned_expert&.id&.to_s,
#       assignedExpertUsername: assigned_expert&.username,
#       createdAt: conversation.created_at&.iso8601,
#       updatedAt: conversation.updated_at&.iso8601,
#       lastMessageAt: conversation.last_message_at&.iso8601,
#       unreadCount: Message.where(
#         conversation_id: conversation.id,
#         is_read: false
#       ).where.not(sender_id: viewer_id).count
#     }
#   end
# end

# app/serializers/conversation_serializer.rb
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
      summary: summary
    }
  end

  private

  def self.get_or_generate_summary(conversation)
    # Check if we have a cached summary
    if conversation.respond_to?(:summary) && conversation.summary.present?
      return conversation.summary
    end

    # Generate summary asynchronously if needed
    if conversation.messages.any?
      GenerateSummaryJob.perform_later(conversation.id)
      return "Generating summary..."
    end

    "No messages yet"
  end
end