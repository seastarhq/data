SCRIPTS=./output_langley.py
MODULES=./seastar_analysis_params.py ./seastar_analysis_utils.py ./seastar_cloud_flags.py ./seastar_datautils.py ./seastar_error_flags.py ./seastar_filepaths.py 
PARAMSFILES=../setup/local.sh ../setup/environment.sh ../setup/parameters.sh ../setup/channel_wavelengths.sh
vpath %.L06 ../../pickle

langley_2026-05-17_14-06-16.csv: SeaSTAR_2026-05-17_14-06-16.L06 $(SCRIPTS) $(MODULES) $(PARAMSFILES) 
	echo plotting langley from  $@
	. ../setup/local.sh; . ../setup/environment.sh; . ../setup/parameters.sh; . ../setup/channel_wavelengths.sh; ./output_langley.py $< --outputfile $@

SeaSTAR_2026-05-17_14-06-16.L06:
	# somehow this does not work:
	echo making symlink
	. ../setup/local.sh; . ../setup/environment.sh; ln -s $(PICKLE_DIR)/$@
