#!/usr/bin/bash 

OUTFILE=langley.ps
PDFFILE=`basename $OUTFILE .ps`.pdf
PDFROTATE=`basename $OUTFILE .ps`_.pdf
PROJECTION=X10/10l
. ./colorblindpallet.sh
. ./spectralcolors.sh

gmtset PS_MEDIA=A3 FONT_ANNOT_PRIMARY=12p FONT_LABEL=12p

# 500nm---------------------------------------------------------------------------------------------------------
REGION=0/10/1/3
psbasemap -J$PROJECTION -R$REGION -BWeSn -Bxa1f+l"Airmass_secant" -Byaf1+l"Voltage" -K > $OUTFILE
DATAFILE=./mlo_5starg_20220515_params.txt
# $4 $5 is airmass_secant voltage440
cat $DATAFILE | awk '{print $4, $5}' |
        psxy -J$PROJECTION -R$REGION -W$FOURFOURTY -Sc0.03c -O -K >> $OUTFILE
# $4 $7 is airmass_secant voltage500
cat $DATAFILE | awk '{print $4, $7}' |
        psxy -J$PROJECTION -R$REGION -W$FOURFOURTY -Sc0.03c -O -K >> $OUTFILE

psbasemap -J$PROJECTION -R$REGION -BWeSn -Bxa1f+l"Airmass_young" -Byaf1+l"Voltage" -X11 -O -K >> $OUTFILE
# $3 $5 is airmass voltage440
cat $DATAFILE | awk '{print $3, $5}' |
        psxy -J$PROJECTION -R$REGION -W$FOURFOURTY -Sc0.03c -O -K >> $OUTFILE
# $3 $7 is airmass voltage500
cat $DATAFILE | awk '{print $3, $7}' |
        psxy -J$PROJECTION -R$REGION -W$FOURFOURTY -Sc0.03c -O -K >> $OUTFILE


# closing off the plot
psxy -J$PROJECTION -R$REGION -T -O >> $OUTFILE
psconvert $OUTFILE -A -Tf
#pdftk $PDFFILE rotate 1east output $PDFROTATE
#mv $PDFROTATE $PDFFILE

