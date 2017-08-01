#!/usr/bin/python
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask_cors import CORS, cross_origin
import json
import uuid
import dse
import requests
from dse.cluster import Cluster
from dse.auth import DSEPlainTextAuthProvider
from confluent_kafka import Producer

savelog = "/home/frogbot/api.log"
botqueue = "/home/frogbot/frogbot/incoming/"

app = Flask(__name__)
CORS(app)

#Configuration
contactpoints = ['66.70.191.99']
auth_provider = DSEPlainTextAuthProvider (username='cassandra', password='fr0gp0w3r')
keyspace = "ingress"

print "Connecting to cluster"

cluster = Cluster( contact_points=contactpoints,
                   auth_provider=auth_provider )

session = cluster.connect(keyspace)
print "Setting up kafka producer"
kafka = Producer({'bootstrap.servers': 'localhost'})

def writelog(d, filename):
   target = open(filename, 'a')
   target.write(d)
   target.write("\n")
   target.close()

def fileDrop(d, filename):
   target = open(filename, 'w')
   target.write(request.json['id'])
   target.close()

@app.route('/')
def index():
    return "mmm smurf tears"


@app.route('/lvfrogtech')
def lvfrogtech():
    return "Hello, Frog!"

@app.route('/lvfrogtech/api/incoming', methods=['POST'])
def incoming():
   if not request.json or not 'id' in request.json:
      abort(400)

   print json.dumps(request.json)
   fileDrop(request.json['id'], botqueue + str(uuid.uuid4()))
   writelog(json.dumps(request.json), savelog)
   return "201"

@app.route("/lvfrogtech/portal/<string:key>/", methods=['GET'])
def portal(key):
   query = """ select * from ingress.portals where solr_query = '{"q":"portal:*%s*"}' limit 5 """ % (key)
   final = ""
   rows = session.execute(query)
   if not rows:
       return "No portals found"
   else:
      for row in rows:
         result = str(row.pname) + ": " + str(row.intelurl)
         final = final + "\n" + result
   return final


## {
##    "pname": "<portal name>",
##    "lat": "<latitude",
##    "long": "<longitude>"
## }
@app.route("/lvfrogtech/portals", methods=['POST', 'PUT'])
def portals():
   if request.method == 'POST':
      search = request.json['p'].split()
      query = """ select * from ingress.portals where solr_query = '{"q":"portal:*%s*" """ % (search[0])
      cquery = """ select count(*) from ingress.portals where solr_query = '{"q":"portal:*%s*" """ % (search[0])
      for s in search:
         query = query + """ , "fq":"portal:*%s*" """ % (s)
         cquery = cquery + """ , "fq":"portal:*%s*" """ % (s)
      query = query + """ }' limit 5 """
      cquery = cquery + """ }' """
      
      print(query)
      print(cquery)
      final = ""
      rows = session.execute(query)
      if not rows:
          return '{"count": [{"total": [0]}]}'
      else:
         myjson = {'portals':[], 'count':[]}
         for row in rows:
            d = {}
            d['name'] = str(row.pname)
            d['intelurl'] = str(row.intelurl)
            myjson.get('portals').append(d)
            
            result = str(row.pname) + ": " + str(row.intelurl)
            final = final + "\n" + result
         d = {}
         d['total'] = session.execute(cquery)[0]
         myjson.get('count').append(d)
         output = json.dumps(myjson)
         print(output)
      return output
   if request.method == 'PUT':
      try:
         pname = request.json['pname'] #.replace('\'','')
         lat = request.json['lat']
         long = request.json['long']
         #lat = float(request.json['lat'])
         #long = float(request.json['long'])
         latlong = lat + "," + long
         intelurl = """ https://www.ingress.com/intel?ll=%s,%s&pll=%s,%s&z=19 """ %(lat, long, lat, long)
         #query = """ UPDATE ingress.portals SET status = 'S' WHERE pname = '%s' AND latlong = '%s'  """ % (pname, latlong)
         tokafka = pname + ";" + intelurl + ";" + latlong + ";" + lat + ";" + long
      except:
         print("ERROR: INPUT")
         abort(400)
      try:
         if request.json['status']:
            tokafka = tokafka + ";" + request.json['status']
      except:
         print("DEBUG: NO STATUS")

      print(tokafka)
      try:
         kafka.produce('ingressPortals', tokafka.encode('utf-8'))
      except:
         print("ERROR: KAFKA")
         abort(400)

      #print(query)
      #try:
      #   session.execute(query)
      #except:
      #   print("DEBUG: DSE ERROR")
      #   abort(400)
      return "success!"

#{"id":"<attackts>", "owner":"<owner>", "portal":"<portal>","plevel":"<plevel>", "address":"<address>", "health":"<health>", "attacker":"<attacker>", "attacktime":"<attacktime>"}
#{
#	"id": "<attackts>",
#	"owner": "<owner>",
#	"portal": "<portal>",
#	"plevel": "<plevel>",
#	"address": "<address>",
#	"health": "<health>",
#	"attacker": "<attacker>",
#	"attacktime": "<attacktime>"
#}
@app.route("/lvfrogtech/attacks", methods=['POST', 'PUT'])
def attacks():
   if request.method == 'PUT':
      try:
         id = request.json['id']
         owner = request.json['owner']
         portal = request.json['portal'].replace('\'','')
         plevel = request.json['plevel']
         address = request.json['address']
         health = request.json['health']
         attacker = request.json['attacker']
         attacktime = request.json['attacktime']
         tokafka =  id + ";" + owner + ";" +  portal + ";" +  plevel + ";" +  address+ ";" +  health + ";" + attacker + ";" + attacktime
      except:
         print("ERROR: INPUT")
         abort(400)

      print(tokafka)
      try:
         kafka.produce('ingressAttacks', tokafka.encode('utf-8'))
      except:
         print("ERROR: KAFKA")
         abort(400)
      return "success!"

#{"id":"<attackts>", "portal":"<portal", "remote":"<remote portal>", "attacker":"<attacker>"}'
#"$attacktime" "$portal" "$remote" "$attacker"
#{
#	"id": "<attackts>",
#	"portal": "<portal",
#	"remote": "<remote portal>",
#	"attacker": "<attacker>"
#}

@app.route("/lvfrogtech/links", methods=['POST', 'PUT'])
def links():
   if request.method == 'PUT':
      try:
         id = request.json['id']
         portal = request.json['portal'].replace('\'','')
         remote = request.json['remote']
         attacker = request.json['attacker']
         tokafka =  id + ";" +  portal + ";" +  remote + ";" +  attacker
      except:
         print("ERROR: INPUT")
         abort(400)

      print(tokafka)
      try:
         kafka.produce('ingressLinks', tokafka.encode('utf-8'))
      except:
         print("ERROR: KAFKA (ingressLinks)")
         abort(400)
      return "success!"


if __name__ == '__main__':
    app.run(debug=True)

