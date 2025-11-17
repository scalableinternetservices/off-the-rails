class ConversationSerializer
  def self.for_user(conversation, viewer_id:)
    questioner = conversation.initiator
    assigned_expert = conversation.assigned_expert

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
      ).where.not(sender_id: viewer_id).count
    }
  end
end
