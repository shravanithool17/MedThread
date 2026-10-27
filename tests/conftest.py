"""Give every pytest process an isolated SQLite database."""

import os
import tempfile
import atexit


_test_database_directory = tempfile.TemporaryDirectory(prefix="medthread-pytest-")
atexit.register(_test_database_directory.cleanup)
os.environ["MEDTHREAD_DB_PATH"] = os.path.join(
    _test_database_directory.name,
    "test.sqlite3",
)
