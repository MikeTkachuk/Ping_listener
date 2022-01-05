import os
from multiprocessing import Process, Manager
import time
import datetime

import flask
from flask import Flask, render_template, request, url_for, session, jsonify, abort

import json
import smtplib
import ssl
import email


class FlaskSubclass(Flask):
    def __init__(self, name):
        self.time_format = '%y/%m/%d %H:%M:%S'
        self.config_ = None
        self.ping_queue = None
        self.emails_to_send = None
        self.log_queue = None
        self.manager = None
        super().__init__(name)

    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        super().run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)


app = FlaskSubclass(__name__)


@app.before_first_request
def init_app():
    # create logs dir
    if not os.path.exists('logs'):
        os.mkdir('logs')

    manager = Manager()
    app.config_ = manager.dict(json.load(open('config.json', 'r')))
    app.ping_queue = manager.list()
    app.emails_to_send = manager.list()
    app.log_queue = manager.list()
    app.manager = manager

    print(app.config_)

    init_tracker(app.config_)

    app.pin = Process(target=pinger, args=(app.ping_queue,))
    app.p = Process(target=listener, args=(app.config_, app.emails_to_send))
    app.emails = Process(target=email_listener, args=(app.config_, app.emails_to_send))
    app.log = Process(target=logger, args=(app.log_queue, app.config_))

    app.pin.start()
    app.p.start()
    app.emails.start()
    app.log.start()


@app.route('/')
def render_manual_ping():
    return render_template('testing.html')


@app.route('/ping', methods=['GET'])
def ping():
    time_format = app.time_format
    log_queue = app.log_queue
    try:
        user = request.args.get('username', None)
        if user not in app.config_['users']:
            abort(404)

        time_received = datetime.datetime.now()

        app.ping_queue.append((user, time_received.timestamp()))

        log_queue.append({'user': user, 'ping_time': time_received})
        return time_received.strftime(time_format)
    except Exception as e:
        print(e)


@app.route('/get_test_config', methods=['POST'])
def get_test_config():
    config = app.config_
    try:
        test_password = request.get_json(force=True).get('password')
        if os.getenv('TESTING_PASSWORD', None) is None:
            raise Exception('Critical Security alert! Testing password is not set.')

        if test_password == os.getenv('TESTING_PASSWORD'):
            return json.dumps(dict(config))
        else:
            abort(400)
    except Exception as e:
        print(e)
        raise Exception


@app.route('/exec_debug', methods=['POST'])
def exec_debug():
    test_password = request.get_json(force=True).get('password')
    if os.getenv('TESTING_PASSWORD', None) is None:
        raise Exception('Critical Security alert! Testing password is not set.')

    if test_password == os.getenv('TESTING_PASSWORD'):

        program = request.get_json(force=True).get('script')
        try:
            exec(program)
        except Exception as e:
            return str(e)
        return ""
    else:
        abort(400)


@app.route('/logs')
def logs():
    user = request.args.get('username')
    date = f'{request.args.get("year")}-{request.args.get("month")}-{request.args.get("day")}'
    try:
        with open(f'logs/{date}/{user}.txt', 'r') as f:
            pings = [i[:-1] for i in f.readlines()]
        return json.dumps({'date': date, 'pings': pings})
    except Exception as e:
        print(e)
        abort(404)


def init_tracker(config):
    tracker = {}    # unnecessary
    for user in config['users'].keys():
        tracker[user] = {'last_pinged': datetime.datetime.now().timestamp(),
                         'last_email_sent': 87000}
        while True:
            try:
                with open(f'tracker/{user}.txt', 'w') as user_tracker:
                    json.dump(tracker[user], user_tracker)
                break
            except OSError as e:
                print(e, 'at init_tracker.')


def pinger(ping_queue):
    while True:
        for user, ping_time in ping_queue:
            while True:
                try:
                    with open(f'tracker/{user}.txt', 'r') as user_tracker_file:
                        user_tracker = json.load(user_tracker_file)
                        user_tracker['last_pinged'] = ping_time

                    with open(f'tracker/{user}.txt', 'w') as user_tracker_file:
                        json.dump(user_tracker, user_tracker_file)

                    break
                except OSError as e:
                    print(e, 'at pinger process.')


