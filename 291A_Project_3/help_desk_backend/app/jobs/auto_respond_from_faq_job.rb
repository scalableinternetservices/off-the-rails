class AutoRespondFromFaqJob < ApplicationJob
  queue_as :default

  def perform(message_id)
    message = Message.find_by(id: message_id)
    Rails.logger.info("AutoRespondFromFaqJob started for message #{message_id}")
    return unless message


    conversation = message.conversation
    return unless conversation.assigned_expert_id.present?

    # Get expert profile
    expert_profile = ExpertProfile.find_by(user_id: conversation.assigned_expert_id)
    return unless expert_profile

    # Try to get FAQ response
    llm_service = LlmService.new
    faq_response = llm_service.check_faq_response(message.content, expert_profile)

    if faq_response.present?
      # Create auto-response message
      expert = User.find_by(id: conversation.assigned_expert_id)
      return unless expert

      auto_message = conversation.messages.create!(
        sender: expert,
        sender_role: 'expert',
        content: faq_response,
        is_read: false,
        read_at: nil
      )
      Rails.logger.info("Auto-responded to message #{message_id} from FAQ with message ID #{auto_message.id}")

      conversation.update(last_message_at: auto_message.created_at)
    end
  rescue StandardError => e
    Rails.logger.error("Auto-respond from FAQ failed for message #{message_id}: #{e.message}")
  end
end