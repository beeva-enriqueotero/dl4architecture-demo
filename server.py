#!flask/bin/python
from flask import Flask, jsonify
from flask import request
from flask import session

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


#app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

db = pickledb.load('example.db', False) 


@app.route('/processimages', methods=['GET'])
def process_images():
    result = "Yeah"
    url = "images"
    process_images_graphlab(url)
    return result

@app.route('/findpath', methods=['GET'])
def find_path():
    result = "Yeah"
    result = find_path_graphlab("images", 16, 23)
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
    array = []
    images_resized = gl.load_sframe('tmp5.csv')
    for item in images_resized:
      data = {}
      data['id'] = item['id']
      data['url'] = item['path']
      array.append(data)
#    path2 = translate_path(path, images_resized)
    return json.dumps({"result":array})


###
def search_images_impl(city):
    go(city + ' building', 'images')
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

###
def process_images_graphlab(url):
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
  images_resized.save('tmp5.csv', format='csv')
  end_time = time.time()
  uptime = end_time - start_time
  print "Time: "+str(uptime)

###
def find_path_graphlab(url, id1, id2):
    start_time = time.time()
    images_resized = gl.load_sframe('tmp5.csv')
    incr_status()
    model = gl.nearest_neighbors.create(images_resized, features=['extracted_features'], label = 'id', distance='euclidean')

    incr_status() 
    k=8
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
    print type(path)
    #print path
    array = []
    for item in path:
      print item
      data = {}
      data['id'] = item[0]
      data['url'] = images_resized['path'][item[0]]
      print data
      array.append(data)
#    path2 = translate_path(path, images_resized)
    return json.dumps({"result":array})


def translate_path(my_path, images_resized):
    mylist = []
    for x in my_path:
      print(x)
      x = x[0]
      print(x)
      mylist.append(MyImage(id=str(x), url=images_resized['path'][x]))
    return mylist   

###
if __name__ == '__main__':
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(debug=True, threaded=True, host='0.0.0.0', port=8080)

