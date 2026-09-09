SCRIPTS=./extract_radiometers.py ./extract_temperatures.py ./extract_tracking.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py
PARAMSFILES=../setup/environment.sh
vpath %.L06 ../../../pickle
vpath %.txt ../extracted_txt

all: SeaSTAR_2025-07-10_09-23-46-temperatures.txt SeaSTAR_2025-07-10_09-23-46-radiometers.txt SeaSTAR_2025-07-10_09-23-46-tracking.txt 
	# I want it to do the temperatures, tracking, radiometers
	# for some reason, this doesn't work

SeaSTAR_2025-07-10_09_23-46-temperatures.txt: SeaSTAR_2025-07-10_09-23-46.L06 $(SCRIPTS) $(MODULES) $(PARAMETERS)
	(source ../setup/environment.sh; ./extract_temperatures.py $< > ../extracted_txt/$@)

SeaSTAR_2025-07-10_09_23-46-radiometers.txt: SeaSTAR_2025-07-10_09-23-46.L06 $(SCRIPTS) $(MODULES) $(PARAMETERS)
	(source ../setup/environment.sh; ./extract_radiometers.py $< > ../extracted_txt/$@)

SeaSTAR_2025-07-10_09_23-46-tracking.txt: SeaSTAR_2025-07-10_09-23-46.L06 $(SCRIPTS) $(MODULES) $(PARAMETERS)
	(source ../setup/environment.sh; ./extract_tracking.py $< > ../extracted_txt/$@)
