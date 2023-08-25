import sys
import os
import pprint
import datetime
import base64
import re
import time
import logging

import concurrent.futures
import multiprocessing

from dotenv import load_dotenv

from palm_utils import Processor
from workers import GmailWorker, SheetsWorker


load_dotenv()

# Create Workers
gmail_worker = GmailWorker()
sheets_worker = SheetsWorker()
processor = Processor(os.environ.get("API_KEY"))


def main() -> None:
    # Get user input
    days = get_days()

    # Get all emails
    emails = gmail_worker.get_messages(days, "read", "inbox")

    # Creating the sheet
    sheets_worker.create_sheet("jobsheet")

    # Get sheet details
    sheet = sheets_worker.get_sheet_details()
    sheet_id = sheet[0].strip()
    sheet_name = sheet[1].strip()

    # Multiprocessing the emails
    with multiprocessing.Manager() as manager:
        print("Multiprcessing as manager")
        app_categories = manager.dict(
            {
                "application": 0,
                "assessment": 0,
                "interview": 0,
                "offer": 0,
                "rejection": 0,
            }
        )
        locked_range = manager.dict()

        with concurrent.futures.ProcessPoolExecutor(2) as executor:
            results = []

            for email in emails:
                new_entry_lock = manager.Lock()  # Lock for each email
                category_locks = {
                    key: manager.Lock() for key in app_categories
                }  # Lock for each vategory
                results.append(
                    executor.submit(
                        process_email,
                        email,
                        app_categories.copy(),
                        new_entry_lock,
                        category_locks.copy(),
                        locked_range.copy(),
                        sheet_id,
                        sheet_name,
                    )
                )

            # Wait for all processes
            concurrent.futures.wait(results)

            # Print the details of the session
            print("\n- - - - - - - - - - - - - - - - - -\n")
            print(f"{sum(app_categories.values())} updates were made")
            for c in app_categories:
                if app_categories[c] > 0:
                    print(f"{c.upper()}: {app_categories[c]}")
            print("\n- - - - - - - - - - - - - - - - - -\n")


def get_days():
    """
    Gets number of days from user
    """
    days = None

    # Try to get the query details from command line
    if len(sys.argv) == 2:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass

    # Get input from the user
    while not days or not (1 <= days < 50):
        try:
            days = int(input("Enter the number of days to look into: "))
        except ValueError:
            pass

    return days


def process_email(
    email,
    app_categories,
    new_entry_lock,
    category_locks,
    locked_range,
    sheet_id,
    sheet_name,
):
    try:
        details = gmail_worker.get_mail_details(email)

        if details:
            if details["message"] != None:
                # Check if the email is job application related
                if processor.is_app_mail(details["message"]):
                    info = processor.extract_info(details["message"])

                    # Include meta data
                    info["date"] = details["date"]
                    info[
                        "email"
                    ] = f"https://mail.google.com/mail/u/{details['receiver'].strip()}/#inbox/{details['id'].strip()}"

                    # Prepare the data to update the sheets
                    values = list(info.values())

                    # Check existing range
                    prev_range = sheets_worker.get_existing_range(
                        info["company"], info["role"]
                    )

                    # Create new entry if no previous entry
                    if prev_range == None:
                        sheet_new_range = sheets_worker.get_sheet_details()[2].strip()
                        sheets_worker.update_sheet_details(1)
                        new_entry_lock.acquire()
                        try:
                            sheets_worker.update_sheet(
                                sheet_id,
                                sheet_new_range,
                                "USER_ENTERED",
                                values,
                            )

                        finally:
                            new_entry_lock.release()

                    # Update the application entry
                    else:
                        # Check if the value is being updated
                        while True:
                            if prev_range in locked_range:
                                time.sleep(0.1)
                            else:
                                break

                        # Lock.acquire()
                        locked_range[prev_range] = 1

                        # Compare dates to make sure it is the latest message
                        prev_range_values = sheets_worker.get_values(
                            prev_range, sheet_id
                        )
                        date_pattern = (
                            r"(\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} [-+]\d{4})"
                        )
                        prev_date = None

                        for val in prev_range_values:
                            match = re.match(date_pattern, val)
                            if match:
                                prev_date = match.group(1).strip()
                                break

                        # prev_date = prev_range_values[2].strip()

                        if prev_date != None:
                            cur_date = info["date"].strip()
                            cur_date = cur_date

                            date_format = "%a, %d %b %Y %H:%M:%S %z"

                            cur_date = datetime.strptime(cur_date, date_format)
                            prev_date = datetime.strptime(prev_date, date_format)

                            # Dont update if sheet's message is more recent
                            if prev_date > cur_date:
                                category_locks[info["status"].lower().strip()].acquire()
                                app_categories[
                                    info["status"].lower().strip()
                                ] += 1  # Acknowledge the email
                                category_locks[info["status"].lower().strip()].release()
                                return

                        sheets_worker.update_sheet(
                            sheet_id, prev_range, "USER_ENTERED", values
                        )

                        # Lock.release()
                        del locked_range[prev_range]

                    # Update the count
                    category_locks[info["status"].lower().strip()].acquire()
                    app_categories[info["status"].lower().strip()] += 1
                    category_locks[info["status"].lower().strip()].release()

                    # Mark the email read
                    # gmail_worker.mark_read(details["id"].strip())

            else:
                # Inform the user
                print(
                    f'Email couldn\'t be read:\nemail id: {details["id"]}\nsender: {details["sender"]}\n'
                )

        else:
            # Inform the user
            print(f"This email couldn't be read: {email['id']}\n")

    except Exception as e:
        logging.error(e)


def print_session_details(app_categories):
    print("\n- - - - - - - - - - - - - - - - - -\n")
    print(f"{sum(app_categories.values())} updates were made")
    for c in app_categories:
        if app_categories[c] > 0:
            print(f"{c.upper()}: {app_categories[c]}")
    print("\n- - - - - - - - - - - - - - - - - -\n")
    print(app_categories)


if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"The session took: {time.time() - start_time} seconds")
