class CreateExpertAssignments < ActiveRecord::Migration[8.1]
  def change
    create_table :expert_assignments do |t|
      t.references :conversation, null:false, foreign_key:true
      t.references :expert, null:false, foreign_key: {to_table: :users}
      t.string :status, null:false, default: 'active'
      t.datetime :assigned_at, null:false
      t.datetime :resolved_at
      t.integer :rating

      t.timestamps
    end
  end
end
