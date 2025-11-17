class CreateMessages < ActiveRecord::Migration[8.1]
  def change
    create_table :messages do |t|
      t.references :conversation, null:false, foreign_key:true
      t.references :sender, null:false, foreign_key:{to_table: :users}
      t.string :sender_role, null:false
      t.text :content, null:false
      t.boolean :is_read, null:false, default:false

      t.timestamps
    end
  end
end
