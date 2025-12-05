# app/jobs/generate_summary_job.rb
class GenerateSummaryJob < ApplicationJob
  queue_as :default

  def perform(conversation_id)
    conversation = Conversation.find_by(id: conversation_id)
    return unless conversation

    # Only generate if there are 1+ messages
    message_count = conversation.messages.count
    if message_count < 1
      Rails.logger.info("Skipping summary generation for conversation #{conversation_id}: only #{message_count} message(s)")
      return
    end

    Rails.logger.info("Generating summary for conversation #{conversation_id} (#{message_count} messages)")

    llm_service = LlmService.new
    summary = llm_service.generate_conversation_summary(conversation)

    Rails.logger.info("Summary generated: #{summary}")

    if summary.present?
      conversation.update(
        summary: summary,
        message_count_at_summary: message_count
      )
      Rails.logger.info("Summary generated successfully for conversation #{conversation_id}")
    else
      Rails.logger.warn("Summary generation returned empty for conversation #{conversation_id}")
    end
  rescue StandardError => e
    Rails.logger.error("Generate summary failed for conversation #{conversation_id}: #{e.class} - #{e.message}")
    Rails.logger.error(e.backtrace.join("\n"))
  end
end