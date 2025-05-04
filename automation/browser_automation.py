# automation/browser_automation.py

import json
from venv import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from config.settings import EDGE_DRIVER_PATH, WAIT_TIME_PAGE_LOAD
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import time
def launch_edge():
    """
    Launch Edge browser using Selenium WebDriver and return driver.
    """
    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")

    service = Service(executable_path=EDGE_DRIVER_PATH)
    driver = webdriver.Edge(service=service, options=options)

    return driver

def open_help_portal_page(driver, url):
    """
    Opens SAP Help Portal page in Edge browser.
    """
    driver.get(url)
    WebDriverWait(driver, WAIT_TIME_PAGE_LOAD).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    print("✅ SAP Help Portal page loaded.")

def get_page_title(driver):
    """
    Gets the page title using multiple strategies.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        str: The page title or browser title if not found
    """
    try:
        # Try several strategies to find the page title
        title_selectors = [
            {"type": "css", "selector": "div.left-content h1", "description": "left-content > h1"},
            {"type": "css", "selector": "h1", "description": "any h1"},
            {"type": "css", "selector": "div.breadcrumbs", "description": "breadcrumbs"},
            {"type": "css", "selector": ".page-title, .title", "description": "page-title or title class"}
        ]
        
        for strategy in title_selectors:
            try:
                if strategy["type"] == "css":
                    element = driver.find_element(By.CSS_SELECTOR, strategy["selector"])
                else:  # xpath
                    element = driver.find_element(By.XPATH, strategy["selector"])
                
                title_text = element.text.strip()
                if title_text:
                    print(f"✅ Found page title from {strategy['description']}: {title_text}")
                    return title_text
            except:
                continue
                
        # If all strategies fail, use the document title
        print("⚠️ Could not find page title element, falling back to browser title")
        return driver.title
            
    except Exception as e:
        print(f"⚠️ Error getting page title: {e}")
        return driver.title
    
    
def clean_title(title):
    """
    Cleans a title for comparison by removing common prefixes and standardizing format.
    
    Args:
        title: The title string to clean
        
    Returns:
        str: Cleaned title for comparison
    """
    if not title:
        return ""
        
    # Remove common SAP prefixes
    prefixes = ["SAP Help Portal:", "SAP:", "Login |", "Purpose |"]
    cleaned = title
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    # Normalize whitespace
    cleaned = " ".join(cleaned.split())
    
    # Remove trailing/leading special characters
    cleaned = cleaned.strip(" -|:,.")
    
    return cleaned.lower()

def titles_match(title1, title2):
    """
    Checks if two titles match, with some flexibility for minor differences.
    
    Args:
        title1: First title
        title2: Second title
        
    Returns:
        bool: True if titles match with reasonable confidence
    """
    # Check for exact match after cleaning
    if title1 == title2:
        return True
        
    # Check if one is a substring of the other (for partial titles)
    if title1 in title2 or title2 in title1:
        return True
    
    # Check for significant word overlap
    words1 = set(title1.split())
    words2 = set(title2.split())
    common_words = words1.intersection(words2)
    
    # If we have at least 3 common words or 70% overlap, consider it a match
    if len(common_words) >= 3:
        return True
    
    if len(common_words) > 0 and len(common_words) / max(len(words1), len(words2)) >= 0.7:
        return True
        
    return False

def handle_page_filters(driver):
    """
    When a title doesn't match, handle the filter dropdowns to ensure all content is visible.
    Uses "Select All" option to select all options at once.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Wait for filter elements to be present
        wait = WebDriverWait(driver, 15)
        
        # List of dropdowns to check
        dropdowns = [
            {"name": "Information Classification", "selector": "//button[@title='Information Classification']"},
            {"name": "Features", "selector": "//button[@title='Features']"},
            {"name": "Implementation", "selector": "//button[@title='Implementation']"}
        ]
        
        for dropdown in dropdowns:
            try:
                print(f"Processing {dropdown['name']} dropdown...")
                
                # Find and click the dropdown button
                try:
                    dropdown_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, dropdown["selector"]))
                    )
                    dropdown_button.click()
                    print(f"  ✅ Clicked {dropdown['name']} dropdown")
                    time.sleep(1)  # Wait for dropdown to open
                except Exception as e:
                    print(f"  ⚠️ Could not click {dropdown['name']} dropdown: {e}")
                    continue
                
                # Look for "Select All" option
                try:
                    # Try several methods to find the Select All option
                    select_all = None
                    
                    # Method 1: Direct text match
                    try:
                        select_all = driver.find_element(By.XPATH, "//li/button[text()='Select All']")
                    except:
                        # Method 2: Partial text match
                        try:
                            select_all = driver.find_element(By.XPATH, "//button[contains(., 'Select All')]")
                        except:
                            # Method 3: Look for checkbox with "Select All" label
                            try:
                                select_all = driver.find_element(By.XPATH, "//label[contains(., 'Select All')]")
                            except:
                                print("  ⚠️ Could not find 'Select All' option")
                    
                    if select_all:
                        select_all.click()
                        print("  ✅ Clicked 'Select All' option")
                        time.sleep(1)  # Wait for checkboxes to be selected
                    else:
                        print("  ⚠️ 'Select All' option not found")
                        
                except Exception as e:
                    print(f"  ⚠️ Error selecting 'Select All' option: {e}")
                
                # Close dropdown by clicking elsewhere
                driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(1)  # Wait for dropdown to close
                
            except Exception as e:
                print(f"  ⚠️ Error processing {dropdown['name']} dropdown: {e}")
                # Continue with other dropdowns even if one fails
        
        # Wait for page to update after all filters are set
        time.sleep(2)
        return True
        
    except Exception as e:
        print(f"⚠️ Error handling page filters: {e}")
        return False
        
    except Exception as e:
        print(f"⚠️ Error handling page filters: {e}")
        return False
    
def search_and_navigate_to_correct_page(driver, breadcrumb_text):
    """
    Searches for the breadcrumb text in the search box and clicks the first result.
    
    Args:
        driver: Selenium WebDriver instance
        breadcrumb_text: Text to search for (from email link)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Wait for search input to be present
        wait = WebDriverWait(driver, 10)
        search_input = wait.until(
            EC.presence_of_element_located((By.ID, "simple-search-input"))
        )
        
        # Clear any existing text and enter the breadcrumb text
        search_input.clear()
        search_input.send_keys(breadcrumb_text)
        print(f"✅ Entered search text: {breadcrumb_text}")
        
        # Find and click the search button
        search_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        search_button.click()
        print("✅ Clicked search button")
        
        # Wait dynamically for search results (max 20 seconds)
        search_results = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "search-results")),
            message="Search results did not appear within 20 seconds"
        )
        print("✅ Search results loaded")
        
        # Find and click the first search result
        first_result = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.title a, li.title a"))
        )
        result_text = first_result.text
        print(f"✅ Found first result: {result_text}")
        first_result.click()
        
        # Wait dynamically for page content to load (max 15 seconds)
        wait = WebDriverWait(driver, 15)
        wait.until(
            EC.presence_of_element_located((By.ID, "content")),
            message="Page content did not load within 15 seconds"
        )
        print("✅ Page content loaded")
        
        # Find and click the feedback button
        feedback_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'comments')]"))
        )
        feedback_button.click()
        print("✅ Clicked feedback button")
        
        # Wait for comments to appear
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error in search and navigation: {e}")
        return False
    
