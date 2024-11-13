class CreateItems < ActiveRecord::Migration[7.1]
  def change
    create_table :items do |t|
      t.string :name
      t.decimal :price
      t.string :condition
      t.text :description

      t.timestamps
    end
  end
end
