# Workout video uploader
# Built for Python 2.7

# When executed, this app displays a menu for building up metadata about
# workout videos to send to youtube. Once ready, all videos are uploaded.

import argparse
import os
from os import path
import time
import sys
from functools import partial

class UploadState(object):
    def __init__(self):
        self.day_num = None
        self.day_date = None

    def has_day(self):
        'Returns true if the upload state has a day defined'
        return self.day_num != None and self.day_date != None

    def set_day(self, day_num, day_date):
        self.day_num = day_num
        self.day_date = day_date

class Operations(object):
    def __init__(self, directory):
        # Ensure that directory is a directory
        if not path.isdir(directory):
            raise Exception('Path %s is not a directory!' % directory)
        self.directory = directory

    def get_all_videos(self):
        'Get all videos in directory as a list of file paths'
        return [path.join(self.directory, f)
                for f in os.listdir(self.directory)
                if path.splitext(f)[1].lower() == '.mp4']

    def get_dates(self, video_files):
        'Get all dates for videos given a list of video files'

        dates = []
        for video in video_files:
            date = time.gmtime(path.getmtime(video))

            # Format date to string
            date = time.strftime('%Y-%m-%d', date)

            if date not in dates:
                dates.append(date)

        dates = sorted(dates)

        return dates

def get_exc_msg():
    "Return the current exception's message nicely formatted."

    info = sys.exc_info()
    return 'Exception %s: %s' % (str(info[0]), str(info[1]))

def read_integer(min_ = None, max_ = None):
    '''
    Read an integer from stdin with min_ and max_ as lower and upper limits.
    Defaults to min_=None, max_=None meaning no limits.

    '''

    val = int(sys.stdin.readline())
    if min_ != None and val < min_:
        raise ValueError('Received integer too small. Minimum is %d.' % min_)
    if max_ != None and val > max_:
        raise ValueError('Received integer too large. Maximum is %d.' % max_)
    return val

def while_excepting(callback):
    '''
    While the callback produces exceptions, print message then loop.
    When done, return value returned from callback.

    '''

    while True:
        try:
            return callback()
            break
        except:
            print get_exc_msg()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Workout video upload application.')
    parser.add_argument('directory', default='.', help='Directory to operate upon (videos should be located here).')
    args = parser.parse_args()

    # Initialize operations object
    operations = Operations(args.directory)

    # Enter menu
    done = False
    state = UploadState()
    while not done:
         # Figure out what to do based on upload state
         if not operations.get_all_videos():
            print('No videos in directory %s, leaving.' % operations.directory)

         # If upload state has no day, choose day
         if not state.has_day():
            print('Please choose a date to operate upon:')
            dates = operations.get_dates(operations.get_all_videos())
            for idx in range(len(dates)):
                print('(%d) %s' % (idx, dates[idx]))
            day_date = while_excepting(partial(read_integer, 0, len(dates) - 1))

            print('And which session number is this?')
            day_num = while_excepting(read_integer)

            state.set_day(day_num, day_date)

    print('Done. Workout video uploader exiting.')
