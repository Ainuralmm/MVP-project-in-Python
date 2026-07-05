# =============================================================================
# automation_lock.py
# =============================================================================
# PURPOSE
# -------
# Guarantees that only ONE Selenium automation runs on this machine (VM) at a
# time, across ALL Streamlit user sessions — something st.session_state CANNOT
# do, because session_state is per-user and the VM is shared.
#
# It also provides:
#   - a HEARTBEAT so a long healthy batch (even 1 hour) is never killed, while
#     a truly HUNG run (no progress for N minutes) is detected and reclaimed;
#   - SELF-HEALING: if the process/driver holding the lock has died (crash,
#     user closed Edge, .bat restarted), the next run reclaims the lock and
#     kills ONLY that specific orphaned driver (by PID) — never a blanket kill.
#
# This module has NO Streamlit dependency on purpose: it must be callable from
# deep inside model.py (Selenium loops) where there is no `st` context.
#
# WHY A FILE LOCK (not st.session_state):
#   One `streamlit run main.py` serves every colleague. All sessions share this
#   one Python process and this one filesystem. A lock FILE is visible to every
#   session, so it is the correct place to serialize VM-wide.
# =============================================================================

import os
import json
import time
import platform

# --- Where the lock lives (project-local, next to this file) ---
_LOCK_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(_LOCK_DIR, "automation.lock")

# --- Tunables (safe defaults; change here if needed) ---------------------
# If the holder produces NO heartbeat for this many seconds, the run is
# considered HUNG and may be reclaimed by the next user. A healthy batch
# heartbeats every few seconds, so this never fires on real work.
HEARTBEAT_TIMEOUT_SECONDS = 8 * 60  # 8 minutes of SILENCE = hung

# Absolute hard ceiling as a last-resort backstop, in case heartbeats somehow
# keep firing but the run is stuck in a pathological loop. Generous on purpose
# (your longest real batch was ~14 min; leave big head-room for 1-hour jobs).
HARD_CEILING_SECONDS = 90 * 60  # 90 minutes absolute maximum


# =============================================================================
# PROCESS LIVENESS HELPERS (no external deps)
# =============================================================================
def _pid_alive(pid):
    """Return True if a process with this PID currently exists."""
    if not pid:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False

    if platform.system() == "Windows":
        # tasklist is available everywhere on Windows Server
        import subprocess
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5
            )
            return str(pid) in out.stdout
        except Exception:
            # If we cannot tell, assume alive (safer: don't kill blindly)
            return True
    else:
        # macOS / Linux
        try:
            os.kill(pid, 0)  # signal 0 = existence check, does not kill
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # exists but owned by someone else
        except Exception:
            return True


def kill_driver_pid(driver_pid):
    """
    Kill ONE specific msedgedriver process tree by PID.
    This is the SAFE, targeted kill — it never touches other users' drivers.
    (Contrast with the blanket taskkill /IM which kills everyone's driver.)
    """
    if not driver_pid:
        return
    try:
        driver_pid = int(driver_pid)
    except (TypeError, ValueError):
        return

    import subprocess
    try:
        if platform.system() == "Windows":
            # /T also kills child msedge.exe processes spawned by this driver
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(driver_pid)],
                capture_output=True, timeout=10
            )
        else:
            subprocess.run(
                ["pkill", "-TERM", "-P", str(driver_pid)],
                capture_output=True, timeout=10
            )
            try:
                os.kill(driver_pid, 15)
            except Exception:
                pass
    except Exception:
        pass  # best-effort


# =============================================================================
# LOCK FILE READ / WRITE
# =============================================================================
def _read_lock():
    """Return the lock dict, or None if no lock file / unreadable."""
    if not os.path.exists(LOCK_PATH):
        return None
    try:
        with open(LOCK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Corrupt/half-written lock → treat as absent (will be reclaimed)
        return None


def _write_lock(data):
    """Atomically write the lock dict."""
    tmp = LOCK_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, LOCK_PATH)  # atomic on same filesystem


def _delete_lock():
    """Remove the lock file if present."""
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except Exception:
        pass


# =============================================================================
# STALENESS LOGIC
# =============================================================================
def _lock_is_stale(lock):
    """
    Decide whether an existing lock is ABANDONED and may be reclaimed.

    A lock is stale if ANY of:
      1. The holder Python PID is no longer alive (process crashed / .bat killed)
      2. No heartbeat for HEARTBEAT_TIMEOUT_SECONDS (run is hung)
      3. It has existed beyond HARD_CEILING_SECONDS (pathological backstop)

    Returns (is_stale: bool, reason: str)
    """
    now = time.time()

    holder_pid = lock.get("holder_pid")
    if not _pid_alive(holder_pid):
        return True, "holder_process_dead"

    last_hb = lock.get("last_heartbeat", lock.get("started_at", 0))
    if now - last_hb > HEARTBEAT_TIMEOUT_SECONDS:
        return True, "heartbeat_timeout"

    started = lock.get("started_at", now)
    if now - started > HARD_CEILING_SECONDS:
        return True, "hard_ceiling"

    return False, ""


