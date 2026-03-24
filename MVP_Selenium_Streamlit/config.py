# =============================================================================
# config.py
# =============================================================================
# This file contains ALL XPaths used to interact with Oracle.
# If Oracle updates their interface and something stops working,
# ONLY change the XPath strings in this file.
# Do NOT touch model.py
#
# HOW TO FIND A NEW XPATH:
# 1. Open Oracle in Edge browser
# 2. Right-click on the element that broke
# 3. Click "Inspect"
# 4. Right-click the highlighted code → Copy → Copy XPath
# 5. Paste the new XPath here replacing the old one
# =============================================================================


# =============================================================================
# LOGIN PAGE
# ⚠️ IF LOGIN BREAKS: Update these 3 lines first
# =============================================================================
LOGIN_USERNAME_INPUT     = '//*[@id="idcs-signin-basic-signin-form-username|input"]'
LOGIN_USERNAME_FALLBACK_1 = '//input[contains(@id, "signin-form-username")]'
LOGIN_USERNAME_FALLBACK_2 = '//input[@type="text" and contains(@class, "oj-inputtext-input")]'

LOGIN_PASSWORD_INPUT     = '//*[@id="idcs-signin-basic-signin-form-password|input"]'
LOGIN_PASSWORD_FALLBACK_1 = '//input[contains(@id, "signin-form-password")]'
LOGIN_PASSWORD_FALLBACK_2 = '//input[@type="password" and contains(@class, "oj-inputpassword-input")]'

LOGIN_SUBMIT_BUTTON      = '//*[@id="idcs-signin-basic-signin-form-submit"]//button'
LOGIN_SUBMIT_FALLBACK_1  = '//button[contains(@id, "signin-form-submit")]'
LOGIN_SUBMIT_FALLBACK_2  = '//button[.//span[text()="Next"]]'
LOGIN_SUBMIT_FALLBACK_3  = '//button[@type="submit"]'


# =============================================================================
# MAIN NAVIGATION
# =============================================================================
NAV_NEW_HOMEPAGE_BUTTON = '//*[@id="pt1:commandLink1"]'
NAV_WORKFORCE_MENU  = '//*[@id="groupNode_workforce_management"]'
NAV_LEARN_ADMIN     = 'WLF_FUSE_LEARN_ADMIN'           # used with By.ID
NAV_CORSI_LINK      = '//a[@title="Corsi" and text()="Corsi"]'
NAV_EDIZIONI_LINK   = '//a[@title="Edizioni" and text()="Edizioni"]'


# =============================================================================
# COURSES PAGE - SEARCH
# =============================================================================
COURSE_SEARCH_NAME_INPUT = 'pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value00'  # used with By.NAME
COURSE_SEARCH_DATE_INPUT = '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2:value10::content"]'
COURSE_SEARCH_BUTTON     = '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:1:MgCrUpl:UPsp1:r2:0:crsQry2::search"]'
COURSE_NO_DATA_MESSAGE   = '//*[contains(text(),"Nessun dato da visualizzare.")]'
COURSE_TABLE_SUMMARY     = 'Corsi'                      # used in //table[@summary='Corsi']


# =============================================================================
# COURSES PAGE - CREATE
# =============================================================================
COURSE_CREATE_BUTTON_EN  = "//a[.//span[text()='Create']]"
COURSE_CREATE_BUTTON_IT  = "//a[.//span[text()='Crea']]"
COURSE_CREATE_BUTTON_ID  = "//a[contains(@id, 'crtBtn')]"
COURSE_TITLE_INPUT       = '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:ttlInp::content"]'
COURSE_PROGRAMME_INPUT   = '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:slbsRte::_cic"]/div[1]/div[2]/div'
COURSE_SHORT_DESC_INPUT  = '//input[contains(@id, ":MAnt2:2:lsVwCrs:shdsInp::content")]'
COURSE_DATE_INPUT        = '//input[contains(@id, ":MAnt2:2:lsVwCrs:sdDt::content")]'
COURSE_SAVE_CLOSE_BUTTON = '//*[@id="pt1:_FOr1:1:_FONSr2:0:MAnt2:2:lsVwCrs:svcBtn"]'


# =============================================================================
# COURSE DETAIL PAGE
# =============================================================================
COURSE_DETAIL_EDIZIONI_TAB = '//div[contains(@id, ":lsCrDtl:UPsp1:classTile::text")]'


