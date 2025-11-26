from typing import List
from mq import (
    BoundedBlockingQueue,
    Producer,
    Consumer,
)
def run_producer_consumer():
    """
    Runs one producer & one consumer  thread concurrently.
    This is what you'd call from `if __name__ == "__main__":`
    or from your unit test.
    """
    source_data = list(range(1, 21)) # Source container
    destination_data: List[int] = []  # Destination container

    queue = BoundedBlockingQueue(maxsize=10)
    SENTINEL = object()  # Unique sentinel instance

    producer = Producer(source_data, queue, SENTINEL)
    consumer = Consumer(queue, destination_data, SENTINEL)

    producer.start()
    consumer.start()

    producer.join()
    consumer.join()

    # At this point, all data should have been transferred
    print("Source data:     ", source_data)
    print("Destination data:", destination_data)


if __name__ == "__main__":
    run_producer_consumer()