def verify_page_and_enable_comments(driver, expected_title, breadcrumb_text):
    """
    Verifies we're on the correct page, handles filters if needed,
    and uses search if necessary to navigate to the right page.
    
    Args:
        driver: Selenium WebDriver instance
        expected_title: The expected page title from the email link
        breadcrumb_text: Text from the breadcrumb link for searching
        
    Returns:
        bool: True if verification and setup succeeded, False otherwise
    """
    try:
        # Get the current page title
        current_title = get_page_title(driver)
        if not current_title:
            print("⚠️ Could not determine current page title")
            return False
            
        print(f"✅ Current page title: {current_title}")
        print(f"✅ Expected title from link: {expected_title}")
        
        # Clean titles for comparison
        clean_current = clean_title(current_title)
        clean_expected = clean_title(expected_title)
        
        # Check if we're on the expected page
        if not titles_match(clean_current, clean_expected):
            print(f"⚠️ Page mismatch. Expected: '{clean_expected}', Got: '{clean_current}'")
            print("🔍 Setting page filters to ensure all content is visible...")
            
            # Handle the filter dropdowns
            if not handle_page_filters(driver):
                print("⚠️ Failed to set page filters")
            
            # Search for the specific page using breadcrumb text
            print(f"🔍 Searching for: {breadcrumb_text}")
            if not search_and_navigate_to_correct_page(driver, breadcrumb_text):
                print("⚠️ Failed to search and navigate to correct page")
                return False
                
        else:
            print("✅ Page title verification successful")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error during page verification: {e}")
        return False

# def capture_comment_text(driver, expected_date_string):
#     """
#     Waits for and captures only the clean comment text inside 'comment-span'
#     after expanding 'More' button if needed.
#     Retries if wrong comment is highlighted.
#     """
#     try:

#         wait = WebDriverWait(driver, 15)

#         # Find the comment box
#         comment_box = wait.until(
#             EC.presence_of_element_located((By.CLASS_NAME, "comment-highlighted"))
#         )

#         # Click on comment box to focus (this is mandatory!)
#         comment_box.click()

#         # Validate if comment_box contains expected date
#         full_box_text = comment_box.text
#         print(f"✅ Full comment text: {full_box_text}")
#         print(f"✅ Expected date string: {expected_date_string}")

#         if expected_date_string not in full_box_text:
#             print(f"⚠️ Expected date '{expected_date_string}' not found in highlighted comment. Refreshing page and retrying...")

#             driver.refresh()

#             # Wait for full comment panel reload
#             WebDriverWait(driver, 120).until(
#                 EC.presence_of_element_located((By.CLASS_NAME, "comments-pane"))
#             )

#             # Find the comment box
#             comment_box = wait.until(
#             EC.presence_of_element_located((By.CLASS_NAME, "comment-highlighted"))
#         )
#             comment_box.click()
#             full_box_text = comment_box.text

#             if expected_date_string not in full_box_text:
#                 print(f"❌ Still wrong comment after refresh. Aborting capture.")
#                 return None

#             else:
#                 print("✅ Correct comment found after refresh.")

#         # Now expand "More" button if needed
#         try:
#             more_button = comment_box.find_element(By.CLASS_NAME, "truncation")
#             if more_button.is_displayed():
#                 more_button.click()
#                 print("ℹ️ 'More' button clicked inside comment.")
#                 time.sleep(2)  # wait after expanding
#         except Exception:
#             print("ℹ️ No 'More' button found — full comment already visible.")

