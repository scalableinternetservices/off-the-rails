# app/jobs/auto_assign_expert_job.rb
class AutoAssignExpertJob < ApplicationJob
  queue_as :default

  def perform(conversation_id)
    conversation = Conversation.find_by(id: conversation_id)

    return unless conversation
    return if conversation.assigned_expert_id.present?

    llm_service = LlmService.new
    expert_id = llm_service.assign_expert_to_conversation(conversation)

    if expert_id
      Conversation.transaction do
        conversation.lock!
        # Double-check it hasn't been assigned in the meantime
        return if conversation.assigned_expert_id.present?
        
        expert = User.find_by(id: expert_id)
        return unless expert

        conversation.update!(
          assigned_expert_id: expert_id,
          status: 'active'
        )

        conversation.expert_assignments.create!(
          expert: expert,
          status: 'active',
          assigned_at: Time.current
        )
      end
    end
  rescue StandardError => e
    Rails.logger.error("Auto-assign expert failed for conversation #{conversation_id}: #{e.message}")
  end
end