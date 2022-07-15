FROM python:3.9.13-alpine3.16
RUN apk add --no-cache gcc && cd /opt/ \
    mkdir check_oracle_bot
    
WORKDIR /opt/check_oracle_bot
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "main.py"]
