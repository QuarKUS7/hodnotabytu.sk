import os
import uwsgi
import uuid
import pickle
import json
import logging

import xgboost as xgb
import numpy as np
import pandas as pd

from flask import Flask, request, Response
from scraper import init_logger


log = init_logger()

MODEL_PATH = './model/best'


app = Flask(__name__)
model = None


@app.route('/status', methods=['GET'])
def status():
    return json.dumps({'myapp': 'I am OK!'})

@app.route('/predict', methods=['POST'])
def predict():
    features = json.loads(request.data)
    log.info(features)
    pred = make_prediction(features)
    message = {'status': 200, 'prediction': int(pred[0])}
    response = Response(json.dumps(message))
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def load_model(model_path=MODEL_PATH):
    uwsgi.cache_update('busy', 'yes')
    global model
    model = pickle.load(open(model_path, 'rb'))
    model.id = uwsgi.cache_get('model_id').decode()
    log.info('New model {} was loaded'.format(model.id))
    uwsgi.cache_update('busy', 'no')

@app.route('/update-model', methods=['GET'])
def update_model():
    uid = uuid.uuid1()
    uwsgi.cache_update('model_id', str(uid.int))
    return json.dumps({'status': 'update complete!'})

@app.teardown_request
def check_cache(ctx):
    global model
    if uwsgi.cache_get('model_id').decode() != model.id:
        if uwsgi.cache_get('busy').decode() == 'no':
            load_model()

def make_prediction(features):

    features = {k: v for k, v in features.items() if v != ''}
    pred_data = {key:0 for key in model.get_booster().feature_names}

    num_features = ['uzit_plocha', 'rok_vystavby', 'pocet_nadz_podlazi', 'pocet_izieb', 'podlazie', ]
    for nf in num_features:
        num_f = int(features.get(nf, 0))
        if num_f == 0:
            pred_data[nf] = np.NaN
        else:
            pred_data[nf] = num_f

    gps_features = ['latitude', 'longitude']
    for nf in gps_features:
        num_f = float(features.get(nf, 0))
        if num_f == 0:
            pred_data[nf] = np.NaN
        else:
            pred_data[nf] = num_f

    for k,v in features.items():
        if k not in num_features + gps_features:
            feature_name = k +'_' +str(v)
            pred_data[feature_name] = 1

    log.info(pred_data)
    pred_data = pd.DataFrame.from_dict(pred_data, orient='index').transpose()

    return model.predict(pred_data)

# initialize
uid = uuid.uuid1()
uwsgi.cache_update('model_id', str(uid.int))
load_model(MODEL_PATH)

if __name__ == '__main__':
    app.run()
