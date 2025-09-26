import streamlit as st
from datetime import datetime

class CourseView:
    def __init__(self):
        st.set_page_config(layout='centered')
        st.image("logo-agsm.jpg", width=200)  # Always at the top
        st.title("Automatore per la Gestione dei Corsi Oracle")

    def get_user_options(self):
        #toggle for headless mode
        headless = st.toggle ("Eseguire in modalità headless (nessuna finestra del browser)", value = False)

        #toggle for debug mode
        debug_mode = st.toggle("Abilitare la modalità debug (rallenta l'automazione)", value = False)

        #slider for pause time *if debug mode is on
        debug_pause=st.slider("Durata della pausa di debug (secondi)",1,3,5)

        return headless, debug_mode, debug_pause



    def render_form(self):
        # This method displays the input form and returns the collected data.
        st.header("Inserisci Dettagli del Corso")

        # We use a Streamlit form to group the inputs.
        # The code inside 'with form:' will only run when the submit button is pressed.
        with st.form(key='course_creation_form'):
            # These are the input fields for the user.
            course_title = st.text_input("Titolo del Corso", "Esempio: Analisi dei Dati")
            programme = st.text_area("Dettagli del Programma", "Campo opzionale: se necessario, inserire informazioni importanti sul corso")
            short_desc = st.text_input("Breve Descrizione", "Esempio: Analisi dei Dati Informatica")
            #start_date = st.date_input("Data di Pubblicazione", date(2023, 1, 1))

            # Custom date input in Italian format
            date_str = st.text_input("Data di Pubblicazione (GG/MM/AAAA)", "01/01/2023")

            try:
                start_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                #st.success(f"📅 Data selezionata: {start_date.strftime('%d/%m/%Y')}")
            except ValueError:
                st.error("Formato non valido. Usa GG/MM/AAAA.")

            # This is the button that will trigger the automation.
            submitted = st.form_submit_button("Crea Corso in Oracle")

        #when the button is pressed,'submitted' becomes True
        if submitted:
            #package the ollected data into a dict
            course_details = {
                "title": course_title,
                "programme": programme,
                "short_description": short_desc,
                "start_date": start_date
            }
            st.session_state["course_details"] = course_details
            return course_details

        #if the button has not been pressed,return None
        return None

    def display_message(self,message):
        #this method show a message to the user-->Presenter call this method to provide feedback
        if not message:
            return

        if 'Success' in message:
            st.success(message)
        elif 'Error' in message:
            st.error(message)
        else:
            st.info(message)

#view=CourseView()
#view.render_form()#call the method that renders the form