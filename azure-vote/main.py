from flask import Flask, request, render_template
import os
import random
import redis
import socket
import sys
import logging
from datetime import datetime


# App Insights
# TODO: Import required libraries for App Insights
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.ext.azure.log_exporter import AzureEventHandler

# Logging
# TODO: Setup logger
logger = logging.getLogger(__name__)
loggerEvent = logging.getLogger(__name__)
loggerEvent.addHandler(AzureEventHandler(
   connection_string='InstrumentationKey=705f49e9-1faf-4461-9467-b0ed5e0bd64a')
)
loggerEvent.setLevel(logging.WARNING)

logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=705f49e9-1faf-4461-9467-b0ed5e0bd64a')
)
logger.setLevel(logging.WARNING)

# Metrics
exporter = metrics_exporter.new_metrics_exporter(
  enable_standard_metrics=True,
  connection_string='InstrumentationKey=705f49e9-1faf-4461-9467-b0ed5e0bd64a')

# Tracing
tracer = Tracer (
    exporter = AzureExporter (
        connection_string = 'InstrumentationKey=705f49e9-1faf-4461-9467-b0ed5e0bd64a'),
        sampler = ProbabilitySampler(1.0),
)

app = Flask(__name__)

# Requests
middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(connection_string='InstrumentationKey=705f49e9-1faf-4461-9467-b0ed5e0bd64a'),
    sampler=ProbabilitySampler(rate=1.0),
)

# Load configurations from environment or config file
app.config.from_pyfile('config_file.cfg')
#logger.info("read config_file.cfg completed")
if ("VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']):
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

#logger.warning("button1=" + button1)

if ("VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']):
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

#logger.warning("button2=" + button2)

if ("TITLE" in os.environ and os.environ['TITLE']):
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

#logger.warning("title=" + title)

# Redis Connection
r = redis.Redis()

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1): r.set(button1,0)
if not r.get(button2): r.set(button2,0)

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':
        logging.warning("logging processing GET method")
        # Get current values
        vote1 = r.get(button1).decode('utf-8')

        # TODO: use tracer object to trace cat vote
        tracer.span(name="Span Cat Vote")

        vote2 = r.get(button2).decode('utf-8')

        # TODO: use tracer object to trace dog vote
        tracer.span(name="Span Dog Vote")

        # Return index with values
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':
        logging.warning("logging processing POST method")
        if request.form['vote'] == 'reset':
            logging.warning("logging in POSt req form is [reset]")
            # Empty table and return results
            r.set(button1,0)
            r.set(button2,0)
            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}

            # TODO: use logger object to log cat vote
            logger.warning('cat properties=', extra=properties)
            logger.warning('vote is reset - Cats Vote')

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}

            # TODO: use logger object to log dog vote
            logger.warning('dog properties=', extra=properties)
            logger.warning('vote is reset - Dogs Vote')

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:
            logging.warning("logging processing POST")
            # Insert vote result into DB
            vote = request.form['vote']
            r.incr(vote,1)
            logging.warning('logging Voted for ' + vote)
            if vote == 'Dogs':
                logger.warning("Voted for Dogs")
                ##tracer.span(name="Voted for Dogs")
            else:
                logger.warning("Voted for Cats")
                #tracer.span(name="Voted for Cats")

            # Get current values
            vote1 = r.get(button1).decode('utf-8')

            vote2 = r.get(button2).decode('utf-8')

            # Return results
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # comment line below when deploying to VMSS
    #app.run() # local
    # uncomment the line below before deployment to VMSS
    app.run(host='0.0.0.0', threaded=True, debug=True) # remote
