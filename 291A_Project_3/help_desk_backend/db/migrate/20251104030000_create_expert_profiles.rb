class CreateExpertProfiles < ActiveRecord::Migration[8.1]
  def change
    create_table :expert_profiles do |t|
      # Modify this line
      t.references :user, null: false, foreign_key: true, index: { unique: true }

      t.text :bio
      t.json :knowledge_base_links

      t.timestamps
    end
  end
end