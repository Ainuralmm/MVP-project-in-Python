import sys
import streamlit as st
from model import OracleAutomator
from view import CourseView
from presenter import CoursePresenter

import logging
import os
import builtins
from datetime import datetime
import automation_lock  # VM-global one-at-a-time lock + heartbeat + reaper

# ══════════════════════════════════════════════════════════════════════
# LOG DIRECTORY SETUP
# ══════════════════════════════════════════════════════════════════════
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(
    log_dir, f"session_{datetime.now().strftime('%Y%m%d')}.log"
)

# Save the true original print once (survives Streamlit reruns)
if not hasattr(builtins, '_true_original_print'):
    builtins._true_original_print = builtins.print

# ══════════════════════════════════════════════════════════════════════
# LOGGER SETUP (reset on every rerun to prevent duplicate handlers)
# ══════════════════════════════════════════════════════════════════════
logger = logging.getLogger()
logger.setLevel(logging.INFO)

for handler in logger.handlers[:]:
    logger.removeHandler(handler)
    handler.close()


class UserContextFilter(logging.Filter):
    """
    Injects the current logged-in Oracle user into every log record.
    Required by Sistemi Informativi for audit/traceability.
    """
    def filter(self, record):
        try:
            import streamlit as st
            record.user = st.session_state.get('oracle_username', 'NO_USER')
        except Exception:
            record.user = 'SYSTEM'
        return True


formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | user=%(user)s | %(message)s'
)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.addFilter(UserContextFilter())
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.addFilter(UserContextFilter())
logger.addHandler(stream_handler)


def _logging_print(*args, **kwargs):
    message = ' '.join(str(a) for a in args)
    logging.info(message)
    builtins._true_original_print(*args, **kwargs)


builtins.print = _logging_print


# ══════════════════════════════════════════════════════════════════════
# ORPHAN BROWSER CLEANUP (kills zombies from previous crashed runs)
# Runs ONCE per Python interpreter startup, not per Streamlit rerun.
# ══════════════════════════════════════════════════════════════════════
def cleanup_orphan_drivers():
    """Kill any leftover msedgedriver.exe processes from crashed runs."""
    import subprocess
    import platform
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/IM", "msedgedriver.exe", "/T"],
                capture_output=True, timeout=5
            )
        else:  # macOS / Linux
            subprocess.run(
                ["pkill", "-f", "msedgedriver"],
                capture_output=True, timeout=5
            )
    except Exception:
        pass  # Best effort, not critical


if not hasattr(builtins, '_orphan_cleanup_done'):
    cleanup_orphan_drivers()
    automation_lock.startup_clean_slate()
    if automation_lock.current_holder() is None:
        cleanup_orphan_drivers()
    builtins._orphan_cleanup_done = True