#         # Finally capture clean comment text from comment-span
#         comment_span = comment_box.find_element(By.CLASS_NAME, "comment-span")
#         clean_comment_text = comment_span.text

#         print(f"✅ Captured clean comment text: {clean_comment_text}")
#         return clean_comment_text

#     except Exception as e:
#         print(f"⚠️ Error capturing clean comment text: {e}")
#         return None

def capture_comment_text(driver, email_comment_text=None):
    """
    Captures the already highlighted comment text and verifies it matches the email comment.
    
    Args:
        driver: Selenium WebDriver instance
        email_comment_text: Comment text extracted from email for validation
        
    Returns:
        str: The clean comment text if found and validated, None otherwise
    """
    try:
        wait = WebDriverWait(driver, 15)

        # Find the highlighted comment (should be only one)
        comment_box = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "comment-highlighted"))
        )
        
        # Click on comment box to ensure it's fully loaded/focused
        comment_box.click()
        
        # First, expand "More" button if needed to see full content
        try:
            more_button = comment_box.find_element(By.CLASS_NAME, "truncation")
            if more_button.is_displayed():
                more_button.click()
                print("ℹ️ 'More' button clicked inside comment.")
                time.sleep(2)  # wait after expanding
        except Exception:
            print("ℹ️ No 'More' button found — full comment already visible.")
        
        # Extract clean comment text from the highlighted comment
        comment_span = comment_box.find_element(By.CLASS_NAME, "comment-span")
        clean_comment_text = comment_span.text

                # Get HTML content using JavaScript
        comment_html = driver.execute_script("""
            return arguments[0].innerHTML;
        """, comment_span)
        
        print(f"✅ Captured highlighted comment text: {clean_comment_text}")
        print(f"✅ Captured comment HTML: {comment_html[:100]}...")
        
        # If we have email comment text, validate the match
        if email_comment_text:
            # Normalize both texts for comparison (remove extra spaces, newlines, etc.)
            clean_email_text = ' '.join(email_comment_text.split())
            clean_ui_text = ' '.join(clean_comment_text.split())
            
            # Check if there's significant overlap
            # This is a simplistic check - in production you might want something more robust
            if clean_email_text in clean_ui_text or clean_ui_text in clean_email_text:
                print("✅ Comment text matches between email and UI")
            else:
                # Find some significant keywords from email text
                significant_words = [w for w in clean_email_text.split() if len(w) > 5][:5]
                
                # Check if these keywords are in the UI text
                matches = sum(1 for word in significant_words if word in clean_ui_text)
                if matches >= min(3, len(significant_words)):
                    print(f"✅ Found {matches} keyword matches between email and UI comment")
                else:
                    print("⚠️ Comment text doesn't match between email and UI")
                    print(f"Email: {clean_email_text[:150]}...")
                    print(f"UI: {clean_ui_text[:150]}...")
                    
                    # Consider returning None here if you want to abort when texts don't match
                    # For now, I'll continue and just log the warning
                    # return None
        
        return {
            'text': clean_comment_text,
            'html': comment_html
        }

    except Exception as e:
        print(f"⚠️ Error capturing comment text: {e}")
        return None
    

def capture_underlined_text(driver, context_window: int = 50) -> dict | None:
    """
    Returns an enhanced dict with:
      comment_id    : str - The data-id attribute from the commented text span
      visible_text  : str - Text visible in the UI
      href          : str | None - Direct href if found
      context       : str - Context around the underlined text
      element_type  : str - Element tag name (xref, pname, etc)
      has_conkeyref : bool - Whether element has a conkeyref
      parent_path   : str - Simple DOM path to help identify location
      comment_type  : str - Inferred type of change (link, text, etc)
    """
    try:
        wait = WebDriverWait(driver, 60)

        # 1) Wait for the orange-underlined element
        u_elem = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "commented-text-hover"))
        )

        # 2) Find the parent span with data-id (NEW)
        commented_text_span = None
        try:
            commented_text_span = u_elem.find_element(By.XPATH, "ancestor-or-self::*[contains(@class,'commented-text')]")
            comment_id = commented_text_span.get_attribute("data-id")
            print(f"✅ Found comment span with data-id: {comment_id}")
        except Exception as e:
            print(f"⚠️ Could not find parent span with data-id: {e}")
            comment_id = None

        # 3) Visible text (may be empty for conkeyref placeholders)
        visible_text = u_elem.text.strip()

        # 4) Enhanced element information
        element_type = driver.execute_script("return arguments[0].tagName.toLowerCase()", u_elem)
        element_classes = driver.execute_script("return arguments[0].className", u_elem)
        
        # 5) Try to grab href from nearest <xref>
        try:
            xref = u_elem.find_element(By.XPATH, "./ancestor-or-self::xref[1]")
            href = xref.get_attribute("href")
        except Exception:
            href = None
            
        # 6) Check for conkeyref attributes (directly or in child elements)
        has_conkeyref = driver.execute_script("""
            const elem = arguments[0];
            if (elem.hasAttribute('conkeyref')) return true;
            return Array.from(elem.querySelectorAll('*')).some(e => e.hasAttribute('conkeyref'));
        """, u_elem)

        # 7) Build a simple parent path to help with XML location
        parent_path = driver.execute_script("""
            const elem = arguments[0];
            let path = [];
            let current = elem;
            
            // Collect up to 3 levels of parent tags with their positions
            for (let i = 0; i < 3; i++) {
                if (!current || !current.parentElement) break;
                current = current.parentElement;
                
                // Get tag and position among siblings
                const tag = current.tagName.toLowerCase();
                const siblings = Array.from(current.parentElement?.children || []);
                const position = siblings.indexOf(current);
                
                path.unshift(`${tag}[${position}]`);
            }
            
            return path.join(' > ');
        """, u_elem)

        # 8) Get context - first try with element content
        context = driver.execute_script("""
            const n = arguments[0];
            const win = n.ownerDocument.defaultView;
            const sel = win.getSelection();
            sel.removeAllRanges();
            const range = win.document.createRange();
            range.selectNodeContents(n);
            return range.toString();
        """, u_elem).strip()

        # Fallback: manual slice if the above returns the same empty text
        if not context:
            context = driver.execute_script(f"""
                const node = arguments[0];
                const txt = node.parentNode.innerText;
                const idx = txt.indexOf(node.innerText);
                const w = {context_window};
                return txt.slice(Math.max(0, idx - w), idx + node.innerText.length + w);
            """, u_elem).strip()

        # 9) Try to infer the type of change from the comment text
        # This will be populated later by analyzing the comment
        comment_type = "unknown"

        info = {
            "comment_id": comment_id,  # NEW
            "visible_text": visible_text,
            "href": href,
            "context": context,
            "element_type": element_type,
            "has_conkeyref": has_conkeyref,
            "parent_path": parent_path,
            "comment_type": comment_type
        }

        print("✅ Captured enhanced underline info:", json.dumps(info, indent=2))
        return info

    except Exception as e:
        print(f"⚠️ Could not capture underlined text: {e}")
        return None
    
