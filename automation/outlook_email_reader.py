# automation/outlook_email_reader.py

import win32com.client
import time
from bs4 import BeautifulSoup
import webbrowser
import datetime

def connect_outlook():
    """
    Connects to the Outlook application using pywin32.
    Returns the Outlook namespace object.
    """
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    return outlook

def get_unread_sap_notification_emails(outlook, target_date):
    """
    Gets unread SAP Help Portal Notification emails received on target_date.
    Returns a list of email items.
    """
    inbox = outlook.GetDefaultFolder(6)  # 6 = Inbox

    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)  # newest first

    unread_sap_emails = []

    for message in messages:
        try:
            if message.Unread and "SAP Help Portal: Comment Notification" in message.Subject:
                email_date = message.ReceivedTime.date()

                if email_date == target_date:
                    unread_sap_emails.append(message)

        except Exception as e:
            print(f"⚠️ Error while processing email: {e}")
            continue

    print(f"✅ Found {len(unread_sap_emails)} unread SAP notification emails on {target_date}.")
    return unread_sap_emails

def extract_breadcrumb_link(email_item):
    """
    Extracts the breadcrumb link (2nd <a> tag), its text label, and comment text from email.
    
    Args:
        email_item: The Outlook email object
        
    Returns:
        tuple: (breadcrumb_link, link_text, comment_text) or (None, None, None) if extraction fails
    """
    try:
        html_body = email_item.HTMLBody
        soup = BeautifulSoup(html_body, 'html.parser')

        # Extract breadcrumb link (2nd <a> tag)
        links = soup.find_all('a')
        breadcrumb_link = None
        link_text = None
        
        if len(links) >= 2:
            breadcrumb_link = links[1].get('href')
            link_text = links[1].get_text().strip()
            print(f"✅ Extracted breadcrumb link: {breadcrumb_link}")
            print(f"✅ Extracted link text: {link_text}")
        else:
            print("⚠️ Less than 2 links found in email.")
            return None, None, None

        # Extract comment text - existing logic
        comment_text = None
        
        # Try to find the comment in the table structure
        comment_cells = soup.find_all('td', style=lambda s: s and 'padding: 16px' in s)
        for cell in comment_cells:
            # Skip cells that are just headers
            if 'Status:' in cell.text and len(cell.text) < 100:
                continue
                
            # Get all paragraphs from this cell
            paragraphs = cell.find_all('p')
            if paragraphs:
                # Combine paragraph texts, excluding metadata
                texts = []
                for p in paragraphs:
                    p_text = p.text.strip()
                    # Skip timestamps and status info
                    if not any(x in p_text for x in ['Status:', '(Modified)', 'UTC']):
                        texts.append(p_text)
                
                comment_text = ' '.join(texts)
                break
        
        if comment_text:
            print(f"✅ Extracted comment text: {comment_text[:100]}...")
        else:
            print("⚠️ Could not extract comment text from email.")

        # Return all extracted information
        return breadcrumb_link, link_text, comment_text

    except Exception as e:
        print(f"⚠️ Could not extract breadcrumb link and comment: {e}")
        return None, None, None

# # Quick manual test
# if __name__ == "__main__":
#     outlook = connect_outlook()

#     unread_emails = get_unread_sap_notification_emails(outlook, max_days=3)

#     for email in unread_emails:
#         click_breadcrumb_link(email)
#         break  # Only process the first email for testing
#         time.sleep(5)  # wait between emails (adjust as needed)
