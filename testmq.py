
import unittest
import threading
import time
import random

from mq import (
    BoundedBlockingQueue,
    Producer,
    Consumer,
)


class TestBoundedBlockingQueue(unittest.TestCase):

    # ---------- Constructor Tests ----------

    def test_invalid_maxsize_raises(self):
        with self.assertRaises(ValueError):
            BoundedBlockingQueue(0)
        with self.assertRaises(ValueError):
            BoundedBlockingQueue(-1)

    # ---------- FIFO  Behavior ----------

    def test_put_get_fifo_single_thread(self):
        q = BoundedBlockingQueue(maxsize=3)
        items = [1, 2, 3]

        for item in items:
            q.put(item)

        self.assertEqual(q.qsize(), 3)

        result = [q.get(), q.get(), q.get()]
        self.assertEqual(result, items)
        self.assertEqual(q.qsize(), 0)

    def test_qsize_changes_correctly(self):
        q = BoundedBlockingQueue(maxsize=5)
        q.put(10)
        q.put(20)
        self.assertEqual(q.qsize(), 2)

        _ = q.get()
        self.assertEqual(q.qsize(), 1)

    def test_boundary_exact_maxsize(self):
        q = BoundedBlockingQueue(maxsize=3)
        q.put(1)
        q.put(2)
        q.put(3)

        self.assertEqual(q.qsize(), 3)

        self.assertEqual(q.get(), 1)
        self.assertEqual(q.get(), 2)
        self.assertEqual(q.get(), 3)
        self.assertEqual(q.qsize(), 0)

    # ---------- Blocking Behavior ----------

    def test_get_blocks_until_item_available(self):
        q = BoundedBlockingQueue(maxsize=1)
        result = []
        done = threading.Event()

        def consumer():
            item = q.get()  # Should block
            result.append(item)
            done.set()

        t = threading.Thread(target=consumer)
        t.start()

        time.sleep(0.1)
        self.assertFalse(done.is_set(), "Consumer should be blocked on empty queue")

        q.put(99)  # Unblocks the consumer

        finished = done.wait(timeout=1.0)
        self.assertTrue(finished)
        self.assertEqual(result, [99])

        t.join()

    def test_put_blocks_when_queue_full(self):
        q = BoundedBlockingQueue(maxsize=1)
        q.put("A")

        done = threading.Event()

        def producer():
            q.put("B")  # Should block until "A" is consumed
            done.set()

        t = threading.Thread(target=producer)
        t.start()

        time.sleep(0.1)
        self.assertFalse(done.is_set(), "Producer should be blocked on full queue")

        self.assertEqual(q.get(), "A")  # Frees space

        finished = done.wait(timeout=1.0)
        self.assertTrue(finished)

        self.assertEqual(q.get(), "B")
        t.join()

    # ---------- Existing Producer / Consumer Integration Tests ----------

    def test_consumer_stops_on_sentinel(self):
        q = BoundedBlockingQueue(maxsize=10)
        dest = []
        SENTINEL = object()

        q.put(1)
        q.put(2)
        q.put(SENTINEL)

        consumer = Consumer(q, dest, SENTINEL)
        consumer.start()
        consumer.join(timeout=2.0)

        self.assertEqual(dest, [1, 2])
        self.assertEqual(q.qsize(), 0)

    def test_producer_empty_source_sends_only_sentinel(self):
        q = BoundedBlockingQueue(maxsize=5)
        dest, source = [], []
        SENTINEL = object()

        p = Producer(source, q, SENTINEL)
        c = Consumer(q, dest, SENTINEL)

        p.start()
        c.start()
        p.join()
        c.join()

        self.assertEqual(dest, [])

    def test_burst_put_get_qsize_consistency(self):
        maxsize = 20
        q = BoundedBlockingQueue(maxsize=maxsize)

        NUM_PRODUCERS = 4
        NUM_CONSUMERS = 4
        BURST = 50
        TOTAL_ITEMS = NUM_PRODUCERS * BURST

        produced = []
        consumed = []
        produced_lock = threading.Lock()
        consumed_lock = threading.Lock()

        SENTINEL = object()

        # ---- Producers ----
        def producer_fn(pid):
            items = [f"P{pid}-{i}" for i in range(BURST)]
            with produced_lock:
                produced.extend(items)
            for item in items:
                q.put(item)
                if random.random() < 0.03:
                    time.sleep(random.uniform(0, 0.01))

        # ---- Consumers ----
        def consumer_fn():
            while True:
                item = q.get()
                if item is SENTINEL:
                    # One sentinel per consumer, so just stop
                    break
                with consumed_lock:
                    consumed.append(item)
                if random.random() < 0.03:
                    time.sleep(random.uniform(0, 0.01))

        # ---- Sampler ----
        sizes = []

        def sampler():
            for _ in range(300):
                sizes.append(q.qsize())
                time.sleep(0.003)

        producers = [
            threading.Thread(target=producer_fn, args=(i,))
            for i in range(NUM_PRODUCERS)
        ]
        consumers = [threading.Thread(target=consumer_fn) for _ in range(NUM_CONSUMERS)]
        sampler_thread = threading.Thread(target=sampler)

        # Start producers & consumers & sampler
        for t in producers:
            t.start()
        for t in consumers:
            t.start()
        sampler_thread.start()

        # Wait for producers to finish
        for t in producers:
            t.join()

        # Now push one sentinel per consumer, after all real items are enqueued
        for _ in range(NUM_CONSUMERS):
            q.put(SENTINEL)

        # Wait for consumers & sampler
        for t in consumers:
            t.join()
        sampler_thread.join()

        # ---- Assertions ----
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(len(consumed), TOTAL_ITEMS)
        self.assertCountEqual(consumed, produced)
        self.assertTrue(all(0 <= s <= maxsize for s in sizes))

    def test_chaotic_burst_put_get_qsize_consistency(self):
        maxsize = 20
        q = BoundedBlockingQueue(maxsize=maxsize)

        NUM_PRODUCERS = 4
        NUM_CONSUMERS = 4
        BURST = 80
        TOTAL_ITEMS = NUM_PRODUCERS * BURST

        produced = []
        consumed = []
        produced_lock = threading.Lock()
        consumed_lock = threading.Lock()

        SENTINEL = object()

        # ---- Chaotic Producers ----
        def producer_fn(pid):
            items = [f"P{pid}-{i}" for i in range(BURST)]
            with produced_lock:
                produced.extend(items)

            for item in items:
                # Sometimes sleep BEFORE put
                if random.random() < 0.25:
                    time.sleep(random.uniform(0, 0.02))

                q.put(item)

                # Sometimes sleep AFTER put
                r = random.random()
                if r < 0.20:
                    time.sleep(random.uniform(0, 0.01))
                elif r < 0.22:
                    time.sleep(0)

        # ---- Consumers ----
        def consumer_fn():
            while True:
                item = q.get()
                if item is SENTINEL:
                    break

                with consumed_lock:
                    consumed.append(item)

                if random.random() < 0.10:
                    time.sleep(random.uniform(0, 0.01))

        # ---- Sampler ----
        sizes = []

        def sampler():
            for _ in range(500):
                sizes.append(q.qsize())
                time.sleep(0.002)

        producers = [
            threading.Thread(target=producer_fn, args=(i,))
            for i in range(NUM_PRODUCERS)
        ]
        consumers = [threading.Thread(target=consumer_fn) for _ in range(NUM_CONSUMERS)]
        sampler_thread = threading.Thread(target=sampler)

        for t in producers:
            t.start()
        for t in consumers:
            t.start()
        sampler_thread.start()

        for t in producers:
            t.join()

        # After producers are done, enqueue one sentinel per consumer
        for _ in range(NUM_CONSUMERS):
            q.put(SENTINEL)

        for t in consumers:
            t.join()
        sampler_thread.join()

        # ---- Assertions ----
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(len(consumed), TOTAL_ITEMS)
        self.assertCountEqual(consumed, produced)
        self.assertTrue(
            all(0 <= s <= maxsize for s in sizes),
            msg=f"Found invalid qsize samples: "
                f"{[s for s in sizes if s < 0 or s > maxsize]}"
        )


    # ---------- Producer / Consumer Focused Tests ----------

    def test_producer_places_all_items_and_sentinel_in_queue(self):
        """
        Directly tests Producer.run:
        - All source items are put into the queue
        - Exactly one sentinel is put at the end
        """
        q = BoundedBlockingQueue(maxsize=10)
        source = ["a", "b", "c"]
        SENTINEL = object()

        p = Producer(source, q, SENTINEL)
        p.start()
        p.join(timeout=2.0)

        self.assertFalse(p.is_alive(), "Producer thread should have finished")

        size = q.qsize()
        self.assertEqual(size, len(source) + 1)

        items = [q.get() for _ in range(size)]
        self.assertEqual(items[:-1], source)
        self.assertIs(items[-1], SENTINEL)
        self.assertEqual(q.qsize(), 0)

    def test_consumer_drains_queue_and_stops_on_sentinel_only(self):
        """
        Directly tests Consumer.run:
        - Consumer reads until sentinel and stops
        - Sentinel is not added to dest
        """
        q = BoundedBlockingQueue(maxsize=10)
        dest = []
        SENTINEL = object()
        items = [10, 20, 30]

        for x in items:
            q.put(x)
        q.put(SENTINEL)

        c = Consumer(q, dest, SENTINEL)
        c.start()
        c.join(timeout=2.0)

        self.assertFalse(c.is_alive(), "Consumer thread should have finished")
        self.assertEqual(dest, items)
        self.assertEqual(q.qsize(), 0)

    def test_producer_consumer_integration_transfers_all_items(self):
        """
        End-to-end test of Producer + Consumer +
        BoundedBlockingQueue with a bounded size to force blocking.
        """
        source = list(range(50))
        dest = []

        q = BoundedBlockingQueue(maxsize=5)
        SENTINEL = object()

        p = Producer(source, q, SENTINEL)
        c = Consumer(q, dest, SENTINEL)

        p.start()
        c.start()

        p.join(timeout=2.0)
        c.join(timeout=2.0)

        self.assertFalse(p.is_alive(), "Producer should have finished")
        self.assertFalse(c.is_alive(), "Consumer should have finished")

        # All items transferred, in order
        self.assertEqual(dest, source)
        self.assertEqual(q.qsize(), 0)