# =============================================================================
# PUBLIC API
# =============================================================================
def try_acquire(username, operation="Automazione"):
    """
    Attempt to acquire the VM-global automation lock.

    Returns (acquired: bool, info: dict)
      - acquired=True  → caller may proceed to open the browser. `info` holds
                         the fresh lock (including our holder_pid).
      - acquired=False → someone else holds a LIVE lock. `info` describes the
                         current holder for the busy page (username, operation,
                         started_at, last_heartbeat, seconds_since_heartbeat).

    Self-healing: if the existing lock is stale, we reclaim it here, killing
    the orphaned driver by its recorded PID first.
    """
    existing = _read_lock()

    if existing is not None:
        stale, reason = _lock_is_stale(existing)
        if not stale:
            # Someone is legitimately running. Report holder for the busy page.
            now = time.time()
            info = dict(existing)
            info["seconds_since_heartbeat"] = int(
                now - existing.get("last_heartbeat",
                                   existing.get("started_at", now))
            )
            info["seconds_running"] = int(
                now - existing.get("started_at", now)
            )
            return False, info
        else:
            # Stale lock → reclaim. Kill the orphaned driver (targeted, by PID).
            orphan_driver_pid = existing.get("driver_pid")
            if orphan_driver_pid:
                kill_driver_pid(orphan_driver_pid)
            _delete_lock()
            # fall through to acquire

    # Acquire fresh
    now = time.time()
    lock = {
        "holder_pid": os.getpid(),   # the Streamlit interpreter PID
        "driver_pid": None,          # set later via set_driver_pid()
        "username": username or "sconosciuto",
        "operation": operation,
        "step": "avvio…",
        "started_at": now,
        "last_heartbeat": now,
    }
    _write_lock(lock)
    return True, lock


def set_driver_pid(driver_pid):
    """
    Record the msedgedriver PID into the lock, so that if THIS run later
    hangs/crashes, the next user can kill exactly this driver.
    Call right after the browser is created.
    """
    lock = _read_lock()
    if lock is None:
        return
    lock["driver_pid"] = driver_pid
    lock["last_heartbeat"] = time.time()
    try:
        _write_lock(lock)
    except Exception:
        pass


def heartbeat(step=None):
    """
    Mark progress. Call this frequently from BOTH:
      - view.update_progress() (milestones), AND
      - model.py batch loops (per student / per edition / per activity)
    so a long healthy batch keeps proving it is alive.

    `step` (optional) updates the human-readable step shown on the busy page.
    This is a cheap local file write; safe to call very often.
    """
    lock = _read_lock()
    if lock is None:
        return
    lock["last_heartbeat"] = time.time()
    if step:
        lock["step"] = str(step)[:120]
    try:
        _write_lock(lock)
    except Exception:
        pass


def release(expected_holder_pid=None):
    """
    Release the lock at the end of a run.

    If expected_holder_pid is given, only release if WE are still the holder
    (prevents a just-reclaimed lock belonging to a new run from being deleted
    by a late finally-block of the old run).
    """
    lock = _read_lock()
    if lock is None:
        return
    if expected_holder_pid is not None:
        if lock.get("holder_pid") != expected_holder_pid:
            # We are no longer the holder (someone reclaimed). Do not delete.
            return
    _delete_lock()


def current_holder():
    """
    Return holder info for the busy page, or None if the VM is free.
    Also transparently reports staleness so the waiting page can say
    'automazione bloccata, verrà liberata a breve'.
    """
    lock = _read_lock()
    if lock is None:
        return None
    now = time.time()
    stale, reason = _lock_is_stale(lock)
    return {
        "username": lock.get("username", "sconosciuto"),
        "operation": lock.get("operation", "Automazione"),
        "step": lock.get("step", ""),
        "seconds_running": int(now - lock.get("started_at", now)),
        "seconds_since_heartbeat": int(
            now - lock.get("last_heartbeat", lock.get("started_at", now))
        ),
        "is_stale": stale,
        "stale_reason": reason,
    }


def startup_clean_slate():
    """
    Called ONCE at interpreter startup (from main.py).
    If a lock file survived a crash/restart AND its holder is dead, remove it
    and kill its orphaned driver. This is the safe replacement for the old
    'blanket taskkill at startup'. We still keep an optional blanket sweep in
    main.py guarded to run only when there is NO live holder.
    """
    lock = _read_lock()
    if lock is None:
        return
    stale, _ = _lock_is_stale(lock)
    if stale:
        orphan = lock.get("driver_pid")
        if orphan:
            kill_driver_pid(orphan)
        _delete_lock()
