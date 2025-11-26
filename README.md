# Bounded Blocking Queue (MQ)

Lightweight demonstration of a bounded blocking queue with single producer, single consumer threads. The project includes a small demo script and an extensive unittest suite that can be run with coverage.

## Quick start
- Clone: `git clone <repo-url> && cd MQ`
- Python: 3.10+ recommended.
- Create venv: `python -m venv .venv`
- Activate venv: `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows)
- Dependencies: implementation and demo use only the standard library. Install coverage tooling via:
  - `pip install -r requirements.txt`

## Run tests with coverage
From the project root with the virtual environment activated:
```
coverage run -m unittest discover -v
coverage report -m
```
To generate a browsable HTML coverage report:
```
coverage html
open htmlcov/index.html   # macOS; use your browser to open htmlcov/index.html on other platforms
```
`.coverage` is the binary data file that `coverage run` creates to track executed lines; it is not meant to be stored in Git. `coverage html` reads that data and generates the human-readable HTML report in `htmlcov/`, which you can build locally with the commands above.

## Run the demo message queue
Execute the sample producer/consumer flow:
```
python demo-mq.py
```
You should see the source and destination lists printed, showing that all items were transferred through the queue.

## Project layout
- `mq.py` — implementation of `BoundedBlockingQueue`, `Producer`, and `Consumer`.
- `demo-mq.py` — runnable example that wires one producer and one consumer.
- `testmq.py` — unittest coverage for queue behavior and producer/consumer integration.
