FROM python:3.9

# Install ffmpeg for Whisper
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# Create uploads folder and set permissions
RUN mkdir -p /code/uploads && chmod 777 /code/uploads

CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
