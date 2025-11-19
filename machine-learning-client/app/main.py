"""Entrypoint runner for the machine learning client.

This module provides a `loop()` function that repeatedly invokes the
poller implementation (if present) to process pending recordings. It
supports a one-shot run (`--once`) and graceful shutdown via signals.
"""

from __future__ import annotations

import argparse
import logging
import signal
import time
from typing import Callable, Optional


DEFAULT_INTERVAL = 5.0


def _find_poller_callable() -> Optional[Callable[[], None]]:
    """Attempt to import `app.poller` and find a sensible entry function.

    The poller module (when implemented) may expose several common names
    for a single-step processing function; we try them in order and
    return the first callable we find.
    """
    candidate_names = (
        "process_pending",
        "poll_once",
        "run_once",
        "run",
        "process",
        "poll",
    )
    try:
        # Prefer package-style import when running as a package
        from app import poller  # type: ignore
    except Exception:
        try:
            import poller  # type: ignore
        except Exception:
            logging.getLogger(__name__).warning(
                "No poller module found (app.poller or poller)"
            )
            return None

    for name in candidate_names:
        func = getattr(poller, name, None)
        if callable(func):
            logging.getLogger(__name__).debug("Using poller function: %s", name)
            return func

    logging.getLogger(__name__).warning(
        "No callable poller entrypoint found in app.poller"
    )
    return None


def loop(interval: float = DEFAULT_INTERVAL, run_once: bool = False) -> int:
    """Run the client loop, invoking the poller periodically.

    Returns an exit code (0 on success).
    """
    logger = logging.getLogger(__name__)
    stop = False

    def _signal_handler(signum, frame):
        nonlocal stop
        logger.info("Received signal %s, stopping after current iteration", signum)
        stop = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    poller_func = _find_poller_callable()
    if poller_func is None:
        logger.error("Poller not available; exiting")
        return 2

    iteration = 0
    try:
        while True:
            iteration += 1
            logger.info("Poller iteration %d starting", iteration)
            try:
                poller_func()
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Poller iteration failed: %s", exc)

            if run_once:
                logger.info("Run-once requested; exiting after one iteration")
                break

            if stop:
                logger.info("Stop requested; exiting main loop")
                break

            logger.debug("Sleeping for %s seconds", interval)
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received; shutting down")

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Machine learning client runner")
    parser.add_argument(
        "--once", action="store_true", help="Run a single poll iteration and exit"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(DEFAULT_INTERVAL),
        help="Seconds between poll iterations",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return loop(interval=args.interval, run_once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