# =============================================================================
# EDITION PAGE - CREATE
# =============================================================================
EDITION_CREA_BUTTON          = "//a[text()='Crea']"
EDITION_GUIDATA_OPTION       = "//td[text()='Edizione guidata da docente']"
EDITION_TITLE_INPUT          = '//input[contains(@id, ":lsVwCls:ttlInp::content")]'
EDITION_DESCRIPTION_INPUT    = '//div[contains(@aria-label, "main") and @role="textbox"]'
EDITION_PUB_START_DATE_INPUT = '//input[contains(@id, ":lsVwCls:sdDt::content")]'
EDITION_PUB_END_DATE_INPUT   = '//input[contains(@id,"lsVwCls:edDt::content")]'
EDITION_START_DATE_INPUT     = '//input[contains(@id, ":lsVwCls:liSdDt::content")]'
EDITION_END_DATE_INPUT       = "//input[contains(@id, ':lsVwCls:liEdDt::content')]"
EDITION_SAVE_CLOSE_BUTTON    = "//button[text()='Salva e chiudi']"


# =============================================================================
# EDITION PAGE - LOCATION (AULA)
# =============================================================================
EDITION_AULA_LOV_ICON      = '//*[contains(@id, "primaryClassroomName1Id::lovIconId")]'
EDITION_AULA_SEARCH_LINK_1 = "//a[contains(@id, 'primaryClassroomName1Id') and contains(@id, 'popupsearch')]"
EDITION_AULA_SEARCH_LINK_2 = "//a[text()='Cerca...']"
EDITION_AULA_SEARCH_LINK_3 = "//a[text()='Search...']"
EDITION_AULA_KEYWORD_INPUT = '//input[contains(@id, "primaryClassroomName1Id::_afrLovInternalQueryId:value00::content")]'
EDITION_AULA_SEARCH_BTN_1  = "//button[contains(@id, 'primaryClassroomName1Id') and contains(@id, '::search')]"
EDITION_AULA_SEARCH_BTN_2  = "//button[contains(@id, 'primaryClassroomName1Id') and text()='Cerca']"
EDITION_AULA_SEARCH_BTN_3  = "//button[contains(@id, 'primaryClassroomName1Id') and text()='Search']"
EDITION_AULA_RESULTS_TABLE = '//div[contains(@id, "primaryClassroomName1Id_afrLovInternalTableId::db")]'
EDITION_AULA_OK_BUTTON     = "//button[text()='OK' and contains(@id, 'primaryClassroomName1Id')]"


# =============================================================================
# EDITION PAGE - LANGUAGE
# =============================================================================
EDITION_LANGUAGE_DROPDOWN = "//a[contains(@id, ':lsVwCls:lngSel::drop')]"
EDITION_LANGUAGE_DEFAULT  = "Italiana"


# =============================================================================
# EDITION PAGE - SUPPLIER
# =============================================================================
EDITION_MODERATOR_DROPDOWN     = "//a[contains(@id, ':lsVwCls:socFaciType::drop')]"
EDITION_MODERATOR_TYPE         = 'Fornitore formazione'
EDITION_SUPPLIER_LOV_ICON      = "//a[contains(@id, ':lsVwCls:supplierNameId::lovIconId')]"
EDITION_SUPPLIER_SEARCH_LINK_1 = "//a[contains(@id, 'supplierNameId') and contains(@id, 'popupsearch')]"
EDITION_SUPPLIER_SEARCH_LINK_2 = "//a[text()='Cerca...']"
EDITION_SUPPLIER_SEARCH_LINK_3 = "//a[text()='Search...']"
EDITION_SUPPLIER_INPUT         = "//input[contains(@id, 'supplierNameId') and contains(@id, 'value00::content')]"
EDITION_SUPPLIER_SEARCH_BTN_1  = "//button[contains(@id, 'supplierNameId') and contains(@id, '::search')]"
EDITION_SUPPLIER_SEARCH_BTN_2  = "//button[contains(@id, 'supplierNameId') and text()='Cerca']"
EDITION_SUPPLIER_SEARCH_BTN_3  = "//button[contains(@id, 'supplierNameId') and text()='Search']"
EDITION_SUPPLIER_RESULTS_TABLE = '//div[contains(@id, "supplierNameId_afrLovInternalTableId::db")]'
EDITION_SUPPLIER_OK_BTN_1      = "//button[contains(@id, 'supplierNameId') and text()='OK']"
EDITION_SUPPLIER_OK_BTN_2      = "//button[text()='OK' and contains(@id, 'supplierNameId')]"


