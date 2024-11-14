class RemoveItemIdFromOrders < ActiveRecord::Migration[7.1]
  def change
    remove_column :orders, :item_id, :bigint
    remove_column :orders, :price
  end
end
