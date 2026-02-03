#!/usr/bin/env python3

from datetime import datetime,timedelta
import sys,os
import pandas as pd
import pytz
import datautils

seastar_timezone = pytz.timezone("US/Pacific")

ROOT_DIR = os.environ['ROOT_DIR']
SCRIPTS_DIR = os.environ['SCRIPTS_DIR']
RAW_DATA_DIR = os.environ['RAW_DATA_DIR']
EXTRACTED_DATA_DIR = os.environ['EXTRACTED_DATA_DIR']
raw_data_dirs = [RAW_DATA_DIR,]

seastar_logfile = datautils.findFile(sys.argv[1],raw_data_dirs)

file_split_interval = int(sys.argv[2])

logfile_date = os.path.basename(seastar_logfile).split("_")

sys.stderr.write(f"seastar logfile date: {logfile_date[0]}\n")
sys.stderr.write(f"requested file split interval (minutes): {file_split_interval}\n")


# this is old code, for using numpy to read the old file format:
#skiprows = sys.argv[2]
#log_time_raw, m0_encoder, m1_encoder, m2_encoder, sun_ephemAz, sun_ephemAlt, quaternion_w, quaternion_x, quaternion_y, quaternion_z, camera_sun_x, camera_sun_y, camera_sun_brighness, azOff, altOff, imu_ang_vel_x, imu_ang_vel_y, imu_ang_vel_z, m0_commanded_vel, m1_commanded_vel, sun_target_x, sun_target_y, imuT, imuP = np.loadtxt(seastarlog, unpack=True, delimiter=',', skiprows=skiprows, dtype=str)

# this file's column descriptions:
#0 time    time           
#1 q1     motor0 angle
#2 q2     motor1 angle
#3 q3     motor2 angle
#4 sunAz  sun ephem azimuth
#5 sunAlt sun ephem altitude
#6 qw     IMU quaternion w
#7 qx     IMU quaternion x
#8 qy     IMU quaterion y
#9 qz     IMU quaternion z
#10 sx      camera sun x
#11 sy      camera sun y
#12 sb      camera sun brightness
#13 tx      camera target x
#14 ty      camera target y
#15 rx      IMU angular velocity x
#16 ry      IMU angular velocity y
#17 rz      IMU angular velocity z
#18 ax      free accelleration on x axis
#19 ay      free accekkeratuib on y axis
#20 az      free accelleration on z axis
#21 cqw     correction quaternion w
#22 cqx     corrction x
#23 cqy     correction y
#24 cqz     correction z
#25 imuT    IMU temperature
#26 imuP    IMU pressure (i.e. atmospheric pressure measured by hardware on the IMU board)
#27 imuLat  IMU (gps) latitude
#28 imuLon  IMU (gpt) longitude
#29 hMin    hyperbolic function tuning parameter - min
#30 hMax    h           f       t       p       - max
#31 hScale  h           f        t       p          - scaling parameter
#32 j3 ch1  channel 1
#33         channel 2
#34         channel 3
#35         channel 4
#36         channel 5

# we use pandas: # the things we are interested in are # columns: 
# 0=timestamp, 
# 1=m0_encoder 2=m1_encoder 3=m2_encoder 
# 4=sun_ephem_az 5=sun_ephem_elev
# 6=quaternion_w 7=quaternion_x 8=quaternion_y 9=quaterion_z
# 10=camera_sun_x 11=camera_sun_y 12=camera_brightness 13=camera_target_x 14=camera_target_y
# 15=angular_vx, 16=angular_vy, 17=angular_vz, 18=linear_ax, 19=linear_ay, 20=linear_az, 25=imu_temp, 26=imu_press, 27=imu_lat, 28=imu_lon 
# we omit for now: 29=hyperbolic_min 30=hyper_max 31=hyper_scale
# 32=ch1, 33=ch2, 34=ch3, 35=ch4, 36=ch5
# 37=t3
dataframe = pd.read_csv(seastar_logfile,skiprows=0,usecols=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,25,26,27,28,32,33,34,35,36,37])
dataframe['datetime'] = pd.to_datetime(dataframe['time'], format='%Y-%m-%d %H:%M:%S.%f') 
dataframe['datetime'] = dataframe['datetime'].dt.tz_localize(seastar_timezone)
dataframe.drop('time',axis=1,inplace=True)
# rename the motor & quaternion
dataframe.rename(columns={" q1": "motor_0_enc", " q2": "motor_1_enc", " q3": "motor_2_enc", " qw": "quaternion_w", " qx": "quaternion_x", " qy": "quaternion_y", " qz": "quaternion_z"},inplace=True)
# rename the suntracking 
dataframe.rename(columns={" sunAz": "sun_ephem_az", " sunAlt": "sun_ephem_elev", " sx": "camera_sun_x", " sy": "camera_sun_y", " sb": "camera_sun_brightness", " tx": "camera_target_x", " ty": "camera_target_y"},inplace=True)
# rename the imu variables
dataframe.rename(columns={" rx": "angular_vx", " ry": "angular_vy", " rz": "angular_vz", " ax": "linear_ax", " ay": "linear_ay", " az": "linear_az", " imuT": "imu_temp", " imuP": "imu_press", " imuLat": "imu_lat", " imuLon": "imu_lon"},inplace=True)
# rename the radiometer variables
dataframe.rename(columns={" j3_ch1_1x": "ch1_1x", " j3_ch2_1x": "ch2_1x", " j3_ch3_1x": "ch3_1x", " j3_ch4_1x": "ch4_1x", " j3_ch5_1x": "ch5_1x"},inplace=True)
dataframe.rename(columns={" t3": "hot_block1_temp"},inplace=True)
print(dataframe.columns)

