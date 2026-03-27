import pika
import time
import json
import ansible_runner
import os
import threading

def run_ansible_task(connection, channel, delivery_tag, device_name):
    try:
        print(f" [>] Starting job for: {device_name}")
        
        # Запуск Ansible
        r = ansible_runner.run(
            private_data_dir='/ansible',
            playbook='site.yml',
            extravars={'target_host': device_name}
        )

        if r.status == 'successful':
            print(f" [OK] {device_name} configured successfully")
        else:
            print(f" [!] Error in Ansible for {device_name}")

    except Exception as e:
        print(f" [X] Error inside thread: {e}")
    
    finally:
        # IMPORTANT: Send ACK through the main RabbitMQ thread
        connection.add_callback_threadsafe(
            lambda: channel.basic_ack(delivery_tag=delivery_tag)
        )

def my_callback(ch, method, properties, body):
    """This method is called by pika when a message is received"""
    try:
        data = json.loads(body.decode('utf-8'))
        device_name = data.get('device')
        print(f" [V] Message received, creating thread for: {device_name}")

        # Create and start a thread, passing connection and channel
        t = threading.Thread(
            target=run_ansible_task, 
            args=(ch.connection, ch, method.delivery_tag, device_name)
        )
        t.start()

    except Exception as e:
        print(f" [X] Error in callback: {e}")
        # If we couldn't even create a thread — acknowledge to avoid looping error
        ch.basic_ack(delivery_tag=method.delivery_tag)

# Connect to RabbitMQ (use the container name if they are in the same network)
def connect_rabbitmq():
    rabbit_host = os.getenv('RABBIT_HOST', 'rabbitmq')
    rabbit_user = os.getenv('RABBIT_USER', 'ansible_worker')
    rabbit_pass = os.getenv('RABBIT_PASS', 'worker_pass')
    credentials = pika.PlainCredentials(rabbit_user, rabbit_pass)
    parameters = pika.ConnectionParameters(host=rabbit_host, credentials=credentials, heartbeat=600, blocked_connection_timeout=300)
    while True:
        try:
            print(f" [*] Connecting to RabbitMQ at {rabbit_host}...")
            connection = pika.BlockingConnection(parameters)
            return connection
        except pika.exceptions.AMQPConnectionError:
            print(" [!] RabbitMQ not available, retrying in 5 seconds...")
            time.sleep(5)

connection = connect_rabbitmq()
channel = connection.channel()

channel.queue_declare(queue='netbox_tasks', durable=True)
channel.basic_qos(prefetch_count=1) # Take one task at a time
channel.basic_consume(queue='netbox_tasks', on_message_callback=my_callback)

print(' [*] Dispatcher started. Waiting for tasks...')
channel.start_consuming()
