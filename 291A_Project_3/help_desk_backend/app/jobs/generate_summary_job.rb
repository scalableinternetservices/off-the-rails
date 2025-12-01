# app/jobs/generate_summary_job.rb
class GenerateSummaryJob < ApplicationJob
  queue_as :default

  def perform(conversation_id)
    conversation = Conversation.find_by(id: conversation_id)
    return unless conversation

    llm_service = LlmService.new
    summary = llm_service.generate_conversation_summary(conversation)

    if summary.present? && conversation.respond_to?(:summary=)
      conversation.update(summary: summary)
    end
  rescue StandardError => e
    Rails.logger.error("Generate summary failed for conversation #{conversation_id}: #{e.message}")
  end
end