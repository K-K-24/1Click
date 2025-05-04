# config/settings.py

# --- OpenAI Settings ---
OPENAI_API_KEY = "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"

# You can switch between "gpt-3.5-turbo" or "gpt-4o" easily
OPENAI_MODEL = "gpt-3.5-turbo"

# --- WebDriver Settings ---
# Path to your EdgeDriver (change accordingly)
EDGE_DRIVER_PATH = r"C:\Users\I751179\Edgedriver\msedgedriver.exe"

# --- Outlook Email Settings ---
OUTLOOK_EMAIL_SUBJECT_FILTER = "SAP Help Portal: Comment Notification"

# --- SAP Help Portal Base URL ---
SAP_HELP_PORTAL_BASE_URL = "https://help.sap.com/"

# --- Smart Waits (in seconds) ---
WAIT_TIME_PAGE_LOAD = 120     # For Help Portal full load
WAIT_TIME_CCMS_WEB_LOAD = 45   # For IXIASOFT Web Editor load
WAIT_TIME_EDIT_MODE = 20       # For edit mode activation
WAIT_TIME_XML_VIEW_LOAD = 6    # For XML view loading