def click_more_button(driver):
    """
    Clicks the 'More' button to open dropdown menu.
    """
    try:
        wait = WebDriverWait(driver, 60)

        more_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'More')]"))
        )
        more_button.click()
        print("✅ Clicked 'More' button.")

    except Exception as e:
        print(f"⚠️ Error clicking 'More' button: {e}")


def click_edit_in_IXIA_dropdown(driver):
    """
    Clicks the 'Edit in IXIA CCMS Web' option inside already opened dropdown.
    """
    try:
        wait = WebDriverWait(driver, 60)

        edit_in_IXIA_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(.,'Edit in IXIA CCMS Web')]"))
        )
        edit_in_IXIA_option.click()
        print("✅ Clicked 'Edit in IXIA CCMS Web' option.")

    except Exception as e:
        print(f"⚠️ Error clicking 'Edit in IXIA CCMS Web': {e}")


def switch_to_new_tab(driver):
    """
    Switch Selenium focus to newly opened tab.
    """
    try:
        driver.switch_to.window(driver.window_handles[-1])
        print("✅ Switched to new tab (IXIA CCMS Web).")
    except Exception as e:
        print(f"⚠️ Error switching tabs: {e}")

def click_authentication_server(driver):
    """
    Clicks on the 'YOUR AUTHENTICATION SERVER' button in IXIA CCMS login page.
    """
    try:
        wait = WebDriverWait(driver, 80)

        auth_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'YOUR AUTHENTICATION SERVER')]"))
        )
        auth_button.click()
        print("✅ Clicked 'YOUR AUTHENTICATION SERVER' button.")

    except Exception as e:
        print(f"⚠️ Error clicking authentication server: {e}")

def wait_for_homepage_load(driver):
    """
    Waits until IXIA Home Page is fully loaded (detects 'My Assignments' tile).
    """
    try:
        wait = WebDriverWait(driver, 90)  # maximum wait 30 seconds

        home_tile = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(.,'My Assignments')]"))
        )
        print("✅ IXIA CCMS Home Page loaded.")

    except Exception as e:
        print(f"⚠️ Error waiting for IXIA Home Page: {e}")

def close_current_tab(driver):
    """
    Closes the current active tab and switches back to the previous one.
    """
    try:
        driver.close()
        time.sleep(2)  # small safety wait

        driver.switch_to.window(driver.window_handles[-1])
        print("✅ Closed current tab and switched back to previous tab.")

    except Exception as e:
        print(f"⚠️ Error closing tab: {e}")


def switch_back_to_breadcrumb_tab(driver):
    """
    Switches focus back to the SAP Help Portal tab.
    """
    try:
        if len(driver.window_handles) >= 2:
            driver.switch_to.window(driver.window_handles[0])
            print("✅ Switched back to SAP Help Portal tab.")
        else:
            print("⚠️ Only one tab open, cannot switch back.")

    except Exception as e:
        print(f"⚠️ Error switching back to SAP Help Portal tab: {e}")

def wait_for_more_menu_ready(driver):
    """
    Waits until the 3-dot 'More' menu is fully available after switching to Edit mode.
    Handles internal DOM reloads after Edit click.
    """
    try:
        wait = WebDriverWait(driver, 120)

        # Wait for document readyState to be complete
        wait.until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        print("✅ Document reloaded after Edit.")

                # Now wait for DOM stabilization
        dom_stable = False
        last_dom_count = 0
        stable_count = 0

        while not dom_stable:
            current_dom_count = driver.execute_script('return document.getElementsByTagName("*").length')
            if current_dom_count == last_dom_count:
                stable_count += 1
            else:
                stable_count = 0
                last_dom_count = current_dom_count

            if stable_count >= 5:
                dom_stable = True
                print("✅ DOM stabilized after Edit.")

            time.sleep(1)  # check every 1 second

     

    except Exception as e:
        print(f"⚠️ Error waiting for 3-dot menu after Edit: {e}")




