#!/usr/bin/python

import httplib
import httplib2
import os
import random
import sys
import time
from os import path
from tempfile import NamedTemporaryFile

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, httplib.NotConnected,
    httplib.IncompleteRead, httplib.ImproperConnectionState,
    httplib.CannotSendRequest, httplib.CannotSendHeader,
    httplib.ResponseNotReady, httplib.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = """\
Could not open client secrets file. For more information see
https://console.developers.google.com/
and
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets"""
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

class Youtube(object):
    '''
    Youtube service api.
    Meant to be used with the 'with' statement.
    See http://stackoverflow.com/a/865272/1359232

    '''

    def __init__(self, client_secrets_path):
        if not os.path.isfile(client_secrets_path):
            raise ValueError('Could not find client secrets file %s' %
                client_secrets_path)

        self.client_secrets_path = client_secrets_path
        self.temp_path = None
        self.service = None

    def __enter__(self):
        # Ensure that we have not re-entered
        if self.temp_path != None or self.service != None:
            raise Exception('Cannot use multiple nested with blocks on same Youtube object!')

        flow = flow_from_clientsecrets(
            self.client_secrets_path,
            scope=YOUTUBE_UPLOAD_SCOPE,
            message=MISSING_CLIENT_SECRETS_MESSAGE)

        temp_file = NamedTemporaryFile(delete=False)
        self.temp_path = temp_file.name
        temp_file.close()

        storage = Storage(self.temp_path)
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(
                flow, storage, argparser.parse_args(list())
            )

        self.service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
            http=credentials.authorize(httplib2.Http()))

        return self

    def __exit__(self, type, value, traceback):
        # Ensure that we have not become corrupt
        if not self.temp_path or not self.service:
            raise Exception('Exiting with block without a temp_path!')
        os.unlink(self.temp_path)
        self.temp_path = None
        self.service = None

    def _require_engaged(self):
        if not self.service:
            raise Exception('Youtube object cannot be used outside of "with" block')

    def videos_insert(self,
        video_file_path,
        title,
        description='',
        tags=list(),
        categoryId=22,
        privacyStatus='unlisted',
    ):
        '''
        Upload a file. Return response.

        '''

        self._require_engaged()

        body=dict(
            snippet=dict(
                title=title,
                description=description,
                tags=tags,
                categoryId=categoryId
            ),
            status=dict(
                privacyStatus=privacyStatus
            )
        )

        # Call the API's videos.insert method to create and upload the video.
        insert_request = self.service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_file_path, chunksize=-1, resumable=True)
        )

        return self._resumable_upload(insert_request)

    def _resumable_upload(self, insert_request):
        '''
        This method implements an exponential backoff strategy to resume a
        failed upload.

        '''
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                print "Uploading file..."
                status, response = insert_request.next_chunk()
                if 'id' in response:
                    print "Video id '%s' was successfully uploaded." % response['id']
                    return response
                else:
                    raise Exception(
                        "The upload failed with an unexpected response: %s" % response
                    )
            except HttpError, e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                        e.content)
                else:
                    raise
            except RETRIABLE_EXCEPTIONS, e:
                error = "A retriable error occurred: %s" % e

        if error is not None:
            print error
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print "Sleeping %f seconds and then retrying..." % sleep_seconds
            time.sleep(sleep_seconds)
