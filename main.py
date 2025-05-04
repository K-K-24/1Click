# main.py

import os
import time
import logging
import traceback
from datetime import datetime

from automation.outlook_email_reader import connect_outlook, get_unread_sap_notification_emails, extract_breadcrumb_link
from automation.browser_automation import apply_modified_xml, clean_title, click_check_in_button, get_annotation_offsets, get_page_title, launch_edge, open_help_portal_page, capture_comment_text, capture_underlined_text, switch_to_new_tab, click_edit_button, click_edit_as_xml, capture_full_xml_source, click_authentication_server, titles_match, verify_page_and_enable_comments, wait_for_homepage_load, close_current_tab, click_more_button, click_edit_in_IXIA_dropdown
from xml_parser.extract_fragment import extract_snippet
from ai.ai_processor import process_dita_comment

# Import OpenAI API key from settings or set in environment
from config.settings import OPENAI_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Setup logging to both console and file
log_filename = f"dita_comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_driver_responsive(driver):
    """Check if the WebDriver is still responsive"""
    try:
        # Try a simple command to check if driver is responsive
        driver.current_url
        return True
    except Exception:
        logger.error("WebDriver is no longer responsive")
        return False

def process_single_email(email, target_date, position_info, driver=None, authentication_done=False):
    """
    Process a single email notification and make the necessary changes
    
    Args:
        email: The email object to process
        target_date: The target date for comment context
        position_info: String describing position of email (e.g. "3rd from bottom") 
        driver: Existing WebDriver instance or None to create a new one
        authentication_done: Whether authentication has been done in this session
        
    Returns:
        tuple: (success, driver, authentication_done)
    """
    # Track if we created our own driver
    should_quit_driver = False
    
    try:
        # Extract email subject and sender for better identification
        email_subject = email.Subject
        email_sender = email.SenderName
        email_time = email.ReceivedTime.strftime("%H:%M:%S")
        
        logger.info(f"\nProcessing email: {position_info}")
        logger.info(f"Subject: {email_subject}")
        logger.info(f"From: {email_sender}")
        logger.info(f"Time: {email_time}")
        
        # Step 1: Extract breadcrumb link, link text, and comment text
        breadcrumb_url, link_text, email_comment_text = extract_breadcrumb_link(email)
        if not breadcrumb_url:
            logger.warning(f"⚠️ Could not extract breadcrumb URL. Skipping email {position_info}.")
            return False, driver, authentication_done
        
        # Create new driver if needed
        if driver is None or not is_driver_responsive(driver):
            if driver is not None:
                logger.warning("⚠️ Browser appears to be unresponsive. Restarting browser...")
                try:
                    driver.quit()
                except:
                    pass
            
            driver = launch_edge()
            should_quit_driver = True
            authentication_done = False  # Reset authentication flag
            logger.info("✅ Launched new browser instance")
            
        # Step 2: Open SAP Help Portal page
        open_help_portal_page(driver, breadcrumb_url)