def click_edit_button(driver):
    try:
        btn = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//button[starts-with(@id, 'btn-btn-edit-')]"))
        )
        btn.click()
        print("✅ Clicked 'Edit' button.")
    except Exception as e:
        print(f"⚠️ Error clicking 'Edit' button: {e}")





# def click_edit_as_xml(driver):
#     """
#     Clicks on the 'Edit as XML' option in the IXIA Web Editor after clicking 3-dot More button.
#     """
#     try:
#         wait = WebDriverWait(driver, 90)

#         # Use CSS selector with escaped colon
#         three_dot_button = wait.until(
#             EC.element_to_be_clickable((By.CSS_SELECTOR, "#\\:b"))
#         )

#         three_dot_button.click()
#         print("✅ Clicked 3-dot 'More' button.")

#         # Wait for dropdown and click "Edit as XML"
#         wait.until(
#             EC.visibility_of_element_located((By.CLASS_NAME, "goog-toolbar-menu-button-dropdown"))
#         )

#         # 3. Click 'Edit as XML' menu item
#         edit_as_xml_option = wait.until(
#             EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Edit as XML')]"))
#         )
#         edit_as_xml_option.click()
#         print("✅ Clicked 'Edit as XML' option.")

        





#     except Exception as e:
#         print(f"⚠️ Error clicking 'Edit as XML': {e}")


# def click_edit_as_xml(driver):
#     """
#     Clicks on the 'Edit as XML' option in the IXIA Web Editor after opening the 3-dot menu.
#     """
#     try:
#         wait = WebDriverWait(driver, 60)
#         # 1) wait for full load
#         wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

#         # 2) open the 3-dot menu
#         menu_btn = wait.until(
#             EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='button'][aria-label='More...']"))
#         )
#         driver.execute_script("arguments[0].scrollIntoView(true);", menu_btn)
#         try:
#             menu_btn.click()
#         except:
#             driver.execute_script("arguments[0].click();", menu_btn)
#         print("✅ Clicked three-dot menu")

#         # 3) wait for the dropdown to appear
#         dropdown = wait.until(
#             EC.visibility_of_element_located((By.CSS_SELECTOR, "div.goog-toolbar-menu-button-dropdown"))
#         )
#         print("✅ Dropdown visible")

#         # 4) click the "Edit as XML" entry
#         edit_xml = wait.until(
#             EC.element_to_be_clickable((By.XPATH, "//*[@role='menuitem' and normalize-space(.)='Edit as XML']"))
#         )
#         driver.execute_script("arguments[0].scrollIntoView(true);", edit_xml)
#         driver.execute_script("arguments[0].click();", edit_xml)
#         print("✅ Clicked 'Edit as XML'")

#     except TimeoutException as te:
#         # on timeout, capture screenshot for inspection
#         driver.save_screenshot("edit_as_xml_timeout.png")
#         print("⚠️ Timeout waiting for 'Edit as XML':", te)
#     except Exception as e:
#         driver.save_screenshot("edit_as_xml_error.png")
#         print("⚠️ Error clicking 'Edit as XML':", e)

