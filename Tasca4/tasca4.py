print("hello world")

!pip -q install https://storage.googleapis.com/0x7ff601307fa5/s2dr4-20260905.1-cp313-cp313-linux_x86_64.whl

import s2dr4.inferutils

# Specify the target location in the Lon,Lat (X,Y) format.
# The model will process a 4x4 km bounding box around the target location
lonlat = (1.94,41.26) # NOTE THE X,Y FORMAT!

# Specify the target date. Please note, S2DR3 model will process the date
# from the Sentinel-2 catalogue that is closest to the specified date.
# Selected date may be ocluded by clouds. Please consult the Copernucus
# Dataspace for data availability https://browser.dataspace.copernicus.eu
# Archive images are available from 2018-01-01.
date = '2026-08-20'

# Due to high demand, the preview link may take some time to load.
# !!!Please note: the image below is just a small sample intended to indicate
# successful complition of the inference. Click the generated preview link
# to see the actual results.
s2dr4.inferutils.test(lonlat=lonlat, date=date)
