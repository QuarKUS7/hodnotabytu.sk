import json
import pickle
import logging

import numpy as np
import pandas as pd

from flask import Flask, request, Response

MODEL_PATH = './model/best'
model = None
LOGFILE = '/var/log/app.log'
FORMATTER = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

file_handler = logging.FileHandler(LOGFILE)
file_handler.setFormatter(FORMATTER)
file_handler.setLevel(10)

app = Flask(__name__)
app.logger.addHandler(file_handler)


@app.route('/status', methods=['GET'])
def status():
    app.logger.info("I am OK!")
    return json.dumps({'myapp': 'I am OK!'})

@app.route('/predict', methods=['POST'])
def predict():
    features = json.loads(request.data)
    app.logger.info(features)
    pred = make_prediction(features)
    message = {'prediction': int(pred[0])}
    response = Response(json.dumps(message))
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/update-model', methods=['GET'])
def update_model():
    load_model()
    return json.dumps({'status': 'update complete!'})

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

    app.logger.info(pred_data)
    pred_data = pd.DataFrame.from_dict(pred_data, orient='index').transpose()

    return model.predict(pred_data)

@app.before_first_request
def load_model():
    global model
    model = pickle.load(open(MODEL_PATH, 'rb'))


if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=5000)
