"""
Traffic generator: sends requests to OUR OWN API so the Grafana graphs have something to show.

It never calls Open-Meteo directly. Our API caches each city for 10 minutes, so even
thousands of requests here cause at most ~10 calls to Open-Meteo (one per city).

Usage (needs only Python, no extra packages):
  python scripts/traffic.py                      # 2 requests/second for 2 minutes
  python scripts/traffic.py --rps 5 --duration 300
  python scripts/traffic.py --error-share 0.3    # 30% of requests use unknown cities (404s)

Keep --rps small: this is a demo, not a load test.
"""

import argparse
import random
import time
import urllib.error
import urllib.request

GOOD_CITIES = ["delhi", "mumbai", "bengaluru", "chennai", "kolkata",
               "hyderabad", "pune", "jaipur", "london", "new-york"]
BAD_CITIES = ["atlantis", "gotham", "hogwarts", "narnia"]


def send(base_url: str, city: str) -> tuple[int, float]:
    url = f"{base_url}/weather?city={city}"
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as err:   # 4xx / 5xx still give us a status code
        status = err.code
    except urllib.error.URLError:            # API not running / unreachable
        status = 0
    return status, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(description="Send demo traffic to the weather API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--rps", type=float, default=2.0, help="requests per second (max 20)")
    parser.add_argument("--duration", type=int, default=120, help="how long to run, in seconds")
    parser.add_argument("--error-share", type=float, default=0.1,
                        help="share of requests that ask for an unknown city (0 to 1)")
    args = parser.parse_args()

    rps = min(max(args.rps, 0.1), 20)  # safety cap
    pause = 1 / rps
    end = time.time() + args.duration
    counts: dict[int, int] = {}
    total = 0

    print(f"Sending ~{rps} req/s to {args.url} for {args.duration}s (Ctrl+C to stop)")
    try:
        while time.time() < end:
            bad = random.random() < args.error_share
            city = random.choice(BAD_CITIES if bad else GOOD_CITIES)
            status, took = send(args.url, city)
            counts[status] = counts.get(status, 0) + 1
            total += 1
            print(f"{status}  {took * 1000:6.1f} ms  /weather?city={city}")
            time.sleep(pause)
    except KeyboardInterrupt:
        pass

    print(f"\nDone: {total} requests")
    for status, n in sorted(counts.items()):
        label = "API unreachable" if status == 0 else str(status)
        print(f"  {label}: {n}")


if __name__ == "__main__":
    main()