def click_edit_as_xml(driver):
    """
    1) Switch into the Oxygen iframe
    2) Click the 3‐dot "More..." toolbar button 
    3) Wait for the dropdown, then try several locators for "Edit as XML"
    4) Reset back to the top frame
    
    Enhanced version with better waiting and diagnostics
    """
    try:

        # First make sure we're on the main document
        driver.switch_to.default_content()
        wait = WebDriverWait(driver, 90)  # Increased timeout
        
        # 1) Switch into the embedded editor iframe
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "WebAuthor-frame")))
        print("✅ Switched into WebAuthor-frame iframe")
        
        # Make sure page is fully loaded
        time.sleep(2)  # Small safety wait
        
        # 2) Click the toolbar's 3-dot "More..." button
        menu_locators = [
            (By.CSS_SELECTOR, "div[role='button'][aria-label='More...']"),
            (By.XPATH, "//div[@role='button' and contains(., 'More')]"),
            (By.XPATH, "//div[contains(@class, 'goog-toolbar-menu-button')]"),
            (By.XPATH, "//*[contains(text(), 'More...')]"),
        ]
        
        menu_btn = None
        for by, sel in menu_locators:
            try:
                elements = wait.until(EC.presence_of_all_elements_located((by, sel)))
                for element in elements:
                    if element.is_displayed():
                        menu_btn = element
                        print(f"✅ Found 'More...' button using {by}: {sel}")
                        break
                if menu_btn:
                    break
            except:
                continue
                
        if not menu_btn:
            driver.save_screenshot("more_button_not_found.png")
            raise Exception("Could not find the 'More...' button")
            
        # Take screenshot before click
        driver.save_screenshot("menu_before_click.png")
        
        # Scroll and click
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", menu_btn)
        time.sleep(1)  # Wait after scrolling
        
        try:
            # Try direct click
            menu_btn.click()
        except:
            # If direct click fails, try JavaScript click
            driver.execute_script("arguments[0].click();", menu_btn)
            
        print("✅ Clicked 'More...' toolbar button")
        
        # 3) Wait for dropdown to appear - try multiple selectors
        dropdown_selectors = [
            "div.goog-toolbar-menu-button-dropdown", 
            "div.goog-menu",
            "div[role='menu']"
        ]
        
        dropdown_found = False
        for selector in dropdown_selectors:
            try:
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"✅ Dropdown menu visible with selector: {selector}")
                dropdown_found = True
                break
            except:
                continue
                
        if not dropdown_found:
            driver.save_screenshot("dropdown_not_visible.png")
            raise Exception("Dropdown menu never became visible")
        
        # Take screenshot of dropdown
        driver.save_screenshot("dropdown_visible.png")
        
        # Allow DOM to stabilize
        time.sleep(2)
        
        # 4) Try multiple ways to find and click "Edit as XML"
        xml_menu_locators = [
            (By.XPATH, "//div[contains(@class,'goog-menuitem') and normalize-space(.)='Edit as XML']"),
            (By.XPATH, "//div[@role='menuitem' and normalize-space(.)='Edit as XML']"),
            (By.XPATH, "//*[contains(text(),'Edit as XML')]"),
            (By.CSS_SELECTOR, ".goog-menuitem-content:contains('Edit as XML')"),
            (By.LINK_TEXT, "Edit as XML"),
            # More specific XPath that might catch hierarchical menu structure
            (By.XPATH, "//div[contains(@class,'goog-menu')]//div[normalize-space(.)='Edit as XML']"),
        ]
        
        # Try clicking each element that matches our locators
        clicked = False
        for by, sel in xml_menu_locators:
            try:
                # Find all matching elements
                elems = driver.find_elements(by, sel)
                for e in elems:
                    try:
                        if e.is_displayed():
                            # Screenshot the found item
                            driver.save_screenshot("xml_item_found.png")
                            
                            # Try multiple click strategies
                            try:
                                # 1. Center the element
                                driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center'});", e)
                                time.sleep(1)
                                
                                # 2. Try direct click
                                e.click()
                            except:
                                try:
                                    # 3. Try JavaScript click
                                    driver.execute_script("arguments[0].click();", e)
                                except:
                                    # 4. Try with Actions
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    actions = ActionChains(driver)
                                    actions.move_to_element(e).click().perform()
                            
                            print(f"✅ Clicked 'Edit as XML' via {by}: {sel}")
                            clicked = True
                            
                            # Wait for click effect
                            time.sleep(3)
                            break
                    except:
                        continue
                    
                if clicked:
                    break
            except Exception as ex:
                print(f"Skipping locator {by}: {sel} due to: {ex}")
                continue

        if not clicked:
            # Last resort - try to find by approximate text and JavaScript execution
            try:
                driver.execute_script("""
                    var items = document.querySelectorAll('div');
                    for(var i=0; i<items.length; i++) {
                        if(items[i].textContent.includes('Edit as XML')) {
                            items[i].click();
                            return true;
                        }
                    }
                    return false;
                """)
                print("✅ Attempted to click 'Edit as XML' via JavaScript text search")
                clicked = True
            except:
                pass

        if not clicked:
            driver.save_screenshot("edit_as_xml_not_found.png")
            raise TimeoutException("Could not find or click 'Edit as XML' menu item")
        
        # Wait for XML editor to load
        time.sleep(5)  # Give time for XML view to initialize

    except Exception as e:
        driver.save_screenshot("click_edit_as_xml_error.png")
        print("⚠️ Error in click_edit_as_xml:", e)
        raise e  # Re-raise to allow caller to handle
    finally:
        # Always go back to the main document so the next routine can re-enter cleanly
        try:
            driver.switch_to.default_content()
        except:
            pass

