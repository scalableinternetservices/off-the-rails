class AddJwtRevokedAtToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :jwt_revoked_at, :datetime
  end
end
