from fastapi import FastAPI, Request
import pika
import json
import os

app = FastAPI()

# Настройки RabbitMQ
RABBIT_HOST = os.getenv('RABBIT_HOST', 'rabbitmq')
RABBIT_USER = os.getenv('RABBIT_USER', 'ansible_worker')
RABBIT_PASS = os.getenv('RABBIT_PASS', 'worker_pass')

def send_to_rabbit(message: dict):
    """Universal function to send a message to the queue"""
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    parameters = pika.ConnectionParameters(host=RABBIT_HOST, credentials=credentials)
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Ensure the queue exists
    channel.queue_declare(queue='netbox_tasks', durable=True)
    
    channel.basic_publish(
        exchange='',
        routing_key='netbox_tasks',
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2) # Message durability
    )
    connection.close()

@app.post("/netbox-webhook")
async def handle_webhook(request: Request):
    try:
        payload = await request.json()
        
        # LOGIC TO DETERMINE THE SOURCE OF THE WEBHOOK:
        # 1. If it's a standard NetBox Webhook (has the 'data' key)
        if 'data' in payload:
            device_name = payload['data'].get('name')
            event_type = payload.get('event', 'webhook_update')
            message = {'device': device_name, 'action': event_type}
        
        # 2. If it's your manual request from Custom Script
        else:
            device_name = payload.get('device')
            action = payload.get('action', 'manual_force_update')
            message = {'device': device_name, 'action': action}

        if not device_name:
            return {"status": "error", "message": "No device name found"}, 400

        print(f" [V] Publishing task to RabbitMQ: {message}")
        send_to_rabbit(message)
        
        return {"status": "sent_to_queue", "payload": message}
    
    except Exception as e:
        print(f" [X] Proxy error: {e}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
