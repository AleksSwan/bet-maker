# Bet Maker Service

The Bet Maker Service is a FastAPI-based application that handles betting operations, event management, and integrates with Kafka, Redis, and PostgreSQL. The service is designed to be highly scalable and efficient, making use of asynchronous programming and Docker for containerization.

## Table of Contents

- [Features](#features)
- [Line-Provider Service](#line-provider-service)
- [Installation](#installation)
- [Usage](#usage)
- [Makefile Commands](#makefile-commands)
- [Docker Setup](#docker-setup)
- [License](#license)

## Features

- Asynchronous Kafka consumers and producers
- Redis caching for quick data retrieval
- PostgreSQL database integration
- FastAPI routes for managing bets and events
- Dockerized services for easy deployment

## Line-Provider Service

The Line-Provider service manages events and communicates with the Bet Maker service. It handles creating and updating events, storing them in an internal dictionary, and sending them to the Bet Maker service via Kafka or HTTP. The service is built using FastAPI and includes a Kafka producer for event handling.

## Installation

To set up the Bet Maker Service, clone the repository and navigate to the project directory:

```bash
git clone https://github.com/AleksSwan/bet-maker.git
cd bet-maker
```

Install the dependencies using Pipenv:

```bash
pipenv install --dev
```

## Usage

Run the application using the Makefile commands. All operations should be executed through the Makefile to ensure consistency.

Start the application:

```bash
make up
```

Stop the application:

```bash
make down
```

## Makefile Commands

The following commands are available in the Makefile:

- `make up` - Start the services
- `make down` - Stop the services
- `make lint` - Run code linters and checkers
- `make test` - Run all tests
- `make clean` - Remove build artifacts and temporary files
- `make paths` - Display Python paths
- `make help` - Show the help message

## Docker Setup

The Bet Maker Service is fully containerized using Docker. The `docker-compose.yaml` file defines multiple services, including Zookeeper, Kafka, Nginx, Line-Provider, Bet-Maker, PostgreSQL, and Redis. To build and run the Docker containers, use the Makefile:

```bash
make up
```

This command will build and start all the necessary services, including the Bet Maker and Line-Provider services.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

