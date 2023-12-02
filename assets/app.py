from flask import Flask, jsonify, request 
from flask_restful import Resource, Api
from downloader import Downloader
from flask_bcrypt import Bcrypt
import threading, queue
app = Flask(__name__) 
api = Api(app)
bcrypt = Bcrypt(app)
youtube = Downloader(server=True)

download_queue = queue.Queue()

class Download(Resource):

  def get(self, url):
    download_queue.put(url)
    if not threading.active_count() > 4:
      t1 = threading.Thread(target=self.process_download_queue)
      t1.start()

    return {'message': 'Download request received and queued'}
 
 
  def process_download_queue(self):
    while not download_queue.empty():
      url = download_queue.get()
      youtube.download(url)
      print(f'Download completed for {url}')

class DownloadInfo(Resource):
  def get(self):
    
    return {}
      
class ping(Resource):
  def get(self):
    
    return {
      'ping': 'pong',
            }
  

api.add_resource(Download, '/download/<string:url>')
api.add_resource(ping, '/ping')


if __name__ == '__main__':
    app.run(debug = True)