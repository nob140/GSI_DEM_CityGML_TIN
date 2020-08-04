import io
import sys
import os
import xml
import xml.dom.minidom
import xml.etree.ElementTree as ET
import pandas as pd

def error(text):
	print(text)
	sys.exit()

def add_triangle(doc, trianglePatches, text):
	posList = doc.createElement("gml:posList")
	posList.appendChild(doc.createTextNode(text))
	LinearRing = doc.createElement("gml:LinearRing")
	LinearRing.appendChild(posList)
	exterior = doc.createElement("gml:exterior")
	exterior.appendChild(LinearRing)
	Triangle = doc.createElement("gml:Triangle")
	Triangle.appendChild(exterior)        
	trianglePatches.insertBefore(Triangle, None)

def conv_DEM_TINRelief(inputfile, outputfile):
	tree = ET.parse(inputfile)
	root = tree.getroot()

	child = root.find('.//{http://www.opengis.net/gml/3.2}tupleList')
	if child == None:
		error('Not correct data.')
	tupleList = pd.read_csv(io.StringIO(child.text), header=None)
	tupleList = tupleList[1]

	# gml:boundedBy
	hmin = min(tupleList)
	hmax = max(tupleList)

	boundedBy = root.find('.//{http://www.opengis.net/gml/3.2}boundedBy')
	if boundedBy == None:
		error('Not correct data.')

	child = root.find('.//{http://www.opengis.net/gml/3.2}lowerCorner')
	if child == None:
		error('Not correct data.')
	tmp = child.text.split()
	lowerCorner = [float(s) for s in tmp]

	child = root.find('.//{http://www.opengis.net/gml/3.2}upperCorner')
	if child == None:
		error('Not correct data.')
	tmp = child.text.split()
	upperCorner = [float(s) for s in tmp]

	# calculate mesh size
	child = root.find('.//{http://www.opengis.net/gml/3.2}high')
	if child == None:
		error('Not correct data.')
	tmp = child.text.split()
	high = [int(s) for s in tmp]
	xlen = high[0]+1
	ylen = high[1]+1

	dlat = (upperCorner[0] - lowerCorner[0])/ylen
	dlon = (upperCorner[1] - lowerCorner[1])/xlen

	child = root.find('.//{http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema}mesh')
	if child == None:
		error('Not correct data.')
	fid = child.text

	if xlen * ylen != len(tupleList):
		error('Data length is not correct.')

	# develop data for calculation
	data = {}
	for i in range(xlen * ylen):
		x = i % xlen
		y = int(i / xlen)
		#print(x, y, tupleList[i])
		if y == 0:
			data[x] = {}
		data[x][y] = str(tupleList[i])

	# CityGML document
	doc = xml.dom.minidom.Document()

	# core:CityModel
	CityModel = doc.createElementNS("http://www.opengis.net/citygml/2.0", "core:CityModel")
	CityModel.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
	CityModel.setAttribute("xmlns:gml", "http://www.opengis.net/gml")
	CityModel.setAttribute("xmlns:core", "http://www.opengis.net/citygml/2.0")
	CityModel.setAttribute("xmlns:dem", "http://www.opengis.net/citygml/relief/2.0")
	CityModel.setAttribute("xsi:schemaLocation", "http://www.opengis.net/gml http://schemas.opengis.net/gml/3.1.1/base/gml.xsd http://www.opengis.net/citygml/2.0 http://schemas.opengis.net/citygml/2.0/cityGMLBase.xsd http://www.opengis.net/citygml/relief/2.0 http://schemas.opengis.net/citygml/relief/2.0/relief.xsd")

	# gml:boundedBy
	Envelope = doc.createElement("gml:Envelope")
	Envelope.setAttribute("srsName", "http://www.opengis.net/def/crs/EPSG/0/6697")
	Envelope.setAttribute("srsDimension", "3")
	        
	node = doc.createElement("gml:lowerCorner")
	text = boundedBy[0][0].text + " " + str(hmin)
	node.appendChild(doc.createTextNode(text))
	Envelope.appendChild(node)

	node = doc.createElement("gml:upperCorner")
	text = boundedBy[0][1].text + " " + str(hmax)
	node.appendChild(doc.createTextNode(text))
	Envelope.insertBefore(node, None)

	node = doc.createElement("gml:boundedBy")
	node.appendChild(Envelope)
	CityModel.appendChild(node)

	# dem:TINRelief
	cityObjectMember = doc.createElement("core:cityObjectMember")

	ReliefFeature = doc.createElement("dem:ReliefFeature")
	ReliefFeature.setAttribute("gml:id", "RELIEF_" + fid)

	node = doc.createElement("gml:name")
	node.appendChild(doc.createTextNode("TIN LOD1"))
	ReliefFeature.insertBefore(node, None)

	node = doc.createElement("dem:lod")
	node.appendChild(doc.createTextNode("1"))
	ReliefFeature.insertBefore(node, None)

	reliefComponent = doc.createElement("dem:reliefComponent")

	TINRelief = doc.createElement("dem:TINRelief")
	TINRelief.setAttribute("gml:id", "TIN_" + fid)

	node = doc.createElement("gml:name")
	node.appendChild(doc.createTextNode("Ground"))
	TINRelief.insertBefore(node, None)

	node = doc.createElement("dem:lod")
	node.appendChild(doc.createTextNode("1"))
	TINRelief.insertBefore(node, None)

	tin = doc.createElement("dem:tin")

	TriangulatedSurface = doc.createElement("gml:TriangulatedSurface")
	TriangulatedSurface.setAttribute("gml:id", "Ground_" + fid)

	# gml:trianglePatches
	trianglePatches = doc.createElement("gml:trianglePatches")

	for y in range(ylen-1):
		for x in range(xlen-1):
			# center of mesh
			#lat = upperCorner[0] - y * dlat
			#lon = lowerCorner[1] + x * dlat
			lat = upperCorner[0] - (y + 0.5) * dlat
			lon = lowerCorner[1] + (x + 0.5) * dlon
			
			# upper left triangle
			#print(lat, lon, data[x][y], lat-dlat, lon, data[x][y+1], lat, lon+dlon, data[x+1][y])
			text = str(lat)   +" "+ str(lon)      +" "+ data[x][y]   +" "+ \
				str(lat-dlat) +" "+ str(lon)      +" "+ data[x][y+1] +" "+ \
				str(lat)      +" "+ str(lon+dlon) +" "+ data[x+1][y] +" "+ \
				str(lat)      +" "+ str(lon)      +" "+ data[x][y]
			#print(text)
			add_triangle(doc, trianglePatches, text)
			
			# lower right triangle
			#print(lat-dlat, lon+dlon, data[x+1][y+1], lat, lon+dlon, data[x+1][y], lat-dlat, lon, data[x][y+1])
			text = str(lat-dlat) +" "+ str(lon+dlon) +" "+ data[x+1][y+1] +" "+ \
				str(lat)         +" "+ str(lon+dlon) +" "+ data[x+1][y]   +" "+ \
				str(lat-dlat)    +" "+ str(lon)      +" "+ data[x][y+1]   +" "+ \
				str(lat-dlat)    +" "+ str(lon+dlon) +" "+ data[x+1][y+1]
			#print(text)
			add_triangle(doc, trianglePatches, text)

	# append all classes
	TriangulatedSurface.appendChild(trianglePatches)
	tin.appendChild(TriangulatedSurface)
	TINRelief.insertBefore(tin, None)
	reliefComponent.appendChild(TINRelief)
	ReliefFeature.insertBefore(reliefComponent, None)
	cityObjectMember.appendChild(ReliefFeature)
	CityModel.insertBefore(cityObjectMember, None)
	doc.insertBefore(CityModel, None)

	# output CityGML file
	with open(outputfile, "wb") as xml_file:
		xml_file.write(doc.toprettyxml(encoding="utf-8"))


if __name__ == '__main__':
	usage = 'Usage: python {} INPUT_DEM_FILE [OUTPUT_TIN_FILE] [--help]'.format(__file__)
	arguments = sys.argv
	if len(arguments) != 2 and len(arguments) != 3:
		error(usage)
	
	inputfile = arguments[1]
	if inputfile.startswith('-'):
		error(usage)
	
	if len(arguments) == 2:
		outputfile = inputfile.replace('.xml', '_TIN.xml')
	else:
		outputfile = arguments[2]
		if outputfile.startswith('-'):
			error(usage)
	
	#print('input is {}'.format(inputfile) + ' , output is {}'.format(outputfile))
	
	if os.path.exists(inputfile) == False:
		error(inputfile + " is not exist.")
	if os.path.isfile(inputfile) == False:
		error(inputfile + " is not file.")
	
	conv_DEM_TINRelief(inputfile, outputfile)
