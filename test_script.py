import json
import sys

from sammy import *

with open(str(sys.argv[1])) as file:
	js = json.loads(file.read())

print(lambda_handler(js, None))