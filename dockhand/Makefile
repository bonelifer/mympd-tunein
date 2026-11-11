# Makefile for managing Docker Compose projects with encrypted secrets using env-vault

.DEFAULT_GOAL := default

# Bring up the container
up:
	-@if [ ! -f ./prod.env ]; then \
	  sudo docker compose up -d; \
	 else \
	  env-vault prod.env docker compose -- up -d; \
	 fi

# Edit the prod.env secrets file
edit:
	-@if [ ! -f ./prod.env ]; then \
	  echo "prod.env doesn't exist, please run the command below to create the file."; \
	  echo "make init"; \
	 else \
	  env-vault edit prod.env; \
	 fi

# Decrypt the prod.env secrets file
decrypt:
	-@if [ ! -f ./prod.env ]; then \
	  echo "prod.env doesn't exist, please run the command below to create the file."; \
	  echo "make init"; \
	 else \
	  env-vault decrypt prod.env; \
	 fi

# Re-encrypt the prod.env secrets file
encrypt:
	-@if [ ! -f ./prod.env ]; then \
	  echo "prod.env doesn't exist, please run the command below to create the file."; \
	  echo "make init"; \
	 else \
	  env-vault encrypt prod.env; \
	 fi

# Create the prod.env secrets file if it doesn't exist
init:
	-@if [ -f ./prod.env ]; then \
	  echo "prod.env already exists"; \
	 else \
	  env-vault create prod.env; \
	 fi

# Pull the newest image and recreate the container
pull:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "Is this a docker compose project? The docker-compose.yml doesn't exist"; \
	 else \
	  sudo docker compose pull; \
	  sudo docker compose up -d --remove-orphans; \
	 fi

# Start the container
start:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "Is this a docker compose project? The docker-compose.yml doesn't exist"; \
	 else \
	  sudo docker compose start; \
	 fi

# Stop the container
stop:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "Is this a docker compose project? The docker-compose.yml doesn't exist"; \
	 else \
	  sudo docker compose stop; \
	 fi

# Restart the container
restart:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "Is this a docker compose project? The docker-compose.yml doesn't exist"; \
	 else \
	  sudo docker compose restart; \
	 fi

# Force docker compose to recreate the container
force:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "Is this a docker compose project? The docker-compose.yml doesn't exist"; \
	 else \
	  sudo docker compose up -d --force-recreate --remove-orphans; \
	 fi

# View container logs
logs:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "docker-compose.yml not found."; \
	 else \
	  sudo docker compose logs -f --tail=100; \
	 fi

# Show container status
ps:
	-@if [ ! -f ./docker-compose.yml ]; then \
	  echo "docker-compose.yml not found."; \
	 else \
	  sudo docker compose ps; \
	 fi

# Prune unused volumes and networks
prune:
	@echo "Pruning unused Docker volumes and networks..."
	@docker volume prune -f
	@docker network prune -f

# Default target displaying usage information
default:
	@ echo " "; \
	echo "make up      - bring up the container"; \
	echo "make edit    - edit the prod.env secrets file"; \
	echo "make decrypt - decrypt the prod.env secrets file"; \
	echo "make encrypt - re-encrypt the prod.env secrets file"; \
	echo "make init    - create the prod.env secrets file"; \
	echo "make pull    - pull the newest image and recreate the container"; \
	echo "make start   - start the container"; \
	echo "make stop    - stop the container"; \
	echo "make restart - restart the container"; \
	echo "make force   - force docker compose to recreate the container"; \
	echo "make logs    - view container logs"; \
	echo "make ps      - show container status"; \
	echo "make prune   - remove unused volumes and networks"