# Step 3: Verify we're on the correct page, handle filters if needed, and search if necessary
        verify_page_and_enable_comments(driver, 
                               expected_title=link_text,  # For title comparison
                               breadcrumb_text=link_text)  # For search functionality
        
        # Step 3: Wait for dynamic comment highlighting
        logger.info("⏳ Waiting 3 seconds for full dynamic comment loading...")
        time.sleep(3)
        
        # Generate expected date string
        expected_date_string = f"{target_date.month}/{target_date.day}/{str(target_date.year)[-2:]}"
        

        # Step 4: Capture comment text with HTML
        comment_data = capture_comment_text(driver, email_comment_text)
        if not comment_data:
            logger.warning(f"⚠️ Could not capture comment text. Skipping email {position_info}.")
            return False, driver, authentication_done

        # Print captured information
        logger.info("\n✅ Captured Comment Text:\n" + str(comment_data['text']))
        logger.info("\n✅ Captured Comment HTML:\n" + str(comment_data['html']))
        
        # Step 5: Capture highlighted underlined text
        underlined_text = capture_underlined_text(driver)
        if not underlined_text:
            logger.info("ℹ️ No underlined text found - this might be a new content request")
            # Create a minimal structure for underlined_text to prevent crashes
            underlined_text = {
                "visible_text": "",
                "comment_id": None,
                "context": "",
                "element_type": "unknown",
                "parent_path": "",
                "has_conkeyref": False,
                "comment_type": "new_content"  # Special flag to indicate this is a new content request
            }
        
        # Print captured information
        logger.info("\n✅ Captured Underlined Text:\n" + str(underlined_text))
        

        
        # Step 6: Navigate to XML editor
        click_more_button(driver)
        click_edit_in_IXIA_dropdown(driver)
        switch_to_new_tab(driver)
        
        # Only authenticate if not done already in this session
        if not authentication_done:
            logger.info("First email in session - performing authentication...")
            click_authentication_server(driver)
            authentication_done = True
        else:
            logger.info("Authentication already done - skipping...")
        
        click_edit_button(driver)
        click_edit_as_xml(driver)
        
        # Step 7: Capture full XML source
        full_xml = capture_full_xml_source(driver)
        if not full_xml:
            logger.warning(f"⚠️ Could not capture full XML source. Skipping email {position_info}.")
            return False, driver, authentication_done
        
        logger.info("\n✅ Captured full XML source")
        
        # Step 8: Use AI to process the XML with the comment
        logger.info("\n🤖 Processing XML with AI...")
        modified_xml, explanation = process_dita_comment(
            full_xml, 
            underlined_text, 
            comment_data
        )
        
        if not modified_xml:
            logger.warning(f"⚠️ AI processing failed: {explanation}. Skipping email {position_info}.")
            return False, driver, authentication_done
        
        logger.info("\n✅ AI processing successful")
        logger.info(f"✅ AI explanation: {explanation}")
        
        # Step 9: Apply the modified XML to the document
        if not apply_modified_xml(driver, modified_xml):
            logger.warning(f"⚠️ Failed to apply modified XML. Skipping email {position_info}.")
            return False, driver, authentication_done
        
                # Check if the XML was actually modified or if AI determined no changes needed
        if "already implemented" in explanation.lower() or "already exists" in explanation.lower():
            logger.info(f"✅ AI determined change already implemented: {explanation}")
            # Mark email as read since the change is already in place
            email.Unread = False
            email.Save()
            logger.info("✅ Marked email as Read after determining change was already implemented.")
            return True, driver, authentication_done  # Return success even though no XML was changed
        
        # Add a small delay to ensure changes are registered
        time.sleep(2)
        
        # Step 10: Check in the document
        if not click_check_in_button(driver):
            logger.warning(f"⚠️ Failed to check in document. Skipping email {position_info}.")
            return False, driver, authentication_done
        
        logger.info("✅ Document successfully checked in")

        time.sleep(3)  # Wait for check-in to complete

        # Mark email as read
        email.Unread = False
        email.Save()
        logger.info("✅ Marked email as Read after processing.")
        
        return True, driver, authentication_done
    
    except Exception as e:
        # Log the full stack trace for better debugging
        logger.error(f"⚠️ Error processing email {position_info}: {e}")
        logger.error(traceback.format_exc())
        
        # Take screenshot if driver is available
        if driver:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_file = f"error_{timestamp}.png"
            try:
                driver.save_screenshot(screenshot_file)
                logger.info(f"✅ Error screenshot saved as {screenshot_file}")
            except:
                logger.error("⚠️ Failed to save error screenshot")
        
        return False, driver, authentication_done
    finally:
        # Only quit the driver if we created it in this function
        if should_quit_driver and driver:
            try:
                driver.quit()
                driver = None
                logger.info("✅ Closed browser instance created for this email")
            except:
                logger.error("⚠️ Error closing browser instance")

