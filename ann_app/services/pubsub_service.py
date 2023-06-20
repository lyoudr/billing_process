from google.cloud import pubsub_v1 
from concurrent.futures import TimeoutError

import random 
import time

project_id = 'ikala-cloud-swe-dev-sandbox'
topic_id='my-topic'
sub_id = 'my-sub'
timeout = 20.0

def publish():
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    
    # Monitor randomly generate streaming billing data
    for n in range(1, 15):
        billing_amount = random.uniform(10, 100)
        data_str = f"company, A, service, Cloud Run, cost, {billing_amount}"
        # Data must be a bytestinrg 
        data = data_str.encode("utf-8")
        # When you publish a message, the client returns a future.
        future = publisher.publish(topic_path, data)
        time.sleep(1)
        print(future.result())

    print(f"Published messages to {topic_path}")


"""
Pub/Sub service APIs
    - Pull
    - Streaming Pull

1. Streaming Pull API
    (1) The client sends a request to the server to establish a connection. If the connection quota is exceeded, the server returns a resource exhausted error.
        The client library retries the out-of-quota errors automatically.
    (2) If there is no error or the connection quota is available again, the server continuously sends messages to the connected client
    (3) If or when the throughput quota is exceeded, the server stops sending messages. However, the connection is not broken.
        Whenever there's sufficient throughput quota available again, the stream resumes.
    (4) The client or the server eventually closes the connection.
2. Flow control:
    flow control allows you to control the rate at which messages are pulled from a subscription. 
    Flow control is useful to ensure that your subscriber doesn't get overwhelmed with a large number of messages or when you want to limit the rate of message processing.
"""
def subscribe():
    subscriber = pubsub_v1.SubscriberClient()
    sub_path = subscriber.subscription_path(project_id, sub_id)
    # Limit the subscriber to only have ten outstanding messages at a time.
    flow_control = pubsub_v1.types.FlowControl(max_messages=10)

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        print(f"Received {message}.")
        message.ack()
    
    streaming_pull_future = subscriber.subscribe(sub_path, callback, flow_control=flow_control)

    # Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
            # When `timeout` is not set, result() will block indefinitely,
            # unless an exception is encountered fist  
            streaming_pull_future.result(timeout=timeout)
        except TimeoutError:
            streaming_pull_future.cancel() # Trigger the shutdown
            streaming_pull_future.result() # Block until the shutdown is complete