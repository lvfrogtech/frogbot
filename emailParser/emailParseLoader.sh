#!/bin/bash

. ~/.ingressparse
ts=`date +%s`

function portalparse() {

#Split out HTML
sed 's/=$/\n/g' $1 | tr -d '\n' | sed 's/<td>/\n/g' | recode html..ascii > ${dirTemp}/${ts}-${1}.html

for p in `grep -o -P '(?<=3D.Portal - ).*(?=" h)' ${dirTemp}/${ts}-${1}.html |awk -F "\" h" '{print $1}' | recode html..ascii | sed 's/ /^^/g'`; do
  pp=`echo $p | sed 's/\^\^/ /g' `
  ##echo $pp
  pname=`echo $pp | recode html..ascii | sed 's/"//g' | sed "s/'//g"`
  intelurl=`grep "$pp" ${dirTemp}/${ts}-${1}.html | sed 's/3D//g' | grep -o  "https://www.ingress.com/intel?ll.*z=19"`
  latlong=`echo $intelurl | awk -F= '{print $2}' | awk -F\& '{print $1}'`
  lat=`echo $latlong | awk -F, '{print $1}'`
  long=`echo $latlong | awk -F, '{print $2}'`
  #echo "$pp;$intelurl;$latlong;$lat;$long  FILE: $1" ##>> $locationsFile
  json=`printf '{"pname":"%s", "lat":"%s","long":"%s", "status":"T"}' "$pname" "$lat" "$long"`
  #echo $json
  curl -s -H 'Content-Type: application/json' http://localhost:5000/lvfrogtech/portals -X PUT --data "$json" > /dev/null &
done
}


function alparse() {
 #echo "parsing $1"
 ts=`date +%s`
 awk '/^Date:/,/End Transmission/' $1 | sed '/^\s*$/d' > $dirTemp/$1

 #Global email variables
 attacker=`grep "attacked by" $dirTemp/$1 | head -1 | awk '{print $NF}'`
 attacktime=`grep "^Date:" $dirTemp/$1 | tail -1 | awk -F ": " '{print $2}'`
 attackdate=`grep "^Date" $1 | awk -F"Date: " '{print $2}' | head -1`
 attackts=`date --date="$attackdate" +%s`


 mkdir -p ${dirTemp}/${ts}-$1
 #csplit -f ${dirTemp}-${ts}/tmp-${ts} $dirTemp/$1 '/STATUS:/' '{*}'
 csplit -s -f ${dirTemp}/${ts}-$1/tmp-${ts} $dirTemp/$1 '/Health:/+2' '{*}'

 #Parse each segment of email
 for file in `ls -1 ${dirTemp}/${ts}-$1`; do
   #Common Vars
   valid=0
   owner=`grep "^Owner:" ${dirTemp}/${ts}-${1}/${file} | awk '{print $2}'`
   health=`grep "^Health:" ${dirTemp}/${ts}-${1}/${file} | awk '{print $2}'`
   portal=`sed '/^\s*$/d' ${dirTemp}/${ts}-${1}/${file} | grep "^Portal" | head -1 | awk -F " - " '{print $2}' | sed 's/"//g'`
   plevel=`grep "^Level" ${dirTemp}/${ts}-${1}/${file} | awk '{print $2}'`
   
   grep "DAMAGE REPORT" ${dirTemp}/${ts}-${1}/${file} > /dev/null
   if [ $? -eq 0 ]; then
     #do first segment logic
     address=`grep -A 2 "^DAMAGE REPORT" ${dirTemp}/${ts}-${1}/${file} | tail -1`
     valid=1
   else
     grep "^DAMAGE:$" ${dirTemp}/${ts}-${1}/${file} > /dev/null
     if [ $? -eq 0 ]; then
       #do additional segment logic
       address=`head -2 ${dirTemp}/${ts}-${1}/${file} | tail -1`
       valid=1
     fi
   fi

   #Check if links were destroyed
   if [ $parse_links -eq 1 ]; then
      grep "LINK" ${dirTemp}/${ts}-${1}/${file} > /dev/null
      if [ $? -eq 0 ]; then
        for i in `awk '/^LINK/,/DAMAGE/' ${dirTemp}/${ts}-${1}/${file} | grep Portal | awk -F " - " '{print $2}' | sed 's/ /^^/g'`; do
          remote=`echo $i | sed 's/\^\^/ /g'`
          json=`printf '{"id":"%s", "portal":"%s", "remote":"%s", "attacker":"%s"}' "$attackts" "$portal" "$remote" "$attacker"`
          curl -s -H 'Content-Type: application/json' http://localhost:5000/lvfrogtech/links -X PUT --data "$json" > /dev/null &
        done
      fi
   fi

 #Parse out attacks
 if [ $parse_attacks -eq 0 ]; then
    valid=0
 fi
 if [ $valid -eq 1 ]; then
    #echo "$owner;$portal;$plevel;$address;$health;$attacker;$attacktime" >> $attackFile
    #echo a
    #echo "$attackts;$owner;$portal;$plevel;$address;$health;$attacker;$attacktime" | /opt/kafka/current/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic ingressAttacks 
    json=`printf '{"id":"%s", "owner":"%s", "portal":"%s","plevel":"%s", "address":"%s", "health":"%s", "attacker":"%s", "attacktime":"%s"}' "$attackts" "$owner" "$portal" "$plevel" "$address" "$health" "$attacker" "$attacktime"`
    #echo $json
    curl -s -H 'Content-Type: application/json' http://localhost:5000/lvfrogtech/attacks -X PUT --data "$json" > /dev/null &
 fi
 #cleanup
 #rm -rf ${dirTemp}/${ts}-${1}
 done


}

mkdir -p $dirTemp
cd $dirPath

echo "Processing...."
count=0
for f in `ls -1`; do
   ((count++))
   #alparse $f
   if [ $parse_portals -eq 1 ]; then
      portalparse $f
   fi
   ## mv $f $dirProcess
done

echo "Processed $count files"