def test_single_email():
    """
    Test function that processes just the first email for a given date
    using the same strategy as the main email processing flow.
    """
    logger.info("=" * 80)
    logger.info("DITA COMMENT AUTOMATION TEST - SINGLE EMAIL")
    logger.info("=" * 80)
    
    try:
        # Ask user for input date
        date_input = input("Enter target date (YYYY-MM-DD): ")
        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        logger.info(f"Processing comments for date: {target_date}")
        
        # Connect to Outlook
        logger.info("Connecting to Outlook...")
        outlook = connect_outlook()
        
        # Find unread SAP Help Portal emails for the specified date
        logger.info(f"Finding unread SAP notification emails for {target_date}...")
        unread_emails = get_unread_sap_notification_emails(outlook, target_date)
        
        if not unread_emails:
            logger.info("ℹ️ No unread SAP Help Portal emails found for this date. Exiting.")
            return
        
        total_emails = len(unread_emails)
        logger.info(f"✅ Found {total_emails} unread SAP notification emails on {target_date}.")
        
        # Reverse the list to process oldest emails first (same as main function)
        unread_emails.reverse()
        
        # Take only the first email
        test_email = unread_emails[0]
        logger.info("=" * 60)
        logger.info(f"TEST MODE: Processing only the first email")
        logger.info("=" * 60)
        
        # Initialize driver
        logger.info("Launching web browser...")
        driver = launch_edge()
        authentication_done = False
        
        try:
            # Process just the first email
            position_info = "1st email (TEST MODE)"
            success, driver, authentication_done = process_single_email(
                test_email, 
                target_date, 
                position_info, 
                driver, 
                authentication_done
            )
            
            if success:
                logger.info(f"✅ TEST SUCCESSFUL: Successfully processed {position_info}")
            else:
                logger.info(f"❌ TEST FAILED: Failed to process {position_info}")
        
        finally:
            # Always quit the driver when done
            if driver:
                try:
                    driver.quit()
                    logger.info("✅ Closed browser instance")
                except:
                    logger.error("⚠️ Error closing browser instance")
        
        # Write test summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Date: {target_date}")
        logger.info(f"Email Subject: {test_email.Subject}")
        logger.info(f"Sender: {test_email.SenderName}")
        logger.info(f"Result: {'SUCCESS' if success else 'FAILURE'}")
        
    except Exception as e:
        logger.error(f"⚠️ Critical error in test process: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("=" * 80)
    logger.info("DITA COMMENT AUTOMATION TEST COMPLETED")
    logger.info("=" * 80)

if __name__ == "__main__":
    # Change this to test_single_email() for testing one email
    test_single_email()
    # main()  # Comment this out during testing


def main():
    logger.info("=" * 80)
    logger.info("DITA COMMENT AUTOMATION STARTED")
    logger.info("=" * 80)
    logger.info(f"Log file: {log_filename}")
    
    try:
        # Ask user for input date
        date_input = input("Enter target date (YYYY-MM-DD): ")
        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        logger.info(f"Processing comments for date: {target_date}")
        
        # Connect to Outlook
        logger.info("Connecting to Outlook...")
        outlook = connect_outlook()
        
        # Find unread SAP Help Portal emails
        logger.info(f"Finding unread SAP notification emails for {target_date}...")
        unread_emails = get_unread_sap_notification_emails(outlook, target_date)
        
        if not unread_emails:
            logger.info("ℹ️ No unread SAP Help Portal emails found. Exiting.")
            return
        
        total_emails = len(unread_emails)
        logger.info(f"✅ Found {total_emails} unread SAP notification emails on {target_date}.")
        
        # Reverse the list to process oldest emails first
        # This ensures the newest comments on the same topics are processed last
        unread_emails.reverse()
        
        # Track successfully and failed emails
        successful_emails = []
        failed_emails = []
        
        # Initialize driver outside the loop to reuse it
        logger.info("Launching web browser...")
        driver = launch_edge()
        
        # Flag to track if authentication has been done in this session
        authentication_done = False
        
        # Process each email
        max_consecutive_failures = 3
        consecutive_failures = 0
        
        try:
            for i, email in enumerate(unread_emails, 1):
                # Calculate position from bottom (1-based indexing)
                position_from_bottom = i
                ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
                position_info = f"{ordinal(position_from_bottom)} email from bottom ({i}/{total_emails})"
                
                logger.info("=" * 60)
                logger.info(f"Starting to process {position_info}")
                logger.info("=" * 60)
                
                # Check if we need to restart the browser due to too many consecutive failures
                if consecutive_failures >= max_consecutive_failures and driver:
                    logger.warning(f"⚠️ {max_consecutive_failures} consecutive failures. Restarting browser...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = launch_edge()
                    authentication_done = False  # Reset authentication flag for new browser
                    consecutive_failures = 0
                
                try:
                    success, driver, authentication_done = process_single_email(
                        email, target_date, position_info, driver, authentication_done
                    )
                    
                    if success:
                        logger.info(f"✅ Successfully processed {position_info}")
                        successful_emails.append((position_from_bottom, email.Subject, email.ReceivedTime))
                        consecutive_failures = 0  # Reset consecutive failures counter
                    else:
                        logger.warning(f"⚠️ Failed to process {position_info}")
                        failed_emails.append((position_from_bottom, email.Subject, email.ReceivedTime))
                        consecutive_failures += 1
                    
                    # Add a delay between emails to ensure browser is stable
                    if i < total_emails:
                        delay = 5  # seconds between emails
                        logger.info(f"Waiting {delay} seconds before processing next email...")
                        time.sleep(delay)
                
                except Exception as e:
                    logger.error(f"⚠️ Catastrophic error processing {position_info}: {e}")
                    logger.error(traceback.format_exc())
                    failed_emails.append((position_from_bottom, email.Subject, email.ReceivedTime))
                    consecutive_failures += 1
                    authentication_done = False  # Reset on catastrophic error
        
        finally:
            # Always quit the driver when done
            if driver:
                try:
                    driver.quit()
                    logger.info("✅ Closed browser instance")
                except:
                    logger.error("⚠️ Error closing browser instance")
        
        # Print summary report
        logger.info("\n" + "="*80)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*80)
        logger.info(f"Total emails processed: {total_emails}")
        logger.info(f"Successfully processed: {len(successful_emails)}")
        logger.info(f"Failed to process: {len(failed_emails)}")
        
        if failed_emails:
            logger.info("\nFAILED EMAILS (Require manual attention):")
            for pos, subject, time in failed_emails:
                logger.info(f"- {ordinal(pos)} from bottom: '{subject}' received at {time.strftime('%H:%M:%S')}")
        
        # Write summary to separate file for quick reference
        summary_file = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w') as f:
            f.write("DITA COMMENT AUTOMATION SUMMARY\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Target date: {target_date}\n")
            f.write(f"Total emails processed: {total_emails}\n")
            f.write(f"Successfully processed: {len(successful_emails)}\n")
            f.write(f"Failed to process: {len(failed_emails)}\n\n")
            
            if failed_emails:
                f.write("FAILED EMAILS (Require manual attention):\n")
                for pos, subject, time in failed_emails:
                    f.write(f"- {ordinal(pos)} from bottom: '{subject}' received at {time.strftime('%H:%M:%S')}\n")
        
        logger.info(f"Summary saved to {summary_file}")
    
    except Exception as e:
        logger.error(f"⚠️ Critical error in main process: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("=" * 80)
    logger.info("DITA COMMENT AUTOMATION COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_single_email()