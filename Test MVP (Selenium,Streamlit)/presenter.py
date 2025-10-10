
class CoursePresenter:
    def __init__(self, model, view):
        # the presenter holds references to the model and the view
        self.model = model
        #self.view = view

        # HELPER: update progress via callback
    def _safe_call(self, cb, *args, **kwargs):
        try:
            if cb:
                cb(*args, **kwargs)
        except Exception as e:
            print("Presenter: callback error:", e)

    # =============================
    #  COURSE CREATION
    # =============================
    def run_create_course(self, course_details, secrets, progress_cb, status_cb, done_cb):
        # SECRETS is a dict with ORACLE_URL, ORACLE_USER, ORACLE_PASS
        try:
            self._safe_call(status_cb, "🔑 Accesso a Oracle in corso...", "course")
            self._safe_call(progress_cb, 10, "course")

            login_res = self.model.login(secrets["ORACLE_URL"], secrets["ORACLE_USER"], secrets["ORACLE_PASS"])
            if not login_res.get("ok"):
                self._safe_call(status_cb, f"❌ Login failed: {login_res.get('error')}", "course")
                return done_cb(login_res, "course")

            self._safe_call(status_cb, "🧭 Navigazione verso la pagina Corsi...", "course")
            self._safe_call(progress_cb, 30, "course")
            nav = self.model.navigate_to_courses_page()
            if not nav.get("ok"):
                self._safe_call(status_cb, f"❌ Navigation failed: {nav.get('error')}", "course")
                return done_cb(nav, "course")

            self._safe_call(status_cb, f"🔍 Ricerca corso '{course_details['title']}'...", "course")
            self._safe_call(progress_cb, 60, "course")
            search = self.model.search_course(course_details['title'])
            if not search.get("ok"):
                self._safe_call(status_cb, f"❌ Search failed: {search.get('error')}", "course")
                return done_cb(search, "course")
            if search.get("found"):
                msg = {"ok": True, "created": False, "message": f"‼️ Il corso '{course_details['title']}' esiste già."}
                self._safe_call(status_cb, msg["message"], "course")
                return done_cb(msg, "course")

            self._safe_call(status_cb, "📝 Creazione nuovo corso...", "course")
            self._safe_call(progress_cb, 75, "course")
            create_res = self.model.create_course(course_details)
            self._safe_call(progress_cb, 95, "course")
            self._safe_call(status_cb, create_res.get("message", "Done"), "course")
            return done_cb(create_res, "course")
        except Exception as e:
            err = {"ok": False, "error": "presenter_exception", "message": str(e)}
            self._safe_call(status_cb, f"⚠️ Errore inatteso: {e}", "course")
            return done_cb(err, "course")
        finally:
            try:
                self.model.close_driver()
            except:
                pass

    # RUN CREATE EDITION
    def run_create_edition(self, edition_details, secrets, progress_cb, status_cb, done_cb):
        try:
            self._safe_call(status_cb, "🔑 Accesso a Oracle in corso...", "edition")
            self._safe_call(progress_cb, 10, "edition")
            login_res = self.model.login(secrets["ORACLE_URL"], secrets["ORACLE_USER"], secrets["ORACLE_PASS"])
            if not login_res.get("ok"):
                self._safe_call(status_cb, f"❌ Login failed: {login_res.get('error')}", "edition")
                return done_cb(login_res, "edition")

            self._safe_call(status_cb, "🧭 Navigazione verso la pagina Corsi...", "edition")
            self._safe_call(progress_cb, 25, "edition")
            nav = self.model.navigate_to_courses_page()
            if not nav.get("ok"):
                self._safe_call(status_cb, f"❌ Navigation failed: {nav.get('error')}", "edition")
                return done_cb(nav, "edition")

            course_name = edition_details["course_name"]
            self._safe_call(status_cb, f"🔍 Ricerca corso '{course_name}'...", "edition")
            self._safe_call(progress_cb, 40, "edition")
            search = self.model.search_course(course_name)
            if not search.get("ok"):
                self._safe_call(status_cb, f"❌ Search failed: {search.get('error')}", "edition")
                return done_cb(search, "edition")
            if not search.get("found"):
                msg = {"ok": True, "found": False, "message": f"❌ Il corso '{course_name}' non esiste. Crealo prima."}
                self._safe_call(status_cb, msg["message"], "edition")
                return done_cb(msg, "edition")

            # open course in list
            self._safe_call(status_cb, f"📂 Apertura corso '{course_name}'...", "edition")
            self._safe_call(progress_cb, 55, "edition")
            open_res = self.model.open_course_from_list(course_name)
            if not open_res.get("ok"):
                self._safe_call(status_cb, "❌ Impossibile aprire il corso", "edition")
                return done_cb(open_res, "edition")

            # create edition
            self._safe_call(status_cb, "🧾 Creazione edizione...", "edition")
            self._safe_call(progress_cb, 70, "edition")
            create_res = self.model.create_edition(edition_details)
            if not create_res.get("ok"):
                self._safe_call(status_cb, f"❌ {create_res.get('message')}", "edition")
                return done_cb(create_res, "edition")

            self._safe_call(progress_cb, 100, "edition")
            self._safe_call(status_cb, create_res.get("message", "Edizione creata"), "edition")
            return done_cb(create_res, "edition")
        except Exception as e:
            err = {"ok": False, "error": "presenter_exception", "message": str(e)}
            self._safe_call(status_cb, f"⚠️ Errore inatteso: {e}", "edition")
            return done_cb(err, "edition")
        finally:
            try:
                self.model.close_driver()
            except:
                pass