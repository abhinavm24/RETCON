"""Process-safe local JSON store shared by the writer server and Airflow tasks."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile

from .seed import seed_story

STATE_DIR = Path(os.environ.get("RETCON_STATE_DIR", Path(os.environ.get("AIRFLOW_HOME", Path.home() / "airflow")) / "retcon"))


def initial_state():
    return {"story": seed_story(), "run": None, "history": []}


@contextmanager
def transaction():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / "state.json"
    with (STATE_DIR / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(path.read_text()) if path.exists() else initial_state()
        try:
            yield state
            fd, tmp = tempfile.mkstemp(dir=STATE_DIR, prefix=".state-", suffix=".json")
            try:
                with os.fdopen(fd, "w") as stream:
                    json.dump(state, stream, ensure_ascii=False, indent=2)
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load_state():
    with transaction() as state:
        return json.loads(json.dumps(state))