# ══════════════════════════════════════════════════════════════════════
# MAIN APP ENTRY POINT
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Read DRIVER_PATH from secrets.toml (works on Mac AND Windows)
    # secrets.toml must have EDGE_DRIVER_PATH set correctly per machine
    try:
        DRIVER_PATH = st.secrets['EDGE_DRIVER_PATH']
    except Exception:
        st.error(
            "❌ EDGE_DRIVER_PATH mancante in secrets.toml.\n\n"
            "Aggiungi al file `.streamlit/secrets.toml`:\n"
            '`EDGE_DRIVER_PATH = "path/to/msedgedriver"`'
        )
        st.stop()

    # 1. Initialize the View
    view = CourseView()

    # 2. AUTH GATE — show login screen until user is authenticated
    if not view._render_login_screen():
        st.stop()

    headless, debug_mode, debug_pause = view.get_user_options()

    # 3. Get current state BEFORE rendering UI
    current_state = st.session_state.get('app_state', 'IDLE')

    # 3.5 Reset stale automation guard when state is IDLE.
    # The presenter resets app_state but not this guard, so clear it here
    # to allow the user to start a NEW automation after one completes.
    if current_state == "IDLE":
        st.session_state.automation_in_progress = False

    # 4. Render the UI
    view.render_ui()

    # 4.5 Display any error message from a previous crashed run (top-level, NOT nested)
    if st.session_state.get('CRITICAL_ERROR_MSG'):
        st.error(st.session_state.CRITICAL_ERROR_MSG)
        st.session_state.CRITICAL_ERROR_MSG = None

    # ══════════════════════════════════════════════════════════════════
    # 5. CONTROLLER LOGIC — TOP LEVEL, NOT NESTED INSIDE ANYTHING
    # This runs ONLY when the user has triggered an automation.
    # Wrapped in try/except to guarantee state recovery on any failure.
    # ══════════════════════════════════════════════════════════════════
    _op_labels = {
        "RUNNING_COURSE": "Creazione Corso",
        "RUNNING_BATCH_COURSE": "Creazione Corsi (batch)",
        "RUNNING_EDITION": "Creazione Edizione + Attività",
        "RUNNING_BATCH_EDITION": "Creazione Edizioni (batch)",
        "RUNNING_STUDENTS": "Aggiunta Allievi",
        "RUNNING_BATCH_STUDENTS": "Aggiunta Allievi (batch)",
        "RUNNING_VERIFY_STUDENTS": "Verifica Allievi",
        "RUNNING_PRESENZA": "Assegnazione Presenza",
        "RUNNING_BATCH_PRESENZA": "Assegnazione Presenza (batch)",
    }



    # ── LAUNCH STATE: user explicitly clicked an operation button. ──
    if current_state != "IDLE":
        username = st.session_state.get("oracle_username", "sconosciuto")
        operation_label = _op_labels.get(st.session_state.app_state, "Automazione")

        # ── Try to acquire the VM-GLOBAL lock (across ALL sessions) ──
        acquired, holder = automation_lock.try_acquire(username, operation_label)

        if not acquired:
            # Server busy → stop quietly with a small note. Keep it simple:
            # one user at a time. (If this is a stale lock from a dead run,
            # delete automation.lock on the server, or wait for the 8-min
            # auto-reclaim.)
            st.info(
                "⏳ Server occupato — un'altra operazione è in corso. "
                "Riprova tra qualche minuto. Usare l'automatore una persona "
                "alla volta."
            )
            st.session_state.app_state = "IDLE"
            st.session_state.automation_in_progress = False
            st.stop()

        my_holder_pid = holder["holder_pid"]

        model = None
        try:
            st.session_state.automation_in_progress = True

            # If a PREVIOUS run in this session was abandoned by a Streamlit
            # rerun, its driver may still be alive. Kill it by the PID we
            # recorded, so we never stack browsers.
            try:
                prev_pid = st.session_state.get("last_driver_pid")
                if prev_pid:
                    automation_lock.kill_driver_pid(prev_pid)
                    st.session_state.last_driver_pid = None
            except Exception:
                pass

            model  = OracleAutomator(
                driver_path=DRIVER_PATH,
                debug_mode=debug_mode,
                debug_pause=debug_pause,
                headless=headless
            )

            try:
                driver_pid = model.driver.service.process.pid
                automation_lock.set_driver_pid(driver_pid)
                st.session_state.last_driver_pid = driver_pid  # for self-cleanup
            except Exception:
                pass  # non-fatal; heartbeat/holder-death still protect us

            presenter = CoursePresenter(model, view)

            # ─────────── DISPATCH (unchanged from your code) ───────────
            if st.session_state.app_state == "RUNNING_COURSE":
                presenter.run_create_course(st.session_state.get("course_details"))
            elif st.session_state.app_state == "RUNNING_BATCH_COURSE":
                presenter.run_create_batch_courses(st.session_state.get("batch_course_data"))
            elif st.session_state.app_state == "RUNNING_EDITION":
                presenter.run_create_edition_and_activities(st.session_state.get("edition_details"))
            elif st.session_state.app_state == "RUNNING_BATCH_EDITION":
                presenter.run_batch_edition_creation()
            elif st.session_state.app_state == "RUNNING_STUDENTS":
                presenter.run_add_students(st.session_state.get("student_details"))
            elif st.session_state.app_state == "RUNNING_BATCH_STUDENTS":
                presenter.run_add_students_batch()
            elif st.session_state.app_state == "RUNNING_VERIFY_STUDENTS":
                presenter.run_verify_students()
            elif st.session_state.app_state == "RUNNING_PRESENZA":
                presenter.run_assign_presenza()
            elif st.session_state.app_state == "RUNNING_BATCH_PRESENZA":
                presenter.run_assign_presenza_batch()
            # ───────────────────────────────────────────────────────────

            st.session_state.automation_in_progress = False

        except Exception as global_error:
            logging.error(f"GLOBAL CONTROLLER ERROR: {global_error}", exc_info=True)
            if model is not None:
                try:
                    model.close()
                except Exception:
                    pass
            st.session_state.app_state = "IDLE"
            st.session_state.automation_in_progress = False
            st.session_state.CRITICAL_ERROR_MSG = (
                f"❌ Si è verificato un errore imprevisto: {global_error}\n\n"
                f"L'app è stata ripristinata. Puoi riprovare l'operazione."
            )
            # release the lock we hold, then rerun
            try:
                automation_lock.release(expected_holder_pid=my_holder_pid)
            except Exception:
                pass
            st.rerun()

        finally:
            # SAFETY NET: normally the presenter releases the lock in ITS
            # finally (see presenter edits). But if the presenter somehow
            # returns without releasing, or dispatch matched nothing, we
            # release here too. release() is holder-checked, so this cannot
            # delete a lock that a newer run already took.
            try:
                automation_lock.release(expected_holder_pid=my_holder_pid)
            except Exception:
                pass