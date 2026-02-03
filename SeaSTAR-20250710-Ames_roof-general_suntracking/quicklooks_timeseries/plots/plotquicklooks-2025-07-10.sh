#!/usr/bin/bash

gmtset PS_MEDIA=A2 FONT_ANNOT_PRIMARY=12p FONT_LABEL=12p


. ./colorblindpallet.sh
. ../setup/environment.sh

cp gmt.conf gmt.conf.old
gmtset FONT_ANNOT_PRIMARY 12p,Helvetica \
	FONT_ANNOT_SECONDARY 12p,Helvetica \
	FONT_LABEL 12p,Helvetica \
	FONT_TITLE 12p,Helvetica

OUTFILEARRAY=()

for NUMBER in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
do

DATAFILE=$EXTRACTED_DATA_DIR/alldata_$NUMBER-2025-07-10_09-23-46.txt #$NUMBER_$DATE.txt
echo $NUMBER
echo $DATAFILE
DATE=`$SCRIPTS_DIR/get_plot_name.py $DATAFILE`
PROJECTION=X30/3
OUTFILE=quicklooks_$NUMBER_$DATE.ps

# Plot the radiometer data - range is 0-2 V 
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/0/2
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.5 -By+l"Radiometer / V" -BWesN -K -Y38.0c > $OUTFILE
cat $DATAFILE | awk '{print $1, $12*-1.0}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$CYAN -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $13*-1.0}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$ORANGE  -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $14*-1.0}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$REDPURPLE -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $15*-1.0}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $16*-1.0}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$GREY -O -K >> $OUTFILE

# Plot the tracking data - range is 0.4-0.6
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/0.4/0.6
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.25 -By+l"Tracking / FFOV" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $26}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$REDPURPLE -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $27}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE
# plot the camera brightness - range is 0-255, on the same plot as above
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/0/255
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy255 -By+l"Cam Bright" -BwEsn -K -O >> $OUTFILE
cat $DATAFILE | awk '{print $1, $28}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$GREY -O -K >> $OUTFILE

# Plot the target data - range is 0.4-0.6
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/0.4/0.6
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.25 -By+l"Target / FFOV" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $29}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$REDPURPLE -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $30}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE

# Plot the ephem data - range is 60-130 degrees  
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/0/360
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy60 -By+l"Solar Ephem / deg" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $24}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$CYAN -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $25}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$ORANGE  -O -K >> $OUTFILE

# Plot the imu data - range is 0-255 
# first latitude, then longitude
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/37.4/37.5
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.1 -By+l"Latitude" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $10}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$CYAN -O -K >> $OUTFILE
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/-122.5/-121.5
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.5 -By+l"Longitude" -BwEsn -K -O >> $OUTFILE
cat $DATAFILE | awk '{print $1, $11}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$ORANGE  -O -K >> $OUTFILE

# plot imu temp & pressure, hot_block1_temp
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/35/60
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy10 -By+l"IMU/B1 Temp" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $8}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$CYAN -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $31}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/1000/1100
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy50 -By+l"IMU Press" -BwEsn -K -O >> $OUTFILE
cat $DATAFILE | awk '{print $1, $9/100}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$VERMILLION -O -K >> $OUTFILE

# plot imu accell & velocities
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/-0.5/0.5
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.5 -By+l"Lin accel" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $5}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $6}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$REDPURPLE -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $7}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$CYAN -O -K >> $OUTFILE
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/-0.5/0.5
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy0.5 -By+l"Ang vel" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $2}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLACK -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $3}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$VERMILLION -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $4}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$GREY -O -K >> $OUTFILE

# plot imu encoders & quaternion
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/-180/180
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy120 -By+l"Encoders" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $17}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $18}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$REDPURPLE -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $19}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$CYAN -O -K >> $OUTFILE
REGION=`$SCRIPTS_DIR/get_timeseries_region.py $DATAFILE`/-1/1
psbasemap -J$PROJECTION -R$REGION -Bpx2m -Bpy1 -By+l"Quaternion" -BWesn -K -O -Y-3.5c >> $OUTFILE
cat $DATAFILE | awk '{print $1, $20}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLACK -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $21}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$VERMILLION -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $22}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$GREY -O -K >> $OUTFILE
cat $DATAFILE | awk '{print $1, $23}' | psxy -J$PROJECTION -R$REGION -Sc0.05c -G$BLUEGREEN -O -K >> $OUTFILE

echo 2025-07-08T11:48:10 -1.6 2025-07-08T11:57:42 | pstext -J$PROJECTION -R$REGION -F+jBL -O -K -N >> $OUTFILE
echo 2025-07-08T11:48:10 -1.9 Description goes here | pstext -J$PROJECTION -R$REGION -F+jBL -O -K -N >> $OUTFILE

# close the plot
# and convert formats
psxy -J$PROJECTION -R$REGION -T -O >> $OUTFILE
psconvert $OUTFILE -A -Tf
psconvert $OUTFILE -A -Tg

OUTFILEARRAY+=($OUTFILE)

done

# make it all into one big pdf
# this doesn't seem to work:
#(cd $PLOTS_DIR; 
#pdftk `for file in ${OUTFILEARRAY[@]}
#do 
#    echo `basename $FILE .ps`.pdf
#done | xargs` cat output allpages.pdf)
#export $OUTFILEARRAY


cp gmt.conf.old gmt.conf
