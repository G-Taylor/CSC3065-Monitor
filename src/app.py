import time
import json
import flask
import requests

from datetime import datetime
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from function_list import FUNCTIONS, PROXIES
from flask import Flask, request, render_template
from essential_generators import DocumentGenerator

# scheduler to run the monitor checks
sched = APScheduler()
app = Flask(__name__)

@sched.task("interval", id="do_monitor_checks", minutes=60, misfire_grace_time=900)
@app.route("/")
def home():
    with sched.app.app_context():
        gen = DocumentGenerator()
        results = []
        total_time_for_monitor = 0
        test_num = 0
        last_ran = datetime.now()
        proxy = get_proxy()

        # loop through the external functions file and test each function type with a random string
        for func in FUNCTIONS:
            counter = 0
            # Do 5 tests per function
            while counter < 5:
                sentence = gen.sentence()   # generate a random sentence to test the function
            
                # Time how long each test takes, and record total time for all functions
                start_time = time.time()
                requestURL = f"{proxy}/?func={func}&text={sentence}"
                response = requests.get(requestURL)
                end_time = time.time()
                total = end_time - start_time

                # format the response so it can be represented as a dictionary
                content = response.content
                json_content = json.loads(content)

                # create result entry for each test
                result = {
                    "function": func,
                    "test": test_num,
                    "sentence": sentence,
                    "answer": json_content['answer'],
                    "time": total,
                    "response": response.status_code,
                    "error": json_content['error']
                }

                # Check if an alert email needs to be sent for a bad response
                if response.status_code != 200:
                    monitor_alert(response.status_code)
                
                results.append(result)
                total_time_for_monitor += total
                counter += 1
                test_num += 1

        print ("scheduler running")
        # return the results and timing details to the index template
        return render_template("/index.html", results=results, duration=total_time_for_monitor, last_ran=last_ran)

# method that returns a working proxy
def get_proxy():
    for proxy in PROXIES:
        response = requests.get(PROXIES[proxy])
        if response.status_code == 200:
            print(f"Using proxy: {proxy}")
            return PROXIES[proxy]


# method to send an email alert to desired recipients if any code other than 200 is reported
def monitor_alert(status):

    # configure details for the GMail alerting service
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 465
    app.config["MAIL_USE_SSL"] = True
    app.config["MAIL_USERNAME"] = 'editorqub@gmail.com'
    app.config["MAIL_PASSWORD"] = 'Str0ngP4ssword!'

    mail = Mail(app)

    # The message that will be sent when a bad response is detected
    msg = Message('System Monitoring Issue', sender = 'Automated Monitoring', recipients = ['editorqub@gmail.com'])
    msg.body = f"Monitoring has encountered a {status} status code, please check ASAP"
    mail.send(msg)


if __name__ == '__main__':
    sched.init_app(app)
    sched.start()
    app.run(host = '0.0.0.0', debug=False)