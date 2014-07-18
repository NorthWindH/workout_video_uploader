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
from youtube import Youtube

VALID_EXERCISES = [
    'squat',
    'bench press',
    'overhead press',
    'neutral pull up',
    'deadlift'
]

class Entry(object):
    def __init__(self,
            video_file=None,
            exercise=None,
            set=None,
            reps=None,
            weight=None,
            day_num=None,
            day_date=None
        ):
        self.video_file = video_file

        if exercise != None and exercise not in VALID_EXERCISES:
            raise ValueError('Invalid exercise %s' % exercise)
        self.exercise = exercise

        if set != None and set != 'warmup' and type(set) != int:
            raise ValueError('Invalid set %s' % str(set))
        self.set = set

        if reps != None and (type(reps) != int or reps <= 0):
            raise ValueError('Invalid reps %s' % str(reps))
        self.reps = reps

        if weight != None and (type(weight) != int or weight <= 0):
            raise ValueError('Invalid weight %s' % str(weight))
        self.weight = weight

        if day_num != None and (type(day_num) != int or day_num < 0):
            raise ValueError('Invalid day_num %s' % str(day_num))
        self.day_num = day_num

        if day_date != None and (type(day_date) != str or not day_date):
            raise ValueError('Invalid day_date %s' % str(day_date))
        self.day_date = day_date

    def __str__(self):
        if self.set == 'warmup':
            return 'day %d %s warmup %s' % (
                self.day_num, self.exercise, self.day_date
            )
        else:
            return 'day %d %s set %d %dx%d %s' % (
                self.day_num, self.exercise, self.set, self.reps, self.weight,
                self.day_date
            )

    def __repr__(self):
        return str(self)

    def get_tags(self):
        tags = list()
        tags.extend(
            {
                'bench press': ['Bench Press'],
                'overhead press': ['Overhead Press'],
                'squat': ['Squat'],
                'deadlift': ['Deadlift'],
                'neutral pull up': ['Pull-up']
            }[self.exercise]
        )

        if self.set == 'wamup':
            tags.append('Warming Up')
        return tags

    def valid_file(self):
        return path.isfile(self.video_file)

class UploadState(object):
    def __init__(self):
        self.day_num = None
        self.day_date = None
        self.entries = list()

    def has_day(self):
        'Return true if the upload state has a day defined'
        return self.day_num != None and self.day_date != None

    def set_day(self, day_num, day_date):
        self.day_num = day_num
        self.day_date = day_date

    def add_entry(self, entry):
        if type(entry) != Entry:
            raise ValueError('Can only add Entry objects. Got %s.' % str(type(entry)))
        self.entries.append(entry)

    def get_exercises(self):
        'Return a list of the exercises currently registered.'

        exercises = list()
        for entry in self.entries:
            if entry.exercise != None and entry.exercise not in exercises:
                exercises.append(entry.exercise)
        return exercises

    def get_entries(self):
        return self.entries

    def get_videos(self):
        'Return a list of the video files currently registered.'

        videos = list()
        for entry in self.entries:
            if entry.video_file != None and entry.video_file not in videos:
                videos.append(entry.video_file)
        return videos

    def serialize(self):
        return ''

    def deserialize(self):
        return ''

class Operations(object):
    def __init__(self, directory):
        # Ensure that directory is a directory
        if not path.isdir(directory):
            raise Exception('Path %s is not a directory!' % directory)
        self.directory = directory

    def get_state(self):
        'Generate a state either from a file or get a new one.'
        return UploadState()

    def save_state(self, state):
        'Save an upload state to directory or current directory.'
        pass

    def get_all_videos(self):
        'Get all videos in directory as a list of file paths.'
        return [path.join(self.directory, f)
                for f in os.listdir(self.directory)
                if path.splitext(f)[1].lower() == '.mp4']

    def get_day_videos(self, day_date):
        '''
        Get all videos in directory as a list of file paths if modified on given day_date.
        day_date should be string in format YYYY-MM-DD.

        '''

        return [v for v in self.get_all_videos() if self.get_date(v) == day_date]

    def sort_videos_by_mtime(self, video_files):
        'Sort a list of video files in ascending order by the modification time.'
        return sorted(video_files, key=lambda e: path.getmtime(e))

    def get_date(self, video_file):
        return time.strftime('%Y%m%d', time.gmtime(path.getmtime(video_file)))

    def get_dates(self, video_files):
        'Get all dates for videos given a list of video files'

        dates = []
        for video in video_files:
            date = self.get_date(video)

            if date not in dates:
                dates.append(date)

        dates = sorted(dates)

        return dates

def get_exc_msg():
    "Return the current exception's message nicely formatted."

    info = sys.exc_info()
    return 'Exception: %s' % str(info[1])

def read_str():
    return sys.stdin.readline().strip()