def capture_full_xml_source(driver, timeout=60):
    """
    After 'Edit as XML' click, return the complete XML string displayed
    by Oxygen in IXIA CCMS Web Author by accessing the CodeMirror API.
    """
    def _switch(locator):
        WebDriverWait(driver, timeout).until(
            EC.frame_to_be_available_and_switch_to_it(locator)
        )

    try:
        driver.switch_to.default_content()

        # Step 1: Enter WebAuthor-frame
        _switch((By.ID, "WebAuthor-frame"))
        wait = WebDriverWait(driver, timeout)
        print("✅ In WebAuthor-frame")

        # Step 2: Wait until Oxygen XML editor is loaded
        def oxygen_ready(drv):
            """Return True once the XML editor is present somewhere."""
            # a) inline CodeMirror (SAP build)
            if drv.find_elements(By.CSS_SELECTOR, "div.CodeMirror"):
                return True
            # b) classic nested iframe has appeared
            if drv.find_elements(By.CSS_SELECTOR, "iframe[id^='text-mode-iframe']"):
                return True
            # c) plugin iframe has appeared
            if drv.find_elements(By.CSS_SELECTOR, "iframe[id^='SAP-plugin-iframe']"):
                return True
            return False

        WebDriverWait(driver, 90).until(oxygen_ready)
        print("✅ Oxygen XML editor loaded")

        # Step 3: Handle different iframe layouts
        layout = "unknown"
        
        # Try to locate CodeMirror in the current frame first
        if driver.find_elements(By.CSS_SELECTOR, "div.CodeMirror"):
            layout = "sap-inline"
        # Try the classic nested iframe
        elif driver.find_elements(By.CSS_SELECTOR, "iframe[id^='text-mode-iframe']"):
            inner_iframe = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id^='text-mode-iframe']")
                )
            )
            driver.switch_to.frame(inner_iframe)
            layout = "classic-iframe"
        # Try the plugin iframe
        elif driver.find_elements(By.CSS_SELECTOR, "iframe[id^='SAP-plugin-iframe']"):
            inner_iframe = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id^='SAP-plugin-iframe']")
                )
            )
            driver.switch_to.frame(inner_iframe)
            layout = "plugin-iframe"

        print(f"✅ Found CodeMirror in {layout}")
        
        # Step 4: Get the full XML content through CodeMirror API
        # This is the critical change - use JavaScript to get the full content!
        xml_text = driver.execute_script("""
            // Find the CodeMirror instance
            var editor = document.querySelector('.CodeMirror').CodeMirror;
            // Get the complete document text
            return editor ? editor.getValue() : document.querySelector('.CodeMirror-code').textContent;
        """)
        
        if not xml_text:
            # Fallback method to try if the JavaScript approach fails
            code_div = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.CodeMirror-code"))
            )
            
            # Try to scroll through the entire document to load all content
            driver.execute_script("""
                var codeDiv = arguments[0];
                // Scroll to bottom to ensure all content is loaded
                codeDiv.scrollTop = codeDiv.scrollHeight;
                // Then scroll back to top
                setTimeout(function() { codeDiv.scrollTop = 0; }, 500);
            """, code_div)
            
            # Give time for scrolling to complete
            time.sleep(1)
            
            # Try to get the text now that everything is loaded
            lines = code_div.find_elements(By.CSS_SELECTOR, "pre.CodeMirror-line")
            xml_text = "\n".join(ln.text for ln in lines if ln.text).strip()
            
            if not xml_text:
                # Last resort: try to get text directly
                xml_text = code_div.text.strip()

        print(f"✅ Captured XML ({len(xml_text.splitlines())} lines)")
        return xml_text

    except Exception as e:
        driver.save_screenshot("capture_full_xml_error.png")
        print(f"⚠️ Error capturing XML: {e}")
        return None
    finally:
        driver.switch_to.default_content()

