# README

11/13: Added models to DB

**Item:**
- name: string
- price: decimal
- condition: string (e.g. new, used, fair)
- description: text
- user_id: reference # this will be the seller attached to the item
- order_id: reference # an item belongs to an order - null until order placed
- an item can also have many:
    - reviews

**User:**
- name: string
- a user can have many:
    - items
    - orders
    - ratings

**Order:**
- status: string
- user_id: reference
- an order can have many:
    - items

**Rating:**
- rating: :integer (1-5)
- review: :string
- user_id: :reference
- item_id: :reference

To run a db migration with docker:
`docker-compose run web rails db:migrate`


