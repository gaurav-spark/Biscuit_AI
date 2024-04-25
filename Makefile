PACKAGE_NAME := biscuit-cms

create_env:
	python3 -m venv env

install:
	pip install -r requirements.txt

runserver:
	python manage.py runserver 0:8000

reformat:
	black .

generate_schema:
	python manage.py spectacular --color --file templates/schema.yml