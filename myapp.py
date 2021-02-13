import os
import uwsgi
import uuid
import pickle
import json
import logging

import xgboost as xgb
import numpy as np
import pandas as pd

from flask import Flask, request
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
    features = request.get_json()
    pred = make_prediction(features)
    message = {'status': 200, 'prediciton': int(pred[0])}
    return json.dumps(message)

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
    pred_data = {key:0 for key in model.feature_names}

    num_features = ['uzit_plocha', 'rok_vystavby', 'pocet_nadz_podlazi', 'pocet_izieb', 'podlazie', 'latitude', 'longitude']
    for nf in num_features:
        pred_data[nf] = features.get(nf,np.NaN)

    for k,v in features.items():
        if k not in num_features:
            feature_name = k +'_' +str(v)
            pred_data[feature_name] = 1

    pred_data = pd.DataFrame.from_dict(pred_data, orient='index').transpose()

    pred_dmatrix = xgb.DMatrix(data=pred_data)
    return model.predict(pred_dmatrix)

# initialize
uid = uuid.uuid1()
uwsgi.cache_update('model_id', str(uid.int))
load_model(MODEL_PATH)

if __name__ == '__main__':
    app.run()
