from flask import Flask,jsonify,request
from flask import render_template
import ast

app = Flask(__name__)

labels = []
values = []


@app.route("/")
def chart():
    global labels,values,labelss,valuess
    labels = []
    values = []
    labelss = []
    valuess = []
    return render_template('chart.html', values=values, labels=labels, valuess=valuess, labelss=labelss)


@app.route('/refreshData')
def refresh_graph_data():
    global labels, values, labelss, valuess
    print("labels now: " + str(labels))
    print("data now: " + str(values))
    print("labelss now: " + str(labelss))
    print("datas now: " + str(valuess))
    return jsonify(sLabel=labels, sData=values, xLabel=labelss, xData=valuess)


@app.route('/updateData', methods=['POST'])
def update_data_post():
    global labels, values
    if not request.form or 'data' not in request.form:
        return "error",400
    labels = ast.literal_eval(request.form['label'])
    values = ast.literal_eval(request.form['data'])
    print("labels received: " + str(labels))
    print("data received: " + str(values))
    return "success",201

@app.route('/updateDataSentiment', methods=['POST'])
def update_data_sentiment_post():
    global labelss, valuess
    if not request.form or 'data' not in request.form:
        return "error",400
    labelss = ast.literal_eval(request.form['label'])
    valuess = ast.literal_eval(request.form['data'])
    print("labels received: " + str(labelss))
    print("data received: " + str(valuess))
    return "success",201


if __name__ == "__main__":
    app.run(host='edge.example.com', port=5001)

