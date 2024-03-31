# [Audio Splitter Bot](https://t.me/AudioSplitterRobot)
#### A Telegram bot for separating songs into components such as vocals, instrumental, guitar, or bass.

## Basic technical info
![Static Badge](https://img.shields.io/badge/python-3.10-blue)
![Static Badge](https://img.shields.io/badge/aiogram-3.4-blue)

* Based on `aiogram` python module and `ffmpeg` for audio processing
* Uses the `lalal.ai` API for separating audio tracks

## How it works
Lala.ai is a service that allows you to separate audio tracks into components such as vocals, instrumental, guitar, or bass. But free usage on the official site is limited to 1 minute of audio. 

This bot allows you to split audio tracks without any restrictions. When you send an audio file to the bot, it splits the file into pieces one minute at a time, sends it to the server, and then combines it back into one file and sends the result to the user.

## Deployment
1. Create a database with the tables from the `models.sql` file
2. Fill out the `.env` file with the necessary data
3. Install dependencies from `requirements.txt`
4. Compile localization files with `pybabel compile -d locales -D bot`
5. Run the bot with `python -m app`
6. Run the updater daemon with `python daemons/updater.py`

## License
This project is licensed under the CC BY-NC-SA 4.0 License - see the [LICENSE](LICENSE.txt) file for details.
