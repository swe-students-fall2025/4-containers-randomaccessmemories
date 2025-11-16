![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)

# Audio Note Web App

This project is a Flask web application using PyMongo that allows users to record audio memos, which are then transcribed using AI-assisted speech recognition. The app automatically generates structured notes from the transcriptions, helping users organize and retrieve their thoughts efficiently.

## Team Members

- [Aayan Mathur](https://github.com/aayanmathur)
- [Aden Juda](https://github.com/yungsemitone)
- [Eason Huang](https://github.com/GILGAMESH605)
- [Luna Suzuki](https://github.com/lunasuzuki)
- [Zeba Shafi](https://github.com/Zeba-Shafi)

## How to Launch the App

Follow these steps to set up and launch the full application stack (MongoDB, machine learning client, and web app):

1. **Clone the repository** (if you haven't already):

```sh
git clone <repo-url>
cd 4-containers-randomaccessmemories
```

2.**Copy the example environment file and edit as needed:**

```sh
cp .env.example .env
# Edit .env to set your desired values (or use the defaults for testing)
```

3.**Build and start all services with Docker Compose:**

```sh
docker-compose up --build
```

This will start:

- MongoDB (database)
- Machine learning client (Python)
- Web app (Flask)

4.**Access the web app:**

- Open your browser and go to: [http://localhost:5000](http://localhost:5000)

5.**Stopping the app:**

- Press `Ctrl+C` in the terminal running Docker Compose, or run:

```sh
docker-compose down
```

**Note:**

- The default database and credentials are set for local development and testing. For production, update your `.env` file with secure values.
- Make sure Docker and Docker Compose are installed on your system.
