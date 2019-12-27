# Get messages from gmail
# Marakulin Andrey @annndruha
# 2020

import re
import os.path
import base64
import email

import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


CREDINTIALS_PATH = './secret/credentials.json'
TOKEN_PATH = './secret/token.pickle'
DATA_PATH = './temp/'

def auth():
    """
    Create a credentials file requested premissions in
    your browser, after that create a token to execute api commands.
    """
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDINTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service


def GetSimpleText(data):
    """
    Encoding email message text from bytes format
    and clear html tags. Cut message reply part.
    """
    bytes = base64.urlsafe_b64decode(data.encode('UTF-8'))
    text = bytes.decode('utf-8')
    cleantext = re.sub(r'{.*?}', '', re.sub(r'<.*?>', '', re.sub (r' +', ' ', re.sub(r"\n+", '\n', re.sub(r" \n", '\n', text)))))

    if cleantext.find('&')>=0:
        cleantext = cleantext.split('&')[0]
        cleantext += '\nПродолжение читать в источнике...'

    return cleantext

def GetAttachments(service, user_id, msg_id, store_dir, message):
    """
    Download attachments to DATA_PATH if exists.
    Return text if exist with attachments.
    """
    try:
        text = None
        for part in message['payload']['parts']:
            if part['filename']: # In this case downloads attachments

                attach_id = part['body']['attachmentId']
                attach = service.users().messages().attachments().get(userId='me', messageId = msg_id, id=attach_id).execute()
                data = attach['data']
                bytes = base64.urlsafe_b64decode(data.encode('UTF-8'))

                path = ''.join([store_dir, part['filename']])
                with open(path, 'wb') as f:
                    f.write(bytes)
                    f.close()

            else: # In this case (only text) parse text 
                data = part['body']['data']
                text = GetSimpleText(data)
                
    except  BaseException as err:
        print(err.args)
    return text

def get_message(service, msg_id):
    """
    Main function to get message, attachments and metadata.
    Call download attach func and return message text with metadata.
    """
    message = service.users().messages().get(userId='me', id=msg_id).execute() # Get info about last message
    MIME_type = message['payload']['mimeType']


    # Select type of email message
    if MIME_type == 'multipart/mixed':
        text = GetAttachments(service, 'me', msg_id, DATA_PATH, message)

    elif MIME_type == 'text/html':
        data = message['payload']['body']['data']
        text = GetSimpleText(data)

    elif MIME_type == 'text/plain': # If in message only theme
        text = None

    else:
        text = 'прислал(а) сообщение, но его тип не поддерживает пересылку. Проверьте почту.'

    # Combine different kinds of text to send
    message_to_vk = ''
    theme = None
    sender = None
    for d in message['payload']['headers']:
        if d['name'] == 'Subject':
            theme = d['value']
        if d['name'] == 'From':
            sender = d['value']
    if sender is not None:
        message_to_vk += sender + '\n'
    if theme is not None:
        message_to_vk += theme + '\n'
    if text is not None:
        message_to_vk += text

    return message_to_vk