time = dataframe['datetime'][0]
sys.stderr.write(f"seastar logfile start time: {time}\n")
time_final = dataframe['datetime'][len(dataframe)-1].round('s')
sys.stderr.write(f"seastar logfile end time: {time_final}\n")

begin_of_outfile = time
#begin_of_outfile = time.floor(f"{file_split_interval}min")
outfile_count = 0
index = 0

while (time <= time_final):

    sys.stderr.write(f"beginning of outfile: {begin_of_outfile}\n")
    end_of_outfile = begin_of_outfile + timedelta(minutes=file_split_interval) 
    sys.stderr.write(f"outfile end time: {end_of_outfile}\n")
    outfilename = EXTRACTED_DATA_DIR + "/" + "alldata_" + str(outfile_count) + "-" + logfile_date[0] + "_" + logfile_date[1] + ".txt"
    #outfilename = EXTRACTED_DATA_DIR + "/" + "allvars_" + str(outfile_count) + "_" + logfile_date[0] + "_" + begin_of_outfile.strftime("%H-%M-%S") + ".txt"
    sys.stderr.write(f"output file: {outfilename}\n")
    sys.stderr.write(f"loop 1, index {index}\n\n")

    if index > len(dataframe)-1:
        break


    row = dataframe.iloc[index]
    time = row['datetime']
    
    outfile = open(outfilename, 'w')

    outfile.write("#1    \
2          3          4          5         6         7         8        9         10      11      \
12     13     14     15     16     \
17          18          19          20           21           22           23           \
24           25             26           27           28                    29              30\n")   # 1-based column numbers for awk 
    outfile.write("#time \
angular_vx angular_vy angular_vz linear_ax linear_ay linear_az imu_temp imu_press imu_lat imu_lon \
ch1_1x ch2_1x ch3_1x ch4_1x ch5_1x \
motor_0_enc motor_1_enc motor_2_enc quaternion_w quaternion_x quaternion_y quaternion_z \
sun_ephem_az sun_ephem_elev camera_sun_x camera_sun_y camera_sun_brightness camera_target_x camera_target_y \
hot_block1_temp\n") # the header
    
    while index < len(dataframe)-1:


        if row['datetime'] < end_of_outfile:
            sys.stderr.write(f"loop 2 option 1 {index}\n\n")
            rowstring = f"{row['datetime'].isoformat()} \
{row['angular_vx']} {row['angular_vy']} {row['angular_vz']} {row['linear_ax']} {row['linear_ay']} {row['linear_az']} {row['imu_temp']} {row['imu_press']} {row['imu_lat']} {row['imu_lon']} \
{row['ch1_1x']} {row['ch2_1x']} {row['ch3_1x']} {row['ch4_1x']} {row['ch5_1x']} \
{row['motor_0_enc']} {row['motor_1_enc']} {row['motor_2_enc']} {row['quaternion_w']} {row['quaternion_x']} {row['quaternion_y']} {row['quaternion_z']} \
{row['sun_ephem_az']} {row['sun_ephem_elev']} {row['camera_sun_x']} {row['camera_sun_y']} {row['camera_sun_brightness']} {row['camera_target_x']} {row['camera_target_y']} {row['hot_block1_temp']}\n" 


            sys.stderr.write(rowstring)
            outfile.write(rowstring)
            index += 1
            row = dataframe.iloc[index]
            sys.stderr.write(str(row['datetime']) + '\n')  # for example
            time = row['datetime']

        else:
            sys.stderr.write(f"loop 2 option 2 {index}\n\n")
            outfile.close()
            begin_of_outfile = end_of_outfile
            outfile_count += 1
            index += 1

            break

    index += 1
















