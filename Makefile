migrate:
	alembic upgrade head
makemigration:
	alembic revision --autogenerate -m "auto"
up:
	docker-compose up -d --build
	@echo "Aguardando o banco iniciar..."
	timeout /T 10 /NOBREAK > NUL
	docker-compose exec fastapi alembic upgrade head
	docker-compose logs fastapi