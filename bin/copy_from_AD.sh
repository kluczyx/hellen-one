#!/bin/bash

project_base="${1}"
type="${2}"
name="${3}"
rev="${4}"

src_path="../${type}/hellen1-${name}/jlc-${rev}"
if [ $type = "frames" ]; then
	dst_path="${project_base}/hellen${name}/boards/hellen${name}${rev}/frame"
else
	dst_path="${type}/${name}/${rev}"
fi

echo "Copying ${type} ${name}-${rev} to the repository (${dst_path})..."

mkdir -p ${dst_path}

# copy top layer gerbers
cp ${src_path}/${name}.GT* ${dst_path}
# copy bottom layer gerbers
cp ${src_path}/${name}.GB* ${dst_path}
# copy keepout layer
cp ${src_path}/${name}.GKO ${dst_path}
# copy "mechanical 15" module outline layer
cp ${src_path}/${name}.GM15 ${dst_path}
# copy NC drill
cp ${src_path}/${name}.TXT ${dst_path}/${name}.DRL 2> /dev/null || (echo "* Skipping Drill for ${name}..." && >"${dst_path}/${name}.DRL")
# copy the schematic
cp ${src_path}/${name}-schematic.PDF ${dst_path}/${name}-schematic.pdf
# copy the PCB 3D rendered view
cp ${src_path}/${name}-pcb3d.PDF ${dst_path}/${name}-pcb3d.pdf
# copy the VRML 3D components
cp ${src_path}/${name}-vrml.wrl ${dst_path}/${name}-vrml.wrl
# copy the BOM
sed -E ":a;N;s/Comment.+\n/Comment,Designator,Footprint,LCSC Part #/g" ${src_path}/${name}-BOM.csv > ${dst_path}/${name}-BOM.csv
# process and copy CPL
python3 ./bin/jlc_kicad_tools/jlc_fix.py -o ${dst_path} ${src_path} ${name}-altium-CPL.csv ${name}-CPL.csv
# create a footprint library from PCAD ASCII file
python ./bin/create_footprints_from_pcad.py ${src_path}/${name}-pcad.PCB ibom-data
