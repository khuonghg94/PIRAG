import logging
import os
import re

from flask import Flask, redirect, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from ExtractInfoFromPDF import ProcessPDF
from DrawGraph import DrawGraph, DrawMultiGraph

app = Flask(__name__)
UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/uploads/'
PROCESS_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/process/'
UPLOAD_MULTI_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/multiuploads/'
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = PROCESS_FOLDER
app.config['UPLOAD_MULTI_FOLDER'] = UPLOAD_MULTI_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower()


@app.route('/', methods=['GET', 'POST'])
def index():
   result = ""
   if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
   if not os.path.exists(PROCESS_FOLDER):
       os.makedirs(PROCESS_FOLDER)
   if not os.path.exists(UPLOAD_MULTI_FOLDER):
        os.makedirs(UPLOAD_MULTI_FOLDER)
   if request.method == 'POST':
       if 'file' not in request.files:
           print('No file attached in request')
           return redirect(request.url)
       file = request.files['file']
       if file.filename == '':
           print('No file selected')
           return redirect(request.url)
       if file and allowed_file(file.filename):
           list_filters = []
           list_keywords = []
           language = request.form['language']
           filters = request.form['Fixed-Filter-Keywords']
           filters_more = request.form['Filter-Keywords']
           extracts = request.form['Fixed-Extracted-Keywords']
           extracts_more = request.form['Extracted-Keywords']
           list_filters = re.findall(r"'(.*?)'", str(filters + filters_more))
           list_keywords = re.findall(r"'(.*?)'", str(extracts + extracts_more))
           filename = secure_filename(file.filename)
           file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
           folder_process = filename.split('.')[0]
           zone_folder = os.path.dirname(os.path.abspath(__file__)) + '/process/' + folder_process
           if not os.path.exists(zone_folder):
               os.makedirs(zone_folder)
           jsonFile, list_keys_trans = ProcessPDF(folder_process, UPLOAD_FOLDER, filename, list_filters, language, list_keywords)
           result = "Upload and Process Successfully"
           fileJsonPath = UPLOAD_FOLDER + jsonFile
           plotFile = DrawGraph(folder_process, UPLOAD_FOLDER, fileJsonPath, list_keys_trans, True)
           plotFileSimple = DrawGraph(folder_process, UPLOAD_FOLDER, fileJsonPath, list_keys_trans, False)
           return render_template('index.html', NOTIFY=result, filename=filename, jsonFile=jsonFile, plotPath=plotFile, plotPathSimple=plotFileSimple)
   return render_template('index.html', NOTIFY=result)


@app.route('/uploads/<path:filename>', methods=['GET'])
def download(filename):
    logging.info('Downloading file= [%s]', filename)
    logging.info(app.root_path)
    full_path = os.path.join(app.root_path, UPLOAD_FOLDER)
    logging.info(full_path)
    return send_from_directory(full_path, filename, as_attachment=True)

@app.route('/multizone', methods=['GET', 'POST'])
def multizone():
    result = ""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(PROCESS_FOLDER):
        os.makedirs(PROCESS_FOLDER)
    if not os.path.exists(UPLOAD_MULTI_FOLDER):
        os.makedirs(UPLOAD_MULTI_FOLDER)
    if request.method == 'POST':
        if 'file' not in request.files:
            print('No file attached in request')
            return redirect(request.url)
        listFiles = []
        for file in request.files.getlist('file'):
            if file.filename == '':
                print('No file selected')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_MULTI_FOLDER'], filename))
                fileJsonPath = UPLOAD_MULTI_FOLDER + filename
                listFiles.append(fileJsonPath)
        plotFile = DrawMultiGraph(UPLOAD_FOLDER, listFiles, True)
        plotFileSimple = DrawMultiGraph(UPLOAD_FOLDER, listFiles, False)
        result = "Upload Files Successfully"
        return render_template('multizone.html', NOTIFYM=result, plotMPath=plotFile, plotMPathS=plotFileSimple)
    return render_template('multizone.html', NOTIFY=result)

if __name__=='__main__':
    app.run(debug=True)