# README

11/13: Added models to DB

Item:
- name :string
- price :decimal
- condition :string (e.g. new, used, fair)
- description :text
- user :reference # this will be the seller attached to the item
- rating :reference # can create many reviews
- order: reference # can place many orders

User:
- name: string
- item: :reference
- order: :reference
- rating: :reference

Order:
- status: string
- item: :reference

Rating:
- rating: :integer (1-5)
- review: :string
- user: :reference
- item: :reference

To run a db migration with docker:
`docker-compose run web rails db:migrate`


