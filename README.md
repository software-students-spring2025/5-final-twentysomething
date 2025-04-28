[![Github Event Logger](https://github.com/software-students-spring2025/5-final-twentysomething/actions/workflows/event-logger.yml/badge.svg?branch=main)](https://github.com/software-students-spring2025/5-final-twentysomething/actions/workflows/event-logger.yml) [![Web-app CI](https://github.com/software-students-spring2025/5-final-twentysomething/actions/workflows/web-app.yml/badge.svg?branch=main)](https://github.com/software-students-spring2025/5-final-twentysomething/actions/workflows/web-app.yml)

# Final Project

## Project Description
A web app that allows users to input a mood, event, or vibe to receive a cocktail recipe in return. Users can create accounts to save recipes and keep a photo journal.


## Prerequisites
Install the following software on your machine:

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Installing Docker

1. Go to the [Docker website](https://www.docker.com/products/docker-desktop) and download Docker Desktop for your operating system.
2. Follow the installation instructions and make sure Docker Desktop is running.

## Running and Configuration Instructions
1. Clone the respository: 

```
git clone https://github.com/software-students-spring2025/5-final-twentysomething.git
cd 5-final-twentysomething
```

2. Create an .env file in the root directory with [env.example](https://github.com/software-students-spring2025/5-final-twentysomething/blob/main/env.example). Set the environment variables with real values instead. 

3. Create a virtual environment with `pip`:

```
python -m venv .venv
source .venv/bin/activate
```

4. Navigate to the web-app directory:

```
cd web-app
```

5. Install dependencies and activate environment:

```
pipenv shell
```

6. You can start up the web application with Docker from the root directory or locally from the web-app directory. If using Docker, make sure to have it running in the background.
```
# Using Docker
docker-compose up --build
```

```
# Locally 
python app.py
```

After, you can visit localhost through http://127.0.0.1:8080.

## Testing
From the web-app directory, you can easily run the unit tests for the web app subsystem with code coverage. 

```
python3 -m pytest --cov=.
```

## Container Images

- [Web-app Container Image](https://hub.docker.com/r/chrisimkim/web-app)

## Contributors

- [Jennifer Yu](https://github.com/jenniferyuuu)
- [Iva Park](https://github.com/ivapark)
- [Chrisim Kim](https://github.com/ChrisimKim)
- [Claire Kim](https://github.com/radishsoups)

## Acknowledgements

- [Free Cocktail API](https://www.thecocktaildb.com/api.php)
