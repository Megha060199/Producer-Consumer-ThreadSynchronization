import threading
from collections import deque
from typing import Any, Iterable, List



## Project Specifications:
# Single producer, single consumer 
## Multiple consumers/producers are out of scope for this assignment. 
#• Short Description: Implement producer-consumer pattern with thread synchronization
#• Testing Objectives:
#•  Thread synchronization
#•  Concurrent programming
#•  Blocking queues
#  Wait/Notify mechanism
# Detailed Description: Implement a classic producer-consumer pattern demonstrating thread
#synchronization and communication. The program will simulate concurrent data transfer
#between a producer thread that reads from a source container and places items into a shared
#queue, and a consumer thread that reads from the queue and stores items in a destination
#container.

class BoundedBlockingQueue:
    """
    Bounded blocking queue.
    1) put(item): Inserts an Item in the queue. Blocks if the queue is full
    2) get(): Gets at item from the queue. Blocks if the queue is empty

    Internally uses:
    1) A deque for queue FIFO implementation  
    2) A Lock for mutual exclusion
     Two Condition variables for wait/notify
      *** not_empty: consumer waits when queue is empty
      *** not_full: producer waits when queue is full
    """

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be > 0")
        self._maxsize = maxsize
        self._queue = deque()  # underlying container
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

    def put(self, item: Any) -> None:
        """Put an item into the queue, blocking if it is full."""
        with self._not_full:
            # Wait while the queue is full
            while len(self._queue) >= self._maxsize:
                self._not_full.wait()
            # Add the item
            self._queue.append(item)
            # Notify one waiting consumer that an item is available
            self._not_empty.notify()

    def get(self) -> Any:
        """Remove and return an item from the queue, blocking if empty."""
        with self._not_empty:
            # Wait while the queue is empty
            while not self._queue:
                self._not_empty.wait()

            item = self._queue.popleft()

            # Notify one waiting producer that space is available
            self._not_full.notify()

            return item

    def qsize(self) -> int:
        """Return the current size of the queue (approximate)."""
        with self._lock:
            return len(self._queue)


class Producer(threading.Thread):
    """
    Producer thread:
    1) Reads items from a source container (Iterable)
    2)Places them into the shared blocking queue
    3) Finally puts a sentinel to signal 'no more items'
    """

    def __init__(self, source: Iterable[Any], queue: BoundedBlockingQueue, sentinel: Any) -> None:
        super().__init__(name="ProducerThread")
        self._source = source
        self._queue = queue
        self._sentinel = sentinel

    def run(self) -> None:
        for item in self._source:
            self._queue.put(item)
        # Signal completion
        self._queue.put(self._sentinel)


class Consumer(threading.Thread):
    """
    Consumer thread:
    1) Reads items from the shared blocking queue
    2) Stores them into the destination container
    3) Stops when it encounters the sentinel value
    """

    def __init__(self, queue: BoundedBlockingQueue, dest: List[Any], sentinel: Any) -> None:
        super().__init__(name="ConsumerThread")
        self._queue = queue
        self._dest = dest
        self._sentinel = sentinel

    def run(self) -> None:
        while True:
            item = self._queue.get()
            if item is self._sentinel:
                # Optional: put sentinel back if you had multiple consumers
                # For single consumer, just break
                break
            self._dest.append(item)



