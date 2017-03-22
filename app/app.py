# Python
from flask import Flask, send_file, request
import json
import pandas as pd
#from datetime import datetime

# User-created
import knowhere_db as kdb
from helpers import *

reader = kdb.Reader(db_name='knowhere')
users = query_db_convert_id(
	reader=reader,
	collection="users",
	id_cols=["_id"],
	sort_col="username",
	method=False,
	_filter={}
)

"""
will get every user's data the when the app is run.
need to make this dynamic so new records are fetched
"""
# data = query_db_convert_id(
# 	reader=reader,
# 	collection="iphone_test",
# 	id_cols=["_id", "user_id"],
# 	sort_col="timestamp",
# 	unrolled=True
# )



app = Flask(__name__)

@app.route("/")
def index():
    return send_file("templates/knowhere.html")

@app.route("/query_users", methods=["GET"])
def get_users():
	return json.dumps(users.to_dict(orient='records'));
	#return json.dumps([{"names":["Andrew", "Bill", "Emil", "Glen"]}])

@app.route("/query_iphone_test_GPS", methods=["GET"])
def get_iphone_test():
	user_name = request.args.get("user_name")
	min_date = request.args.get("min_date")
	max_date = request.args.get("max_date")

	# min_date = datetime.strptime(min_date, '%Y-%m-%dT%H:%M:%S.%fZ')
	# max_date = datetime.strptime(max_date, '%Y-%m-%dT%H:%M:%S.%fZ')
	try:
		temp_data = query_db_convert_id(
			reader=reader,
			collection="iphone_test3",
			method="pivoted",
			username=user_name,
			sensor="GPS",
			min_date=min_date,
			max_date=max_date
			#_filter={"user_id":kdb.ObjectId(user_id)}
		)

		user_data = temp_data.apply(make_lat_long, axis=1)
		user_data = list(user_data[pd.notnull(user_data)])

		get_locs(reader, temp_data, user_name, user_data)
		set_distance_traveled(temp_data, user_data)
	except:
		user_data = []

	return json.dumps(user_data);
	#return json.dumps([{"names":["Andrew", "Bill", "Emil", "Glen"]}])
	
@app.teardown_appcontext
def close_db(error):
	reader.close()


if __name__ == "__main__":
    app.run(host='0.0.0.0')