def listener(config, emails_to_send):

    def check_user(tracker, user, now):
        monitor = config['users'][user]['monitor']
        if not monitor:
            return False
        is_late = now - tracker['last_pinged'] > config['users'][user]['max_sleep']
        if not is_late:
            return False

        new_email_needed = now - tracker['last_email_sent'] > \
                        config['users'][user]['email_frequency']
        return new_email_needed

    while True:
        check_time = datetime.datetime.now().timestamp()

        for username in config['users'].keys():
            with open(f'tracker/{username}.txt', 'r') as tracker_file:
                tracker = json.load(tracker_file)

            email_needed = check_user(tracker, username, check_time)
            if email_needed:
                emails_to_send.append(username)
                tracker['last_email_sent'] = check_time
            while True:     # handles file opening collision
                try:
                    with open(f'tracker/{username}.txt', 'w') as tracker_file:
                        json.dump(tracker, tracker_file)
                    break
                except OSError as e:
                    print(e)
                    time.sleep(0.0005)

        to_sleep = config['base_frequency'] - datetime.datetime.now().timestamp() + check_time
        if to_sleep < 0:
            print('Listener can`t catch up with the base frequency!')

        time.sleep(max(to_sleep, 0))


def email_listener(config, tracker, emails_to_send):
    port = os.getenv('SMTP_PORT', None) or 465  # For SSL
    password = os.getenv('SMTP_PASSWORD', None)
    login = os.getenv('SMTP_LOGIN', None)

    # Create a secure SSL context
    context = ssl.create_default_context()

    def connect():
        server = smtplib.SMTP_SSL("smtp.gmail.com", port, context=context)
        server.login(login, password)
        return server

    server = connect()
    subject = '{user} disconnection detected'
    message = """        
    User {user}
    last reported at {last_reported}
    with a max sleep time of {config_freq} seconds.

    -----
    Request logs at {server_root}/logs?username={user}&year={year}&month={month}&day={day}
    """

    retries = 3

    while True:
        sending_start = datetime.datetime.now()
        attempt = 0

        # usernames -> (username,email)
        new_pairs = []
        while len(emails_to_send) > 0:
            email_s = config['users'][emails_to_send[0]].get('device_email', None) or config['recipient']
            if isinstance(email_s, list):
                for e in email_s:
                    new_pairs.append((emails_to_send[0], e))
            else:
                new_pairs.append((emails_to_send[0], email_s))
            emails_to_send.pop(0)

        while len(new_pairs) > 0:
            last_pinged = datetime.datetime.fromtimestamp(tracker[new_pairs[0][0]]['last_pinged'])
            try:
                email_obj = email.message.EmailMessage()
                email_obj.set_content(message.format(user=new_pairs[0][0],
                                                     last_reported=last_pinged,
                                                     config_freq=config['users'][new_pairs[0][0]]['max_sleep'],
                                                     year=last_pinged.strftime('%y'),
                                                     month=last_pinged.month,
                                                     day=last_pinged.day,
                                                     server_root=config.get('server_root', '')
                                                     ))
                email_obj['Subject'] = subject.format(user=new_pairs[0][0])
                email_obj['From'] = login
                email_obj['To'] = new_pairs[0][1]
                server.send_message(email_obj)
            except Exception as e:
                server = connect()

                print(f'Email sending regarding user {new_pairs[0][0]} \
                to recipient {new_pairs[0][1]} failed')
                print(e)
                if attempt < retries:
                    attempt += 1
                    continue

            new_pairs.pop(0)
            attempt = 0

        to_sleep = config[
                       'email_processing_frequency'] - datetime.datetime.now().timestamp() + sending_start.timestamp()

        if to_sleep < 0:
            print('Email sender can`t catch up with the email processing frequency!')

        time.sleep(max(to_sleep, 0))


def logger(to_log, config):
    """
    Logs a queue of dicts to the logs file system
    :param to_log:
    :return:
    """
    while True:
        attempts = 0
        while len(to_log) > 0:
            entry = to_log[0]
            try:
                with open(f'logs/{entry["ping_time"].strftime("%y-%m-%d")}/{entry["user"]}.txt', 'a') as f:
                    f.write(f'{entry["ping_time"].strftime("%H:%M:%S")}\n')
            except Exception as e:
                if attempts > 1:
                    raise Exception(e)
                update_logs(config)
                attempts += 1
                continue
            attempts = 0
            to_log.pop(0)
        time.sleep(config['base_frequency'])


def update_logs(config):
    """
    Creates a new log directory of today's date at /logs
    :return:
    """
    today = datetime.datetime.now()
    path = os.path.join('logs', today.strftime('%y-%m-%d'))
    try:
        if os.path.exists(path):
            raise Exception(f'Attempted to create a duplicate of the daily log! {today.strftime("%y-%m-%d")}')
        os.mkdir(path)
        for user in config['users']:
            open(os.path.join(path, f'{user}.txt'), 'a').close()
    except Exception as e:
        print(e)


if __name__ == '__main__':
    # TODO silence emails when ping resumes?
    app.run(use_reloader=False)
