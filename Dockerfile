FROM python:3.9-slim

WORKDIR /app

ENV PORT 8000
ENV DEBUG False

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "api/index.py"]