def read_integer(min_=None, max_=None, default=None):
    '''
    Read an integer from stdin with min_ and max_ as lower and upper limits.
    Defaults to min_=None, max_=None meaning no limits.

    '''

    val = read_str()
    if not val and default != None:
        val = default
    else:
        val = int(val)

    if min_ != None and val < min_:
        raise ValueError('Received integer too small. Minimum is %d.' % min_)
    if max_ != None and val > max_:
        raise ValueError('Received integer too large. Maximum is %d.' % max_)
    return val

def read_menu(entries, default=None):
    for idx in range(len(entries)):
        print('(%d) %s' % (idx, entries[idx]))
    choice = read_integer(0, len(entries) - 1, default=default)
    return entries[choice]

def read_bool(default=None):
    val = read_str()
    if not val and default != None:
        val = default
    if val == 'y' or val == 'yes':
        return True
    if val == 'n' or val == 'No':
        return False
    raise ValueError('Expected boolean value ie yes/y, no/n.')

def enum_constraint(callback, vals):
    val = callback()
    if val not in vals:
        raise ValueError('Invalid value. Must be one of %s.' % ', '.join(vals))
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

def next_video(video_list):
    if video_list:
        print('Next file: %s' % path.basename(video_list[0]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Workout video upload application.')
    parser.add_argument('directory', default='.', help='Directory to operate upon (videos should be located here).')
    parser.add_argument('--client-secrets', default='client_secrets.json', help='Client secrets file. See https://developers.google.com/api-client-library/python/guide/aaa_client_secrets')
    args = parser.parse_args()

    # Initialize operations object
    operations = Operations(args.directory)

    # Enter menu
    done = False
    do_upload = False
    current_exercise = None
    state = operations.get_state()

    while not done:
        print('\nOperating on %s' % operations.directory)

        # If upload state has no day, choose day
        if not state.has_day():
            print('Please choose a date to operate upon:')
            dates = operations.get_dates(operations.get_all_videos())
            day_date = while_excepting(partial(read_menu, dates))

            print('And which session number is this?')
            day_num = while_excepting(read_integer)
            state.set_day(day_num, day_date)

        exercises = state.get_exercises()
        if exercises:
            print('Exercises added: %s' % ', '.join(exercises))

        # Assemble videos that could still be registered
        videos_remaining = set(operations.get_day_videos(state.day_date))
        videos_remaining -= set(state.get_videos())
        videos_remaining = operations.sort_videos_by_mtime(list(videos_remaining))

        print('Videos remaining: %d' % len(videos_remaining))

        print('What would you like to do?')
        choices = ['upload to youtube']
        if videos_remaining:
            choices.insert(0, 'add exercise')
        choice = while_excepting(partial(read_menu, choices))

        if choice == 'add exercise':
            if not videos_remaining:
                print('No video files.')
                continue

            print('Exercise?')
            exercise_choices = [e for e in VALID_EXERCISES if e not in exercises]
            exercise = while_excepting(partial(read_menu, exercise_choices))

            next_video(videos_remaining)
            print('Warmup?')
            if while_excepting(read_bool):
                entry = Entry(
                    video_file=videos_remaining[0],
                    exercise=exercise,
                    set='warmup',
                    day_num=state.day_num,
                    day_date=state.day_date
                )
                state.add_entry(entry)
                videos_remaining.pop(0)
                print('Added "%s"' % str(entry))

            if videos_remaining:
                print('Weight?')
                weight = while_excepting(partial(read_integer, min_=1, max_=600))
                print('Sets? default: 4')
                sets = while_excepting(partial(read_integer,
                    min_=1, max_=len(videos_remaining), default=4))
                print('Reps? default: 6')
                reps = while_excepting(partial(read_integer,
                    min_=1, default=6))

                for idx in range(sets):
                    next_video(videos_remaining)
                    print('Set %d reps? default: %d' % (idx + 1, reps))
                    set_reps = while_excepting(partial(read_integer, min_=1, default=reps))
                    print('Set %d weight? default: %d' % (idx + 1, weight))
                    set_weight = while_excepting(partial(read_integer, min_=1, default=weight))
                    entry = Entry(
                        videos_remaining[0],
                        exercise,
                        idx + 1,
                        set_reps,
                        set_weight,
                        state.day_num,
                        state.day_date
                    )
                    state.add_entry(entry)
                    videos_remaining.pop(0)
                    print('Added "%s"' % str(entry))

        elif choice == 'upload to youtube':
            done = True
            print('Uploading...')
            with Youtube(args.client_secrets) as youtube:
                responses = list()
                for entry in state.entries:
                    print 'Processing "%s"' % str(entry)
                    responses.append(youtube.videos_insert(
                        entry.video_file,
                        str(entry),
                        entry.get_tags()
                    ))

            print('Delete files?')
            delete_files = while_excepting(read_bool)

            if delete_files:
                for entry in state.entries:
                    print('Deleting %s' % entry.video_file)
                    os.unlink(entry.video_file)
            print('Files deleted.')
        else:
            print('Unknown choice "%s".' % choice)

    print('Done. Workout video uploader exiting.')