# =============================================================================
# EDITION PAGE - PRICE
# =============================================================================
EDITION_PRICE_FLAG_LABEL    = '//label[text()="Override determinazione prezzi"]'
EDITION_PRICE_ADD_LINE_BTN  = "//img[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:addBtn::icon')]"
EDITION_PRICE_LINE_DROPDOWN = "//a[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:t1:0:soc2::drop')]"
EDITION_PRICE_LISTINO_OPTION = '//*[contains(text(),"Prezzo di listino")]'
EDITION_PRICE_COST_INPUT    = "//input[contains(@id, ':lsVwCls:rPrc:0:srAtbl:_ATp:t1:0:it1::content')]"

# =============================================================================
# EDITION SEARCH RESULTS - DATE EXTRACTION (from search results row)
# =============================================================================
EDITION_RESULT_ROW           = "//a[contains(@id, ':_ATp:srTbl:') and contains(@id, ':clnmLnk')]/ancestor::tr"
EDITION_RESULT_PUB_START     = ".//*[contains(@id, ':sdDt::content')]"
EDITION_RESULT_PUB_END       = ".//*[contains(@id, ':edDt::content')]"
EDITION_RESULT_DATE_SPAN     = ".//td[contains(@class,'xen')]//span[contains(@class,'x2ey')]"

# =============================================================================
# ACTIVITY - CREATE (POPUP)
# =============================================================================
ACTIVITY_ADD_BUTTON_1       = "//div[contains(@id, ':actPce:iltBtn') and @title='Aggiungi']"
ACTIVITY_ADD_BUTTON_2       = "//div[@title='Aggiungi' and contains(@id, 'actPce')]"
ACTIVITY_ADD_BUTTON_3       = "//div[@title='Aggiungi']"
ACTIVITY_TITLE_INPUT        = '//input[@aria-label="Titolo"]'
ACTIVITY_DESC_ELENCO_INPUT  = '//input[@aria-label="Descrizione per elenco"]'
ACTIVITY_DESC_DETAIL_CK_1   = '//div[contains(@aria-label, "Editor editing area: main") and @contenteditable="true"]'
ACTIVITY_DESC_DETAIL_CK_2   = '//div[contains(@class, "ck-editor__editable") and @contenteditable="true"]'
ACTIVITY_DESC_DETAIL_CK_3   = '//div[contains(@class, "ck-content") and @contenteditable="true"]'
ACTIVITY_DATE_INPUT         = '//input[@aria-label="Data attività"]'
ACTIVITY_START_TIME_INPUT   = '//input[@aria-label="Ora inizio"]'
ACTIVITY_END_TIME_INPUT     = '//input[@aria-label="Ora fine"]'
ACTIVITY_HOURS_INPUT        = '//input[@aria-label="Impegno previsto in ore"]'
ACTIVITY_OK_BUTTON_1        = '//div[contains(@class, "AFHeaderArea")]//a[.//span[text()="OK"]]'
ACTIVITY_OK_BUTTON_2        = '//div[contains(@class, "popup")]//a[.//span[text()="OK"]]'
ACTIVITY_OK_BUTTON_3        = '//a[@role="button"][.//span[text()="OK"]]'
ACTIVITY_CANCEL_BTN_1       = '//a[@role="button"][.//span[text()="Annulla"]]'
ACTIVITY_CANCEL_BTN_2       = '//span[text()="Annulla"]/parent::a'


# =============================================================================
# EDITION SEARCH PAGE
# =============================================================================
EDITION_SEARCH_OPERATOR_DROP  = "//*[contains(@id, ':operator6::drop')]"
EDITION_SEARCH_OPERATOR_OPT   = "//*[contains(@id, ':operator6::pop')]/li[3]"
EDITION_SEARCH_NUMBER_INPUT_1 = '//*[contains(@id, ":value60::content")]'
EDITION_SEARCH_NUMBER_INPUT_2 = '//*[@aria-label=" Numero edizione"]'
EDITION_SEARCH_DATE_FILTER    = "//*[contains(@id,':value20::content')]"
EDITION_SEARCH_SUBMIT_BTN     = "//button[text()='Cerca' or text()='Search']"
EDITION_SEARCH_RESULT_LINK    = "//a[contains(@id, ':_ATp:srTbl:') and contains(@id, ':clnmLnk')]"
EDITION_DETAIL_CONFIRM_1      = "//a[contains(text(), 'Allievi')]"
EDITION_DETAIL_CONFIRM_2      = "//span[contains(text(), 'Allievi')]"
EDITION_DETAIL_CONFIRM_3      = "//div[contains(@id, 'learnerTile')]"
EDITION_BACK_BTN_TO_SEARCH_1  = "//svg[@id='pt1:_FOr1:1:_FONSr2:0:MAnt2:2:clDtSp1:UPsp1:SPdonei::icon']/parent::a"
EDITION_BACK_BTN_TO_SEARCH_2  = "//a[contains(@id, 'clDtSp1:UPsp1:SPdonei')]"
EDITION_BACK_BTN_TO_SEARCH_3  = "//*[contains(@id, 'clDtSp1:UPsp1:SPdonei::icon')]"


