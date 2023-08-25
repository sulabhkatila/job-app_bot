import google.generativeai as palm
import pprint

import spacy

# python -m spacy download en_core_web_lg

import nltk

# nltk.download('stopwords')
# nltk.download('punkt')

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords


class Processor:
    def __init__(self, API_KEY):
        self.nlp = spacy.load("en_core_web_lg")
        self.sia = SentimentIntensityAnalyzer()

        # PaLM
        palm.configure(api_key=API_KEY)
        models = [
            m
            for m in palm.list_models()
            if "generateText" in m.supported_generation_methods
        ]

        self.model = models[0].name

    def is_app_mail(self, message: str) -> bool:
        """
        Checks of the message is regarding a job application that
        the user has applied to

        PARAMS:
            message: email message

        RETURNS:
            True if the message is regarding a job applicatoin that
            the user applied to else False
        """

        prompt = f"""
        You can answer with only one word: 'Yes' or a 'No'.

        Is the following an email message from a company that the user has applied to (Say yes if it a email message regarding a job application confirmation, or any other update on the job application that the user has applied to):

        {message}
        """
        try:
            completion = palm.generate_text(
                model=self.model,
                prompt=prompt,
                temperature=0,
                # The maximum length of the response
                max_output_tokens=800,
            )

            sentiment_score = self.sia.polarity_scores(completion.result)

            if sentiment_score["compound"] > 0:
                return True
            else:
                return False
        except AttributeError:
            print(completion.result)

    def extract_company_name(
        self, message: str
    ) -> str:  # maybe also add the sender in the paramenters
        """
        Extracts the company name from the message

        PARAMS:
            message: the email message

        RETURNS:
            The company name
        """

        prompt = f"""
        From the following details about an email message, extract the name of the compnay that sent the email (only the name of the company).

        The email message is:

        {message}
        """

        completion = palm.generate_text(
            model=self.model,
            prompt=prompt,
            temperature=0,
            # the maximum length of the response
            max_output_tokens=800,
        )

        return completion.result

    def extract_role_name(self, message: str) -> str:
        """
        Extracts the role name from the message

        PARAMS:
            message: the email message

        RETURNS:
            The role name
        """

        prompt = f"""
        From the following details about an email message, extract the name of the role that the email and application is about (only the name of the role).

        The email message is:

        {message}
        """

        print(message)

        completion = palm.generate_text(
            model=self.model,
            prompt=prompt,
            temperature=0,
            # the maximum length of the response
            max_output_tokens=800,
        )

        return completion.result

    def extract_notes(self, message: str) -> str:
        """
        Extracts any notes from the message

        PARAMS:
            message: the email message

        RETURNS:
            Notes
        """

        prompt = f"""
        From the following email message, determine if there are any important details that the receiver might need to know apart from the name of the company that sent the email and the role the application is about
        Your reaponse can be 20 words max.

        The email message is:

        {message}
        """

        completion = palm.generate_text(
            model=self.model,
            prompt=prompt,
            temperature=0,
            # the maximum length of the response
            max_output_tokens=800,
        )

        return completion.result

    def extract_status(self, message: str) -> str:
        """
        Extracts the company name from the message

        PARAMS:
            message: the email message

        RETURNS:
            The company name
        """

        prompt = f"""
        Given an email message about a job application, extract the status of the application and return one of the following:

        APPLICATION
        REJECTION
        ASSESSMENT
        INTERVIEW
        OFFER


        *APPLICATION is for when the message is about confirmation of the application that was sent to the company.
        *REJECTION is for when the message is about the application being rejected by the company
        *ASSESSMENT is for when the message is about the company giving a assessment (online assessment) for the receipient to complete.
        *INTERVIEW is for when the message is about an interview or a potential interview.
        *OFFER is for when the message is about company accepting the application and offering the position.

        The email message may contain any of the following keywords:

        application
        received
        rejected
        offer
        interview
        opportunity
        assessment

        Here is the message:
        {message}
        """

        completion = palm.generate_text(
            model=self.model,
            prompt=prompt,
            temperature=0,
            # the maximum length of the response
            max_output_tokens=800,
        )

        all_status = {
            "application": 0.0,
            "rejection": 0.0,
            "offer": 0.0,
            "assessment": 0.0,
            "interview": 0.0,
        }

        # get the nouns from the result
        result_nouns = " ".join(
            [
                token.lemma_
                for token in self.nlp(completion.result)
                if token.pos_ == "NOUN"
            ]
        )

        if result_nouns.lower().strip() in all_status:
            return result_nouns.upper().strip()

        for status in all_status:
            all_status[status] = self.nlp(status).similarity(self.nlp(result_nouns))

        res = max(all_status, key=all_status.get)
        return res.upper().strip()

    def extract_info(self, message: str) -> dict:
        """
        Extracts the information and details from the message

        PARAMS:
            message: email message

        RETURNS:
            Details from the message (company name, role name,
            date, notes, and status of the application)
        """

        try:
            info = {}

            info["company"] = self.extract_company_name(message)
            info["role"] = self.extract_role_name(message)
            info["date"] = "X"  # will get updated while processing the email
            info["notes"] = self.extract_notes(message)
            info["email"] = "X"  # will get updated while processing the email
            info["status"] = self.extract_status(message)

            return info

        except Exception as e:
            print(f"An error occured at extract_info: {e}")
            return None
