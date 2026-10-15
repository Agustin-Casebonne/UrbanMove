#!/bin/bash
# Se ejecuta automáticamente cuando LocalStack está listo.
# Crea la infraestructura de eventos y el Data Lake.
set -e
REGION=us-east-1
ACCOUNT=000000000000
TOPIC_ARN=arn:aws:sns:$REGION:$ACCOUNT:urbanmove-events

echo "== Bus de eventos (SNS)"
awslocal sns create-topic --name urbanmove-events

# Dead-letter queue común: los mensajes que fallan 3 veces terminan aquí
awslocal sqs create-queue --queue-name urbanmove-dlq
DLQ_ARN=arn:aws:sqs:$REGION:$ACCOUNT:urbanmove-dlq

# Una cola por consumidor (cada uno procesa a su ritmo y puede caerse sin afectar a los demás)
for Q in history availability datalake-ingest maintenance-detector; do
  echo "== Cola urbanmove-$Q"
  awslocal sqs create-queue --queue-name "urbanmove-$Q" \
    --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\",\"VisibilityTimeout\":\"30\"}"
  awslocal sns subscribe --topic-arn "$TOPIC_ARN" --protocol sqs \
    --notification-endpoint "arn:aws:sqs:$REGION:$ACCOUNT:urbanmove-$Q" \
    --attributes RawMessageDelivery=true
done

echo "== Data Lake (S3)"
awslocal s3 mb s3://urbanmove-datalake
for LAYER in raw trusted curated; do
  awslocal s3api put-object --bucket urbanmove-datalake --key "$LAYER/"
done

echo "== Infraestructura UrbanMove lista"
