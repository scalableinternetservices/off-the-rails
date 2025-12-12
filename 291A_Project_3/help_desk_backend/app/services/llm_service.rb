# app/services/llm_service.rb
require 'open-uri'

class LlmService
  def initialize
    #define the bedrock client (claude-3-5-haiku-20241022-v1:0)
    @client = BedrockClient.new(
      model_id: "anthropic.claude-3-5-haiku-20241022-v1:0",
      region: ENV["AWS_REGION"] || "us-west-2"
    )
  end

  # Auto-assign conversation to best matching expert
  def assign_expert_to_conversation(conversation)
    # Get all expert profiles
    expert_profiles = ExpertProfile.includes(:user).all
    
    return nil if expert_profiles.empty?

    # Get first message if available
    first_message = conversation.messages.order(:created_at).first&.content || conversation.title
    
    
    # Build expert information for LLM
    experts_info = expert_profiles.map do |profile|
      {
        id: profile.user_id,
        username: profile.user.username,
        bio: profile.bio,
        knowledge_base: profile.knowledge_base_links&.join(", ")
      }
    end

    system_prompt = <<~PROMPT
      You are an expert assignment system. Your job is to match a user's question 
      with the most appropriate expert based on their bio and knowledge base.
      
      Return ONLY the expert ID (numeric) that best matches the question.
      Do not include any explanation, just the ID number. You cannot assign user as their own expert. 
    PROMPT

    user_prompt = <<~PROMPT
      Question/Topic: #{first_message}
      
      Available Experts:
      #{experts_info.map { |e| "ID: #{e[:id]}, Username: #{e[:username]}, Bio: #{e[:bio]}, Knowledge: #{e[:knowledge_base]}" }.join("\n")}
      
      Which expert ID is the best match?
    PROMPT

    response = @client.call(
      system_prompt: system_prompt,
      user_prompt: user_prompt,
      max_tokens: 50,
      temperature: 0.3
    )

    # Extract expert ID from response
    expert_id = response[:output_text].strip.to_i
    
    # Verify expert exists
    expert_profiles.find { |p| p.user_id == expert_id }&.user_id
  end

  
  # Check if question can be answered by expert's FAQ
  def check_faq_response(message_content, expert_profile)
    return nil if expert_profile.knowledge_base_links.blank?

    faq_content = expert_profile.knowledge_base_links.map do |url|
      begin
        URI.open(url).read
      rescue StandardError => e
        Rails.logger.warn("Failed to fetch #{url}: #{e.message}")
        ""
      end
    end.join("\n\n")

    Rails.logger.info("In LLM service, FAQ Content: #{faq_content}")

    system_prompt = <<~PROMPT
      You are a helpful assistant that answers questions based on an expert's FAQ.
      If the question can be answered from the FAQ, provide a clear, concise answer.
      If the question cannot be answered from the FAQ, respond with exactly: "NO_FAQ_MATCH"
      
      Do not make up information. Only use what's in the FAQ.
    PROMPT

    user_prompt = <<~PROMPT
      FAQ Content:
      #{faq_content}
      
      User Question:
      #{message_content}
      
      Can you answer this question from the FAQ?
    PROMPT
    
    Rails.logger.info("In LLM service, prompt: #{user_prompt}")
    
    response = @client.call(
      system_prompt: system_prompt,
      user_prompt: user_prompt,
      max_tokens: 300,
      temperature: 0.5
    )

    output = response[:output_text].strip

    Rails.logger.info("In LLM service, response: #{output}")
    
    # Return nil if no match found
    return nil if output.include?("NO_FAQ_MATCH")
    
    output
  end

  # Generate conversation summary 
  ## This is shown in LOGS but is not currently implemented in the front end!
  def generate_conversation_summary(conversation)
    messages = conversation.messages.order(:created_at).limit(20)
    
    return "No messages yet" if messages.empty?

    # Build conversation history
    conversation_text = messages.map do |msg|
      "#{msg.sender_role}: #{msg.content}"
    end.join("\n")

    ### Create prompts for summary generation
    system_prompt = <<~PROMPT
      You are a summarization assistant. Create a brief, informative summary 
      of the conversation so far in 1-2 sentences. Focus on the main topic and any 
      key points or resolutions.
    PROMPT

    user_prompt = <<~PROMPT
      Conversation:
      #{conversation_text}
      
      Provide a brief summary (1-2 sentences):
    PROMPT

    Rails.logger.info("Prompt: #{user_prompt}")
    response = @client.call(
      system_prompt: system_prompt,
      user_prompt: user_prompt,
      max_tokens: 100,
      temperature: 0.5
    )

    response[:output_text].strip
    Rails.logger.info("Response: #{response[:output_text].strip}")
  end
end