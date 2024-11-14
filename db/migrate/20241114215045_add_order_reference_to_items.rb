class AddOrderReferenceToItems < ActiveRecord::Migration[7.1]
  def change
    add_reference :items, :order, null: true, foreign_key: true
  end
end
