#!flask/bin/python
from flask import Flask, jsonify
from flask import request
from flask import session
from flask import render_template

import json
import time

import json
import os
import time
import requests
from PIL import Image
from StringIO import StringIO
from requests.exceptions import ConnectionError
from scipy.misc import imread
import sys
sys.path.append("/usr/local/lib/python2.7/dist-packages/")
import graphlab as gl
import pickle
import pickledb 



import os

myport = 8080

app = Flask(__name__, static_folder='images', static_url_path="/")

db = pickledb.load('example.db', False) 

@app.route('/')
def home():
  return render_template('index.html')

@app.route('/images/<path:path>')
def static_proxy(path):
  return app.send_static_file(path)

@app.route('/js/<path:path>')
def static_js(path):
  return app.send_static_file(os.path.join('js', path))

@app.route('/css/<path:path>')
def static_css(path):
  return app.send_static_file(os.path.join('css', path))

@app.route('/fonts/<path:path>')
def static_fonts(path):
  return app.send_static_file(os.path.join('fonts', path))

@app.route('/img/<path:path>')
def static_img(path):
  return app.send_static_file(os.path.join('img', path))

@app.route('/ajax/<path:path>')
def static_ajax(path):
  return app.send_static_file(os.path.join('ajax', path))


@app.route('/processimages', methods=['GET'])
def process_images():
    mycity = request.args.get('city', False, type=str)
    global myport
    process_images_graphlab("images/"+mycity, mycity)
    result = get_all_images_from(mycity)
    return result

@app.route('/findpath', methods=['GET'])
def find_path():
    myfrom = request.args.get('from', False, type=int)
    myto = request.args.get('to', False, type=int)
    mycity = request.args.get('city', False, type=str)
    result = find_path_graphlab("images/"+mycity, myfrom, myto, mycity)
    return result

@app.route('/getprogress', methods=['GET'])
def get_status():
    status = db.get('status')
    if not status:
      status = 0
    return str(status)

@app.route('/searchimages', methods=['GET'])
def search_images():
    result = "Yeah"
    try:
        city = request.args.get('city', False, type=str)
        result = city
        search_images_impl(city)
    except:
        result = "Fail"
    return result

@app.route('/getallimages', methods=['GET'])
def get_all_images():
    mycity = request.args.get('city', False, type=str)
    return get_all_images_from(mycity)

def get_all_images_from(city):
    array = []
    images_resized = gl.load_sframe('model/'+city+'.csv')
    for item in images_resized:
      data = {}
      data['id'] = item['id']
      data['url'] = replace_path(item['path'])
      array.append(data)
    return json.dumps({"result":array})

###
def search_images_impl(city):
    go(city + ' building', 'images/'+city)
    clean('images')

###
def go(query, path):
  size = 256,256
  BASE_URL = 'https://ajax.googleapis.com/ajax/services/search/images?'\
             'v=1.0&q=' + query + '&start=%d'

  print path
  if not os.path.exists(path):
    os.makedirs(path)
 
  start = 0
  while start < 60:
      print start
      r = requests.get(BASE_URL % start)
      if json.loads(r.text)['responseData']['results'] is not None:
          for image_info in json.loads(r.text)['responseData']['results']:
              url = image_info['unescapedUrl']
              print url
              try:
                  image_r = requests.get(url)
              except ConnectionError, e:
                  print 'could not download %s' % url
                  continue
              title = image_info['titleNoFormatting'].replace('/', '').replace('\\', '')
              file = open(os.path.join(path, '%s.jpg') % title, 'w')
              try:
                  img = Image.open(StringIO(image_r.content))
                  img.thumbnail(size, Image.ANTIALIAS)
                  Image.open(StringIO(image_r.content)).save(file, 'JPEG')
                  imread(file.name)
              except IOError, e:
                  os.remove(file.name)
                  continue
              finally:
                  file.close()
          start = start+4

###                  
def clean(path):
    i = 0
    for f in os.listdir(path):
        os.rename(path + '/' + f, path + '/' + str(i) + '.jpg')
        i += 1

###        
def incr_status():
  status = db.get('status')
  if not (status):
    status = 1
  else:
    status = status + 1
  db.set('status', status)
  print("Step "+str(status))

def replace_path(url):
  filepath = "/home/enrique/github/dl4architecture-demo/"
  #filepath = os.getcwd()
  return url.replace(filepath, '')

###
def process_images_graphlab(url, city):
  start_time = time.time()
  incr_status()  
  images = gl.image_analysis.load_images(url, random_order=False, with_path=True)
  incr_status()
   
  images_resized = gl.SFrame()
  images_resized['image'] = gl.image_analysis.resize(images['image'], 256, 256, 3)
  images_resized = images_resized.add_row_number()
  images_resized['path'] = images['path']
  
  incr_status()
 
  pretrained_model = gl.load_model('http://s3.amazonaws.com/GraphLab-Datasets/deeplearning/imagenet_model_iter45')
  incr_status() 
  images_resized['extracted_features'] = pretrained_model.extract_features(images_resized)
  images_resized.save('model/'+city+'.csv', format='csv')
  end_time = time.time()
  uptime = end_time - start_time
  print "Time: "+str(uptime)

###
def find_path_graphlab(url, id1, id2, city):
    start_time = time.time()
    images_resized = gl.load_sframe('model/'+city+'.csv')
    #images_resized.show()
    incr_status()
    model = gl.nearest_neighbors.create(images_resized, features=['extracted_features'], label = 'id', distance='euclidean')

    incr_status() 
    k=6
    path = None
    while not path:
      print "try " + str(k)
      try:
        sf_nn = model.query(images_resized, label = 'id', k = k)
        sf_nn = sf_nn[sf_nn['distance'] > 0]
        sg_similarities = gl.SGraph().add_edges(sf_nn, src_field='query_label', dst_field='reference_label')
        sp = gl.shortest_path.create(sg_similarities, source_vid=id1)
        path = sp.get_path(id2)
      except Exception, e:
        print e
      finally:
        k+=1
    incr_status()
    end_time = time.time()
    uptime = end_time - start_time
    print "Time: "+str(uptime)
   
    array = []
    for item in path:
      print item
      data = {}
      data['id'] = item[0]
      data['url'] = replace_path(images_resized['path'][item[0]])
      print data
      array.append(data)

    return json.dumps({"result":array})



###
if __name__ == '__main__':
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, threaded=True, host='0.0.0.0', port=myport)