# =============================================================================
# STUDENTS - ADD (ALLIEVI TAB)
# =============================================================================
STUDENT_ALLIEVI_TAB         = "//div[contains(@id, ':clDtSp1:UPsp1:learnerTile::text')]"
STUDENT_ADD_ALLIEVI_BUTTON  = "//a[normalize-space()='Aggiungi allievi']"
STUDENT_ASSEGNAZIONE_OBB_1  = "//*[contains(@id, 'requireCmi')]/td[2]"
STUDENT_ASSEGNAZIONE_OBB_2  = "//td[contains(@class, 'xo2') and normalize-space()='Assegnazione obbligatoria']"
STUDENT_TEAM_DROPDOWN       = '//input[contains(@id, ":clDtSp1:UPsp1:r11:1:r5:0:SP2:r1:0:soc2::content")]'
STUDENT_TEAM_NAME           = "Team Organizzazione & Sviluppo"
STUDENT_NOTA_FIELD_1        = "//*[@id='pt1:_FOr1:1:_FONSr2:0:MAnt2:2:clDtSp1:UPsp1:r11:1:r5:0:SP2:r1:0:it1::content']"
STUDENT_NOTA_FIELD_2        = "//textarea[contains(@id, ':r5:0:SP2:r1:0:it1::content')]"
STUDENT_SCADENZA_FIELD_1    = "//*[@id='pt1:_FOr1:1:_FONSr2:0:MAnt2:2:clDtSp1:UPsp1:r11:1:r5:0:SP2:r1:0:id1::content']"
STUDENT_SCADENZA_FIELD_2    = "//input[contains(@id, ':r5:0:SP2:r1:0:id1::content')]"
STUDENT_SUCCESSIVO_BUTTON   = '//button[text()="Successivo"]'
STUDENT_AGGIUNGI_DROPDOWN_1 = "//*[contains(@id, 'pc1:menuButton')]//a[@role='button']"
STUDENT_ELENCO_OPTION_1     = "//*[contains(@id, 'pc1:cmi1')]//td[normalize-space()='Elenco numeri persona']"
STUDENT_NOME_FIELD_1        = "//input[contains(@id, ':pt1:it2::content')]"
STUDENT_NOME_FIELD_2        = "//*[contains(@id, 'pt1:it2::content')]"
STUDENT_PLUS_BUTTON         = "//div[contains(@id, 'applicationsTable:_ATp:create')]//a[@role='button']"
STUDENT_FILE_INPUT          = "//input[contains(@id, 'attachmentTable:0:desktopFile::content')]"
STUDENT_OK_BUTTON           = "//button[contains(@id, ':pt1:d3::ok')]"
STUDENT_NEXT_BUTTON         = "//button[text()='Successivo']"
STUDENT_SUBMIT_BUTTON       = "//button[text()='Sottometti']"
STUDENT_CONFIRM_DIALOG_OK   = "//button[contains(@id,':1:cfmDlg::ok')]"


# =============================================================================
# STUDENTS - VERIFY
# =============================================================================
STUDENT_STATUS_DROPDOWN  = "//span[contains(@class, 'x1kn')]/a[contains(@id, ':lrasQry:value20::drop')]"
STUDENT_STATUS_TUTTO     = '//*[contains(text(),"Tutto")]'
STUDENT_KEYWORD_INPUT_1  = "//input[contains(@id, 'lrasQry:value10::content')]"
STUDENT_KEYWORD_INPUT_2  = "//input[contains(@id, ':value10::content')]"
STUDENT_CERCA_BUTTON     = "//button[text()='Cerca' or text()='Search']"
STUDENT_RESET_BUTTON     = "//button[text()='Reimposta' or text()='Reset']"


# =============================================================================
# BACK NAVIGATION
# =============================================================================
BACK_FROM_COURSE_DETAIL      = "//a[contains(@id, 'SPdonei')]"
BACK_FROM_EDITION_TO_COURSE  = '//*[contains(@id, "lsCrDtl:UPsp1:SPdonei::icon")]/parent::a'
BACK_FROM_ACTIVITY_TO_EDITION = '//*[contains(@id, "clDtSp1:UPsp1:SPdonei::icon")]/parent::a'