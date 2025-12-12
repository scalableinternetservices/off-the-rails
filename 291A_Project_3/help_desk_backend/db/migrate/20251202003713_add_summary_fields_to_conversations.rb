class AddSummaryFieldsToConversations < ActiveRecord::Migration[8.1]
  def change
    add_column :conversations, :summary, :text
    add_column :conversations, :message_count_at_summary, :integer
  end
end
