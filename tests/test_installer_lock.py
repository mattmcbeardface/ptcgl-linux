import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path

from ptcgl_linux.installer import _installer_cache_lock


def hold_lock(cache, entered, release):
    with _installer_cache_lock(cache):
        entered.set()
        release.wait(timeout=10)


def wait_for_lock(cache, acquired):
    with _installer_cache_lock(cache):
        acquired.set()


class InstallerLockTests(unittest.TestCase):
    def test_lock_serializes_processes(self):
        ctx = multiprocessing.get_context("spawn")

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            entered = ctx.Event()
            release = ctx.Event()
            acquired = ctx.Event()

            first = ctx.Process(
                target=hold_lock,
                args=(cache, entered, release),
            )
            second = ctx.Process(
                target=wait_for_lock,
                args=(cache, acquired),
            )

            try:
                first.start()
                self.assertTrue(
                    entered.wait(timeout=5),
                    "First process did not acquire lock",
                )

                second.start()

                self.assertFalse(
                    acquired.wait(timeout=0.5),
                    "Second process acquired lock prematurely",
                )

                release.set()

                self.assertTrue(
                    acquired.wait(timeout=5),
                    "Second process never acquired released lock",
                )
            finally:
                release.set()

                for process in (first, second):
                    if process.pid is not None:
                        process.join(timeout=3)
                        if process.is_alive():
                            process.terminate()
                            process.join(timeout=3)

            self.assertEqual(first.exitcode, 0)
            self.assertEqual(second.exitcode, 0)


if __name__ == "__main__":
    unittest.main()
