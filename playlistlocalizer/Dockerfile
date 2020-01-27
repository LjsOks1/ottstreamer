FROM python:3-slim
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY playlist_localizer.py /
CMD ["python", "./playlist_localizer.py"]


