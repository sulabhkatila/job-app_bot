import re
import os
import os.path
import pprint
import base64
import datetime
import oauth2 as oauth
import email
import spacy


from apiclient import errors
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


from apiclient import errors
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_service(service_type: str, version: str):
    """
    Returns the google api service object

    PARAMS:
        type: type of service object (
                gmail, sheets
                )
        version: version of the service object (
                    v1 for gmail,
                    v4 for sheets
                    )

    RETURNS:
        Google api service object
    """

    try:
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        else:
            creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        service = build(service_type.strip(), version.strip(), credentials=creds)
        return service

    except Exception as e:
        print(f"An error occured at get_service: {e}")


class GmailWorker:
    def __init__(self):
        self.service = get_service("gmail", "v1")

    def get_messages(self, days: int, label: str = None, location: str = None):
        def generate_query(days: int, label: str, location: str) -> str:
            x_days_ago = (
                datetime.datetime.now() - datetime.timedelta(days=days)
            ).strftime("%Y/%m/%d")

            query = f"after:{x_days_ago}"
            if label:
                query += f" label:{label.strip()}"
            if location:
                query += f" in:{location.strip()}"
            return query

        # Get the messages
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=generate_query(days, label, location))
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            print(f"No Emails found in the last {days} days.")
        return messages

    def get_mail_details(self, msg):
        # Call the Gmail API
        txt = self.service.users().messages().get(userId="me", id=msg["id"]).execute()
        payload = txt["payload"]
        headers = payload["headers"]

        # Grab the Subject Line, From and Date from the Email
        for d in headers:
            if d["name"] == "Subject":
                subject = d["value"]
            if d["name"] == "To":
                receiver = d["value"]
            if d["name"] == "From":
                sender = d["value"]
                try:
                    match = re.search(r"<(.*)>", sender).group(1)
                except:
                    match = sender
            if d["name"] == "Date":
                date = d["value"][:31]
                
        def get_body(payload):
            if "body" in payload and "data" in payload["body"]:
                return payload["body"]["data"]
            elif "parts" in payload:
                for part in payload["parts"]:
                    data = get_body(part)
                    if data:
                        return data
            else:
                return None

        data = get_body(payload)

        if data:
            data = data.replace("-", "+").replace("_", "/")
            decoded_data = base64.b64decode(data).decode("UTF-8")
            decoded_data = (decoded_data.encode("ascii", "ignore")).decode("UTF-8")
            decoded_data = (
                decoded_data.replace("\n", "").replace("\r", "").replace("\t", "")
            )

            print(len(date))

            return {
                "subject": subject,
                "id": msg["id"],
                "sender": sender,
                "receiver": receiver,
                "date": date,
                "message": decoded_data,
            }

        return None

    def mark_read(self, message_id: str) -> None:
        """
        Marks the email as read

        PARAMS:
            message_id: id of the email

        RETURNS:
            None
        """

        try:
            message = (
                self.service.users()
                .messages()
                .modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]})
                .execute()
            )

        except Exception as e:
            print(f"An error occurred while marking the email {message_id} read: {e}")


class SheetsWorker:
    def __init__(self):
        self.service = get_service("sheets", "v4")
        self.nlp = spacy.load("en_core_web_lg")

    def create_sheet(self, title: str) -> None:
        """
        Creates a Google sheet

        PARAMS:
            title: name for the google sheet

        RETURNS:
            None
        """

        if (
            not self.get_sheet_details()
            or self.get_sheet_details()[1].strip() != title.strip()
        ):
            try:
                spreadsheet = {"properties": {"title": title}}
                spreadsheet = (
                    self.service.spreadsheets()
                    .create(body=spreadsheet, fields="spreadsheetId")
                    .execute()
                )
                print(f"Spreadsheet ID: {(spreadsheet.get('spreadsheetId'))}")

                self.update_sheet(
                    spreadsheet.get("spreadsheetId"),
                    "A1:F1",
                    "USER_ENTERED",
                    ["Company", "Role", "Date", "Notes", "Most Recent Email", "Status"],
                )

                with open("app_sheet.txt", "w") as sheet:
                    sheet.write(
                        f'{spreadsheet.get("spreadsheetId")}\n{title}\n{"A2:F2"}'
                    )

            except HttpError as error:
                print(f"An error occurred at create_sheet: {error}")
                return error
        return

    def get_sheet_details(self) -> list:
        """
        Returns the details of the google sheets

        PARAMS:
            None

        RETURNS:
            Details of the google sheets
        """

        if os.path.exists("app_sheet.txt"):
            with open("app_sheet.txt", "r") as file:
                details = file.readlines()
                return details
        return None

    def update_sheet_details(self, n: int) -> None:
        """
        Updates the application sheet detail file (app_sheet.txt)

        PARAMS:
            n: The number of new columns added in the sheets

        RETURNS:
            None
        """

        with open("app_sheet.txt", "r+") as file:
            lines = file.readlines()
            file.seek(0)

            for line in lines:
                if ":" in line:
                    col_start, col_end = line[0], line[-2]

                    row1 = str(int(line[1]) + n)
                    row2 = str(int(line[-1]) + n)
                    line = f"{col_start}{row1}:{col_end}{row2}"

                file.write(line)

    def get_existing_range(self, company: str, role: str) -> str:
        """
        Returns the existing range for given values

        PARAMS:
            company: id of the email

        RETURNS:
            Range for the values
        """

        # call the sheets api
        try:
            sheet_details = self.get_sheet_details()
            range_end = str(int(sheet_details[2][-1]) - 1)

            range_names = [f"A2:B{range_end}"]

            result = (
                self.service.spreadsheets()
                .values()
                .batchGet(spreadsheetId=sheet_details[0].strip(), ranges=range_names)
                .execute()
            )
            ranges = result.get("valueRanges", [])
            values = ranges[0]["values"]

            rows = len(values)
            cols = len(values[0])
            for r in range(rows):
                for c in range(0, cols, 2):
                    if (
                        values[r][c].lower().strip() == company.lower().strip()
                        and self.nlp(values[r][c + 1].lower().strip()).similarity(
                            self.nlp(role.lower().strip())
                        )
                        > 0.8
                    ):
                        # # #
                        row = r + 2
                        col_end = sheet_details[-1][-2]
                        range_val = f"A{row}:{col_end}{row}"

                        return range_val  # previously :: return (r + 2)
            return None

        # except HttpError as error:
        except Exception as e:
            print(f"An error occured at get_existing_range: {e}")
            pass

    def update_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        value_input_option: str,
        val: list,
    ) -> None:
        """
        Updates the sheet with given data

        PARAMS:
            range_name: the range to update
            value_input_option: input value for data interpretation
            val: the values to update the range with

        RETURNS:
            None
        """

        # range_name = A1: E1
        # pylint: disable=maybe-no-member
        try:
            # service = build("sheets", "v4", credentials=creds)
            values = [val]
            body = {"values": values}
            result = (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
            return result
        except HttpError as error:
            print(f"An error occurred at update_sheet: {error}")
            return error

    def get_values(self, range_name: str, spreadsheet_id: str) -> list:
        """
        Returns the values in the given range

        PARAMS:
            range: range to read values from

        RETURNS:
            List of values in the provided range
        """

        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            rows = result.get("values", [])
            print(f"{len(rows)} rows retrieved")
            return result
        except HttpError as error:
            print(f"An error occurred at get_values: {error}")
            return error
