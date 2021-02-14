#!/usr/bin/env python
############################################################################################
# Hellen-One: A board processing script.
# (c) andreika <prometheus.pcb@gmail.com>
############################################################################################

from __future__ import print_function

import os, sys, shutil, errno
import csv, re
import subprocess

if len(sys.argv) < 4:
	print ("Error! Please specify the project base name, frame name, revision and optional BOM replacement list.")
	sys.exit(1)

project_base = sys.argv[1]
frame_name = sys.argv[2]
frame_rev = sys.argv[3]
if len(sys.argv) > 3:
	bom_replace = sys.argv[4]
else:
	bom_replace = ""

board_prefix = "hellen"

imageDpi = "600"

# these should match the definitions in the parent shell script (create_board.sh)!
project_name = board_prefix + frame_name
board_name = project_name + "-" + frame_rev
project_path = project_base + "/" + project_name + "/boards/" + board_name
frame_path = project_path + "/frame"
board_path = project_path + "/board"
board_path_name = board_path + "/" + board_name
board_misc_path = board_path + "/misc"
board_misc_path_name = board_misc_path + "/" + board_name
merged_gerber_path = board_path + "/gerber"
board_cfg_path = board_path + "/board.cfg"
board_place_path = board_path + "/board_place.txt"
board_bom = board_path_name + "-BOM.csv"
board_cpl = board_path_name + "-CPL.csv"
board_img = board_path_name + ".png"
board_img_top = board_misc_path_name + "-top.png"
board_img_bottom = board_misc_path_name + "-bottom.png"
board_img_outline = board_misc_path_name + "-outline.png"
board_img_components = board_misc_path_name + "-components.png"

node_bin = "node"
rotations = "bin/jlc_kicad_tools/cpl_rotations_db.csv"

# the format is: "Module:module_name/module_rev"
pat_module = re.compile(r'Module:([\w]+)/([\w\.]+)')

############################################################################################

def write_lines(f, lines):
	if type(lines) == str:
		f.write(lines + "\n")
	else:
		for l in lines:
			f.write(l + "\n")

def print_module(name, prefix, fileName, flag):
	with open(fileName, 'a') as file:
		write_lines(file, [
			"[" + name + "]",
			"Prefix = " + prefix,
			"*TopCopper=%(prefix)s.GTL",
			"*TopSoldermask=%(prefix)s.GTS",
			"*TopSolderPasteMask=%(prefix)s.GTP",
			"*TopSilkscreen=%(prefix)s.GTO",
			"*BottomCopper=%(prefix)s.GBL",
			"*BottomSoldermask=%(prefix)s.GBS",
			"*BottomSilkscreen=%(prefix)s.GBO",
			"*Keepout=%(prefix)s.GKO",
			"Drills=%(prefix)s.DRL"])
		if (flag == 1):
			write_lines(file, [
				"ToolList = nul",
				"Placement = nul",
				"BoardOutline = nul"])
		else:
			write_lines(file, "BoardOutline=%(prefix)s.GM15")

def append_cpl(src_fname, dst_fname, x, y):
	print ("* appending the CPL with offset (" + str(x) + "," + str(y) + ")...")
	with open(src_fname, 'rb') as src_f, open(dst_fname, 'a') as dst_f:
		reader = csv.reader(src_f, delimiter=',')
		i=0
		# skip header
		next(src_f)
		for row in reader:
			des = row[0]
			cxmm = row[1]
			cymm = row[2]
			lay = row[3]
			rot = row[4]
			# remove module designators
			if (re.match("^M[0-9]+$", des)):
				print ("* (skipping " + des + ")")
				continue
			
			# remove "mm" suffix
			cx = float(cxmm.replace("mm", ""))
			cy = float(cymm.replace("mm", ""))
			# offset the coordinates
			x_offset = cx + float(x)
			y_offset = cy + float(y)
			write_lines(dst_f, des + "," + str(x_offset) + "mm," + str(y_offset) + "mm," + lay + "," + rot)
			i = i + 1
			print (str(i) + " parts processed...", end = "\r")

def append_bom(src_fname, dst_fname):
	print ("* appending the BOM...")
	with open(src_fname, 'rb') as src_f, open(dst_fname, 'a') as dst_f:
		reader = csv.reader(src_f, delimiter=',')
		i = 0
		# skip header
		next(src_f)
		for row in reader:
			comment = row[0]
			des = row[1]
			footprint = row[2]
			lcsc = row[3]

			# remove module designators
			if (re.match("^M[0-9]+$", des)):
				print ("* (skipping " + des + ")")
				continue
			write_lines(dst_f, "\"" + comment + "\",\"" + des + "\",\"" + footprint + "\",\"" + lcsc + "\"")
			i = i + 1
			print (str(i) + " parts processed...", end = "\r")

def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise

def print_to_file(fileName, mode, lines):
	with open(fileName, mode) as f:
		write_lines(f, lines)

def delete_file(fileName):
	if os.path.exists(fileName):
		os.remove(fileName)

############################################################################################

print ("Removing old files of the board...")

try:
	if os.path.exists(board_path):
		shutil.rmtree(board_path)
except OSError as e:
	if exc.errno == errno.EEXIST and os.path.isdir(path):
		pass
	else:
		print ("Error: %s - %s." % (e.filename, e.strerror))
		sys.exit(1)

print ("Creating " + board_name + "...")

mkdir_p(board_path)
mkdir_p(board_misc_path)
mkdir_p(merged_gerber_path)

# create configs
print_to_file(board_cfg_path, "w", [
		"[DEFAULT]",
		"projdir = .",
		"",
		"[Options]",
		"ExcellonLeadingZeros = 0",
		"MeasurementUnits = inch",
		"AllowMissingLayers = 1"])

