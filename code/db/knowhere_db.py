import warnings
import pymongo
import boto3
import ConfigParser
import pickle
import pandas as pd
from numpy import mean
from bson.objectid import ObjectId
from dateutil.parser import parse as parse_date

class Reader:

    def __init__(self, db_name='test'):
        parser = ConfigParser.RawConfigParser()
        parser.read('credentials.cfg')
        self.ip = parser.get('server', 'ip')
        self.user = parser.get('Reader', 'user')
        self.pwd = parser.get('Reader', 'pwd')
        self.db_name = db_name
        self.client = None
        self.db = None
        self.connect()

    def connect(self):
        connect_string = "mongodb://{user}:{pwd}@{ip}/{db_name}".format(user=self.user, pwd=self.pwd,
                                                                        ip=self.ip, db_name=self.db_name)
        self.client = pymongo.MongoClient(connect_string)
        self.db = self.client[self.db_name]   

    def get_user_id(self, username):
        user_id = None
        user_data = self.read('users', filter_args={'username': username}, find_one=True)
        if user_data:
            user_id = user_data.get('_id')
        if user_id is None:
            raise Exception('Could not get user_id for user {}'.format(username))
        return user_id
        
    def build_filter(self, username=None, user_id=None, sensor=None, min_date=None, max_date=None, include_max_date=False): 
        filter_args = {}
        if username:
            user_id = self.get_user_id(username)
        if user_id:
            filter_args['user_id'] = user_id            
        if sensor:
            filter_args['sensor'] = sensor
        if min_date or max_date:
            date_filter = {}
            if min_date:
                date_filter['$gte'] = parse_date(min_date)
            if max_date:
                if include_max_date:
                    date_filter['$lte'] = parse_date(max_date)
                else:
                    date_filter['$lt'] = parse_date(max_date)
            filter_args['timestamp'] = date_filter
        return filter_args

    def get_dataframe(self, collection, filter_args={}):
        data = [entry for entry in self.read(collection, filter_args)]
        return pd.DataFrame(data)
        
    def get_dataframe_unrolled(self, collection, username=None, user_id=None, sensor=None, min_date=None, max_date=None, include_max_date=False):
        def entry_to_rows(entry):
            return map(lambda (data_name, data_raw):
                    {'timestamp': entry['timestamp'], 'user_id': entry['user_id'], 'sensor': entry['sensor'], 
                    'data_name': data_name, 'data_raw': data_raw},
                    entry['data'].iteritems()
                    )
                    
        # build filter_args
        filter_args = self.build_filter(username, user_id, sensor, min_date, max_date, include_max_date)
        entries = self.read(collection, filter_args)
        # turn each entry into a list (called row), so we have a list of list
        rows = map(lambda entry: entry_to_rows(entry), entries)
        # join all the rows into one list
        data = reduce(lambda a,b: a + b, rows, [])
        return pd.DataFrame(data)
        
    def get_dataframe_pivoted(self, collection, username=None, user_id=None, sensor=None, min_date=None, max_date=None, include_max_date=False):
        # build filter_args
        filter_args = self.build_filter()
        if not user_id and not username:
            warnings.warn('Excluding user_id from filter can cause errors during pivot', Warning)
        # get the unrolled version so we can pivot the dataframe
        rdf = self.get_dataframe_unrolled(collection, username, user_id, sensor, min_date, max_date, include_max_date)
        rdf['sensor_name'] = rdf.apply(lambda row: row.sensor + ' (' + row.data_name + ')', axis=1)
        rdf.drop(['sensor', 'data_name'], axis=1, inplace=True)
        rdf_pivoted = rdf.pivot(index='timestamp', columns='sensor_name', values='data_raw')
        return rdf_pivoted

    def read(self, collection, filter_args={}, find_one=False):
        if find_one:
            return self.db[collection].find_one(filter_args)
        return self.db[collection].find(filter_args)
        
    def close(self):
        self.client.close()


class Writer(Reader):

    def __init__(self, db_name='test'):
        parser = ConfigParser.RawConfigParser()
        parser.read('credentials.cfg')
        self.ip = parser.get('server', 'ip')
        self.user = parser.get('Writer', 'user')
        self.pwd = parser.get('Writer', 'pwd')
        self.db_name = db_name
        self.client = None
        self.db = None
        self.connect()

    def write_dataframe_to_collection(self, df, collection):
        data = df.to_dict(orient='records')
        return self.write(collection=collection, data=data, insert_many=True)
        
    def write(self, collection, data, insert_one=False, update_filter={}, upsert=True):
        if insert_one:
            return self.db[collection].insert_one(data)
        return self.db[collection].insert_many(data)
        
    def overwrite(self, collection, data, insert_one=False, update_filter={}, upsert=True):
        if insert_one:
            return self.db[collection].update_one(update_filter, {'$set': data}, upsert)
        return self.db[collection].update_many(update_filter, {'$set': data}, upsert)
        

class S3:

    def __init__(self, db_name='test'):
        self.connection = boto3.client('s3')
        self.writer = Writer(db_name)
        
    def upload_to_s3(self, username, model_type, model, fname, bucket='knowhere-data', collection='models'):
        pickle_object = pickle.dumps(model)
        user_id = self.writer.get_user_id(username)
        key = '{}/{}'.format(collection, fname)
        self.connection.put_object(Bucket=bucket, Key=key, Body=pickle_object)
        s3_response = self.connection.head_object(Bucket=bucket, Key=key)
        filesize = s3_response['ContentLength'] if s3_response else 0
        if filesize == 0:
            raise Exception('Error uploading to S3. File size is 0B')
        entry = {'user_id': user_id, 'model_type': model_type, 'key': key}
        update_filter = {'user_id': user_id, 'model_type': model_type}
        self.writer.overwrite(collection=collection, data=entry, insert_one=True, update_filter=update_filter)
        
    def retrieve_from_s3(self, username, model_type, bucket='knowhere-data', collection='models'):
        user_id = self.writer.get_user_id(username)
        filter_args = {'user_id': user_id}
        response = self.writer.read(collection, filter_args=filter_args, find_one=True)
        key = response['key']
        m_type = response['model_type']
        model = self.connection.get_object(Bucket=bucket, Key=key)
        model = pickle.loads(model['Body'].read())
        return model
    