import sqlite3
import math
import json
from numpy import *
from pathlib import Path
from PIL import Image

#get the stuff from the db
def loadProjections(db_path, tablename):
	with sqlite3.connect(db_path) as connection:
		rows = connection.execute(f"""SELECT angle_degrees, detector_count, light_values FROM {tablename} ORDER BY angle_degrees""").fetchall()
		projections = []
		for angle_degrees, detector_count, light_values in rows: #never gonna use detector_count bc thats just verification of how many things are in light_values
			values = array(json.loads(light_values))
			projections.append((int(angle_degrees), values))
	return projections

#get func for sorted table names used at the bottom
def getTablenames(db_path: Path):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("""SELECT name FROM sqlite_master WHERE type = 'table'""").fetchall()
    tables = []
    for (name,) in rows:
        position_text = name[len("slice_"):-len("cm")]
        tables.append((int(position_text), name))
    # dont sort by alphabetically bc 1000 would be before 2
    tables.sort(key=lambda item: item[0])
    return [name for _, name in tables]

#making the sinogram, explained in the previous readme
def getSinogram(projections):
	maximum_detector_count = max([len(values) for _, values in projections])
	#blank sinogram array
	sinogram = zeros((len(projections), maximum_detector_count))
	#padding is the offset of 0s to get to the data in the center
	for angle_index, (_, values) in enumerate(projections):
		padding = maximum_detector_count - len(values)
		start = padding // 2
		end = start + len(values)
		sinogram[angle_index, start:end] = values

	return sinogram

#sums up all lines that go through each pixel (most of the logic behind the chall)
def getPixelData(sinogram, angles, width, height):
	detector_count = sinogram.shape[1]
	detector_center = (detector_count - 1) / 2.0

	x = arange(width) - (width - 1) / 2.0
	y = arange(height) - (height - 1) / 2.0

	x_grid, y_grid = meshgrid(x, y) # every possible x and y
	pixeldata = zeros((height, width))	# empty array to hold pixel sums

	detector_indexes = arange(detector_count)
	#big loop that does most of the logic w the sinogram
	for projection, angle in zip(sinogram, angles):
		angle_rad = math.radians(angle)
		detector_pos = detector_center + x_grid * math.cos(angle_rad) + y_grid * math.sin(angle_rad)

		newsum = interp(
			detector_pos.ravel(),
			detector_indexes,
			projection,
			left=0,
			right=0
		).reshape(height, width)

		pixeldata += newsum

	return pixeldata

#converts reconstructed sum values into grayscale and saves it to output/
def save(pixeldata, outpath):
	#since all of the values are added up you have to weight the highest value at 255 and lowest at 0 and weigh the rest inbetween. Also skips outliers 0 and 100 so the image isnt mostly just grey but this isnt necessary its just a little filtering
	low, high = percentile(pixeldata, [1.0, 99.0])
	weighted = clip((pixeldata - low) / (high - low), 0.0, 1.0)
	imagedata = rint(weighted * 255.0).astype(uint8)

	Image.fromarray(imagedata).save(outpath)




#most of this stuff is self explanatory tbh
dir = Path(__file__).parent
db = dir / "scan2.sqlite"
outdir = dir / "output"
outdir.mkdir(exist_ok=True)

tablenames = getTablenames(db)
#simple for loop that was added for all tables
for name in tablenames:
	projections = loadProjections(db, name)
	#put stuff in a dict so its accessible by angle
	dict = {angle: values for angle, values in projections}
	imageWidth = len(dict[0]) #num of detectors at 0 is width as explained in the readme
	imageHeight = len(dict[90]) #num of detectors at 90 is height as explained in the readme
	angles = array([angle for angle, _ in projections])
	sinogram = getSinogram(projections)

	pixeldata = getPixelData(sinogram, angles, imageWidth, imageHeight)

	#images are named after their table names
	outpath = outdir / f"{name}.png"
	save(pixeldata, outpath)
	print(f"{name} done")
