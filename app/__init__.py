import threading
from flask import Flask

webapp = Flask(__name__)
webapp.secret_key = '\x81\xa9s*\x12\xc7x\xa9d\x1f(\x03\xbeHJ:\x9f\xf0!\xb1a\xaa\x0f\xee'

from app import ec2_monitor
from app import s3_monitor
from app import main
from app.autoscaling.AutoScaling import start_auto_scalling

start_monitor = threading.Thread(target=start_auto_scalling, args=[])
start_monitor.start()