def apply_modified_xml(driver, modified_xml, timeout=60):
    """
    Apply the modified XML to the CodeMirror editor in IXIA CCMS Web Author.
    Uses the same iframe navigation logic as capture_full_xml_source.
    
    Args:
        driver: Selenium WebDriver instance
        modified_xml: The modified XML content to set
        timeout: Maximum wait time in seconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    def _switch(locator):
        WebDriverWait(driver, timeout).until(
            EC.frame_to_be_available_and_switch_to_it(locator)
        )

    try:
        driver.switch_to.default_content()

        # Step 1: Enter WebAuthor-frame
        _switch((By.ID, "WebAuthor-frame"))
        wait = WebDriverWait(driver, timeout)
        print("✅ In WebAuthor-frame")

        # Step 2: Wait until Oxygen XML editor is loaded
        def oxygen_ready(drv):
            """Return True once the XML editor is present somewhere."""
            # a) inline CodeMirror (SAP build)
            if drv.find_elements(By.CSS_SELECTOR, "div.CodeMirror"):
                return True
            # b) classic nested iframe has appeared
            if drv.find_elements(By.CSS_SELECTOR, "iframe[id^='text-mode-iframe']"):
                return True
            # c) plugin iframe has appeared
            if drv.find_elements(By.CSS_SELECTOR, "iframe[id^='SAP-plugin-iframe']"):
                return True
            return False

        WebDriverWait(driver, 90).until(oxygen_ready)
        print("✅ Oxygen XML editor loaded")

        # Step 3: Handle different iframe layouts
        layout = "unknown"
        
        # Try to locate CodeMirror in the current frame first
        if driver.find_elements(By.CSS_SELECTOR, "div.CodeMirror"):
            layout = "sap-inline"
        # Try the classic nested iframe
        elif driver.find_elements(By.CSS_SELECTOR, "iframe[id^='text-mode-iframe']"):
            inner_iframe = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id^='text-mode-iframe']")
                )
            )
            driver.switch_to.frame(inner_iframe)
            layout = "classic-iframe"
        # Try the plugin iframe
        elif driver.find_elements(By.CSS_SELECTOR, "iframe[id^='SAP-plugin-iframe']"):
            inner_iframe = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id^='SAP-plugin-iframe']")
                )
            )
            driver.switch_to.frame(inner_iframe)
            layout = "plugin-iframe"

        print(f"✅ Found CodeMirror in {layout}")
        
        # Step 4: Set the full XML content through CodeMirror API
        success = driver.execute_script("""
            try {
                // Find the CodeMirror instance
                var editor = document.querySelector('.CodeMirror').CodeMirror;
                
                // Set the modified content
                if (editor) {
                    editor.setValue(arguments[0]);
                    
                    // Trigger change event to ensure the editor recognizes the change
                    editor.refresh();
                    
                    return true;
                } else {
                    return false;
                }
            } catch (error) {
                console.error("Error setting XML content:", error);
                return false;
            }
        """, modified_xml)
        
        if success:
            print("✅ Applied modified XML to editor")
            return True
        else:
            # Fallback if the JavaScript approach fails
            print("⚠️ Primary method failed, trying fallback...")
            
            # Try using clipboard or direct character input as fallback
            # This is less reliable but might work in some cases
            try:
                # Try to use document.execCommand which might work in some browsers
                fallback_success = driver.execute_script("""
                    try {
                        // Find the CodeMirror textarea
                        var textarea = document.querySelector('.CodeMirror textarea');
                        if (textarea) {
                            textarea.value = arguments[0];
                            return true;
                        }
                        return false;
                    } catch (error) {
                        return false;
                    }
                """, modified_xml)
                
                if fallback_success:
                    print("✅ Applied modified XML using fallback method")
                    return True
                else:
                    print("⚠️ Failed to apply modified XML")
                    return False
            except Exception as e:
                print(f"⚠️ Error in fallback method: {e}")
                return False

    except Exception as e:
        driver.save_screenshot("apply_modified_xml_error.png")
        print(f"⚠️ Error applying modified XML: {e}")
        return False
    finally:
        driver.switch_to.default_content()

def get_annotation_offsets(driver, comment_id):
    """
    Use IXIA CCMS Web's IXAnnotations API to get XML offsets for a comment ID.
    
    Args:
        driver: Selenium WebDriver instance
        comment_id: Comment ID from data-id attribute
        
    Returns:
        Dictionary with startOffset and endOffset or None if not found
    """
    try:
        # Execute JavaScript to access the IXAnnotations API
        script = f"""
            if (typeof IXAnnotations !== 'undefined' && IXAnnotations.getAnnotationById) {{
                return IXAnnotations.getAnnotationById('{comment_id}');
            }} else {{
                return null;
            }}
        """
        
        result = driver.execute_script(script)
        
        if result and 'startOffset' in result and 'endOffset' in result:
            print(f"✅ Found annotation offsets for comment ID {comment_id}: {result['startOffset']}-{result['endOffset']}")
            return {
                'startOffset': result['startOffset'],
                'endOffset': result['endOffset']
            }
        else:
            print(f"⚠️ Could not find annotation offsets for comment ID {comment_id}")
            return None
            
    except Exception as e:
        print(f"⚠️ Error accessing IXAnnotations API: {e}")
        return None
    
def wait_for_page_after_checkin(driver, timeout=90):
    """
    Wait for the page to fully load after checking in a document.
    Uses a similar strategy to the beginning of click_edit_as_xml.
    
    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum wait time in seconds
        
    Returns:
        bool: True if page loaded successfully, False otherwise
    """
    try:
        # First make sure we're on the main document
        driver.switch_to.default_content()
        wait = WebDriverWait(driver, timeout)
        
        # Wait for document ready state to be complete
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        print("✅ Document ready state is complete")
        
        # Small safety wait
        time.sleep(2)
        
        # Wait for the WebAuthor-frame to be available (if we're returning to author view)
        try:
            wait.until(EC.presence_of_element_located((By.ID, "WebAuthor-frame")))
            print("✅ WebAuthor-frame is present")
        except:
            # We might not return to the author view, so this is not critical
            print("ℹ️ WebAuthor-frame not found - might be on a different view")
        
        # Check for any loading indicators and wait for them to disappear
        try:
            loading_indicators = driver.find_elements(By.CSS_SELECTOR, ".loading-indicator, .spinner, [role='progressbar']")
            if loading_indicators:
                for indicator in loading_indicators:
                    if indicator.is_displayed():
                        wait.until(EC.invisibility_of_element(indicator))
                print("✅ All loading indicators disappeared")
        except:
            # No loading indicators found, which is fine
            pass
        
        # Additional wait for DOM stability
        prev_dom_size = -1
        stable_count = 0
        max_checks = 10
        
        for _ in range(max_checks):
            current_dom_size = driver.execute_script("return document.getElementsByTagName('*').length")
            if current_dom_size == prev_dom_size:
                stable_count += 1
                if stable_count >= 3:  # 3 consecutive unchanged checks
                    print("✅ DOM has stabilized")
                    break
            else:
                stable_count = 0
                prev_dom_size = current_dom_size
            time.sleep(0.5)
        
        return True
    
    except Exception as e:
        print(f"⚠️ Error waiting for page to load after check-in: {e}")
        driver.save_screenshot("post_checkin_error.png")
        return False
    
def click_check_in_button(driver):
    """
    Clicks on the 'Check In' button in the IXIA CCMS Web Editor and handles the confirmation dialog.
    """
    try:
        # Step 1: Click the main Check In button
        btn = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, "//button[starts-with(@id, 'btn-btn-chkin-')]"))
        )
        btn.click()
        print("✅ Clicked 'Check In' button.")
        
        # Step 2: Wait for the confirmation dialog to appear
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.MuiDialogActions-root"))
        )
        print("✅ Check In confirmation dialog appeared.")
        
        # Step 3: Click the "Check In" button in the confirmation dialog
        confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "check-in-confirm-button"))
        )
        confirm_btn.click()
        print("✅ Confirmed check-in in dialog.")
        
        time.sleep(3)  # Wait for the check-in process to complete
        
        return True
    except Exception as e:
        print(f"⚠️ Error during check-in process: {e}")
        driver.save_screenshot("check_in_error.png")
        return False
    


# # Quick test
# if __name__ == "__main__":
#     # driver = launch_edge()
#     url = "https://help.sap.com/docs/s4hana-best-practices/setting-up-subscription-management-with-sales-billing-57z-ce94397783772ce7b4625bcc48d89fce/system-information?state=DRAFT&comment_id=22339796&show_comments=true"  # TEMP TEST URL
#     open_help_portal_page(driver, url)

#     # Capture comment
#     comment_text = capture_comment_text(driver)

#     # Capture underlined text
#     underlined_text = capture_underlined_text(driver)

#     # After testing, quit
#     # driver.quit()
