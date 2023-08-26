# Job Application Tracker

Welcome to the **Job Application Tracker** project! This Python program aims to revolutionize your job application process by automating the tracking and management of job applications. During peak application seasons, it has the potential to save an average of 2 hours per week, enabling you to focus more on preparing for interviews and networking.

## Features

- **OAuth Authentication**: Securely authenticate your account using OAuth to ensure your application data is handled with care.
- **Integration with PaLM and Google Cloud API**: Seamlessly integrate with PaLM API and Google Cloud API to automate the extraction of job application details and the updating of application statuses in Google Sheets.
  

## How to Set It Up

Given the current development status, the setup process is longer than what will be for the final version. However, if you're interested in exploring the early version of the Job Application Tracker, follow these instructions to set it up:

To set up the Job Application Tracker, follow these steps:

1. **Clone the Project**: Clone this repository to your local machine.

2. **Create a Google Cloud Projects**: [Create a project in Google Cloud Console](https://developers.google.com/workspace/guides/create-project).

3. **Enable APIs**: Enable the Gmail API and Google Sheets API for your project. Here's a guide on how to [enable APIs in Google Cloud Console](https://developers.google.com/workspace/guides/enable-apis).

4. **Create and Download Credentials**: [Download the `credentials.json` file](https://developers.google.com/workspace/guides/create-credentials) after enabling APIs. This file contains the necessary credentials for the application to access Google APIs.

5. **Place Credentials File**: Move the downloaded `credentials.json` file to the root directory of the cloned project.

6. **PaLM API**: Obtain the [PaLM API](https://developers.generativeai.google/).

7. **Environment Variable**: Create a .env file and add your PaLM API key in the file. 
  ```
    API_KEY = 'your_api_key'
  ```

8. **Install Requirements**: Run `pip install -r requirements.txt` to install the required Python dependencies.

9. **Download required NLP resources**:
   - Download the large English language model for spaCy by running: `python -m spacy download en_core_web_lg`
   - Download NLTK stopwords and punkt resources using: `nltk.download('stopwords')` and `nltk.download('punkt')`

10. **Run the Program**: Execute the program using `python main.py`. Follow the prompts for authentication and usage.

Your contribution during this development phase will greatly help improve the Job Application Tracker.

For any feedback, feel free to reach out to us at `kailasulabht@gmail.com`. 
Thank you for your interest and support towards a more efficient job hunting experience!

---
**Note**: As of now, the application is under active development and is not expected to work perfectly. Your understanding and feedback are greatly appreciated.






