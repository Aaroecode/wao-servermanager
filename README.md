# WAO Server Manager

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0%2B-5865F2.svg)](https://discordpy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A bridge application between Discord and Minecraft, providing a FastAPI backend, an advanced RCON implementation, and a comprehensive Discord bot for support tickets and moderation.

## Features

* **FastAPI Backend**: Exposes webhooks and API endpoints for communication between the Minecraft server and other services.
* **Discord Bot**: Built with `discord.py`, features advanced slash commands, support tickets generation with HTML transcripts, inventory management, and welcome messages.
* **Advanced Async RCON**: A robust, rate-limited, asynchronous Minecraft RCON implementation to communicate with the Minecraft server reliably.
* **Asynchronous SQLite Worker**: Dedicated background thread for SQLite operations ensuring non-blocking database queries with built-in schema migration and automated backups.

## Requirements

* Python 3.8+
* A Minecraft Server with RCON enabled.
* A Discord Bot Token.

## Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repository_url>
   cd wao-servermanager
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   Create a `.env` file in the root directory and configure the following variables:
   ```env
   DISCORD_BOT_TOKEN=your_discord_bot_token
   MINECRAFT_RCON_HOST=127.0.0.1
   MINECRAFT_RCON_PORT=25575
   MINECRAFT_RCON_PASSWORD=your_rcon_password
   ```

4. **Run the Server**
   ```bash
   python main.py
   ```
   The application will start the FastAPI server on `127.0.0.1:7001` and launch the Discord bot simultaneously.

## Project Tracking & To-Do

- [x] Base FastAPI application structure
- [x] Asynchronous SQLite database service
- [x] Advanced RCON implementation
- [x] Discord bot Cogs (Tickets, Chat Bridge, Validation)
- [x] Refactor variable names for better code readability
- [x] Add docstrings to complex logic and packet formats
- [ ] Implement robust error handling for Minecraft server offline state
- [ ] Add unit and integration tests
- [ ] Set up continuous integration and deployment (CI/CD)
- [ ] Containerize application using Docker