# board gerbers
print_module("MergeOutputFiles", merged_gerber_path + "/" + board_name, board_cfg_path, 1)

# frame gerbers
print_module(frame_name, frame_path + "/" + frame_name, board_cfg_path, 0)

# the frame should always have zero coordinates, matching the left-bottom keepout border
print_to_file(board_place_path, "w", frame_name + " 0.000 0.000")

# add frame's BOM & CPL
print_to_file(board_cpl, "w", ["Designator,Mid X,Mid Y,Layer,Rotation"])
print_to_file(board_bom, "w", ["Comment,Designator,Footprint,LCSC Part #"])

append_cpl(frame_path + "/" + frame_name + "-CPL.csv", board_cpl, "0", "0")
append_bom(frame_path + "/" + frame_name + "-BOM.csv", board_bom)

schem_list = [frame_path + "/" + frame_name + "-schematic.pdf"]

print ("Processing modules...")
modules_list = []
with open(frame_path + "/" + frame_name + "-BOM.csv", 'r') as bom_f:
	bom_reader = csv.reader(bom_f, delimiter=',')
	# skip header
	next(bom_f)
	for bom_row in bom_reader:
		module = bom_row[0]
		des = bom_row[1]
		footprint = bom_row[2]
		# is it a module?
		mod = pat_module.match(module)
		if mod:
			print ("  ** Inserting " + module + " into " + des + "...")
			module_name = mod.group(1)
			module_rev = mod.group(2)
			
			# get module coords from the CPL file
			with open(frame_path + "/" + frame_name + "-CPL.csv", 'r') as cpl_f:
				cpl_reader = csv.reader(cpl_f, delimiter=',')
				# skip header
				next(cpl_f)
				for cpl_row in cpl_reader:
					if des in cpl_row[0]:
						cxmm = cpl_row[1]
						cymm = cpl_row[2]
						lay = cpl_row[3]
						rot = cpl_row[4]
						xmm = cpl_row[5]
						ymm = cpl_row[6]
						# remove "mm" suffix
						x = float(xmm.replace("mm", ""))
						y = float(ymm.replace("mm", ""))
						# convert into inches (the gerber coords are imperial)
						x_inch = x / 25.4
						y_inch = y / 25.4
	
						print ("  ** adding " + module_name + "/" + module_rev + ", coords: " + str(x_inch) + "\", " + str(y_inch) + "\" (" + str(x) + " mm, " + str(y) + " mm)")

						# add module gerbers
						module_path = "modules/" + module_name + "/" + module_rev
						print_module(module_name, module_path + "/" + module_name, board_cfg_path, 0)
						# write abs. coords
						print_to_file(board_place_path, "a", module_name + " " + str(x_inch) + " " + str(y_inch))

						append_cpl(module_path + "/" + module_name + "-CPL.csv", board_cpl, x, y)

						append_bom(module_path + "/" + module_name + "-BOM.csv", board_bom)

						# adding schematics PDF for merging at the end
						schem_list.append(module_path + "/" + module_name + "-schematic.pdf")
						break

print ("* Done!")

print ("Merging gerbers...")
p = subprocess.Popen([sys.executable, "bin/gerbmerge/gerbmerge", 
	"--place-file=" + board_place_path, 
	board_cfg_path], 
	stdin=subprocess.PIPE)
# pass 'y' symbol to the subprocess as if a user pressed 'yes'
p.communicate(input='y\n')[0]

print ("Post-processing BOM...")
subprocess.call([sys.executable, "bin/process_BOM.py", 
	board_bom, 
	bom_replace])

print ("Merging Schematics...")
subprocess.call([sys.executable, "bin/python-combine-pdfs/python-combinepdf.py"]
	+ schem_list 
	+ ["-o", board_path_name + "-schematic.pdf"])

print ("Rendering TOP side image...")
subprocess.call([sys.executable, "bin/render_gerber.py", 
	merged_gerber_path, 
	board_img_top, 
	"top", 
	imageDpi])

print ("Rendering BOTTOM side image...")
subprocess.call([sys.executable, "bin/render_gerber.py", 
	merged_gerber_path, 
	board_img_bottom, 
	"bottom", 
	imageDpi])

print ("Rendering OUTLINE image...")
subprocess.call([sys.executable, "bin/render_gerber.py", 
	merged_gerber_path, 
	board_img_outline, 
	"outline", 
	imageDpi])

print ("Merging 3D-models of components...")
subprocess.call([sys.executable, "bin/create_3d_components.py", 
	board_place_path, 
	board_cfg_path, 
	board_misc_path_name + "-3D.wrl.gz"])

print ("Rendering a 3D-model of the board components...")
subprocess.call([node_bin, "bin/render_vrml/render_components.js", 
	board_misc_path_name + "-3D.wrl.gz", 
	board_img_components, 
	imageDpi])

print ("Creating a composite board image...")
subprocess.call([node_bin, "bin/render_vrml/render_board.js", 
	board_img_top, 
	board_img_outline, 
	board_img_components, 
	board_img, 
	imageDpi])

print ("Creating an interactive html BOM...")
subprocess.call([sys.executable, "bin/gen_iBOM.py",
	project_name,
	frame_rev,
	imageDpi,
	merged_gerber_path + "/" + board_name + ".GKO",
	merged_gerber_path + "/" + board_name + ".GTO",
	board_img,
	board_bom,
	board_cpl,
	"./ibom-data",
	rotations,
	board_path_name + "-ibom.html"])

print ("Cleaning up...")
delete_file(board_cfg_path)
delete_file(board_place_path)

print ("Creating a zip-archive with gerbers...")
shutil.make_archive(board_path_name + "-gerber", "zip", board_path, "gerber")

print ("Board processing done!")
