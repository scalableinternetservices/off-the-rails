# README

11/13: Added Item model to DB with attributes:
- name :string
- price :decimal
- condition :string (e.g. new, used, fair)
- description :text

To run a db migration with docker:
`docker-compose run web rails db:migrate`


