#!/usr/bin/env python3

'''
WfFormat workflow generator for the Montage toolkit. The generated
workflow will be in WfCommons WfFormat JSON (schema v1.5).

Based on the YAML generator with WfFormat output instead of YAML.

#  Copyright 2025 HyperFlow WMS Team
#  Licensed under the MIT License
'''

import os
import argparse
import re
import subprocess
import sys
import json
from datetime import datetime

# Insert this directory in our search path
os.sys.path.insert(0, os.getcwd())

from astropy.io import ascii


class WfFormatWorkflow:
    """Represents a workflow in WfCommons WfFormat (schema v1.5)"""

    def __init__(self, name):
        self.name = name
        self.specification_tasks = []
        self.specification_files = {}
        self.task_counter = 0
        self.outputs = []  # Track final workflow outputs
        self.file_metadata = {}  # Track source_url and is_input for rc.txt generation

    def add_file(self, name, source_url=None, is_input=False, is_output=False):
        """Register a file in the workflow specification (compatible with YAML API)"""
        if name not in self.specification_files:
            self.specification_files[name] = {
                'id': name,
                'sizeInBytes': 0  # We don't know size at generation time
            }
            # Store metadata for rc.txt generation
            self.file_metadata[name] = {
                'source_url': source_url,
                'is_input': is_input,
                'is_output': is_output
            }
            if is_output:
                self.mark_output(name)
        return name

    def add_task(self, executable, args, inputs, outputs, config=None):
        """Add a task to the workflow specification (compatible with YAML API)"""
        task_id = f"ID{self.task_counter:06d}"
        self.task_counter += 1

        task = {
            'name': f"{executable}_{self.task_counter}",
            'id': task_id,
            'parents': [],  # Will be computed later
            'children': [],  # Will be computed later
            'inputFiles': inputs if inputs else [],
            'outputFiles': outputs if outputs else []
        }

        # Register files
        for input_file in inputs:
            self.add_file(input_file)
        for output_file in outputs:
            self.add_file(output_file)

        self.specification_tasks.append(task)
        return task_id

    def mark_output(self, filename):
        """Mark a file as workflow output (compatible with YAML API)"""
        if filename not in self.outputs:
            self.outputs.append(filename)

    def _compute_dependencies(self):
        """Compute parent-child relationships based on file dependencies"""
        # Build file producers and consumers maps
        producers = {}  # file -> task_id that produces it
        consumers = {}  # file -> [task_ids that consume it]
        
        for task in self.specification_tasks:
            task_id = task['id']
            
            # Track producers
            for output_file in task['outputFiles']:
                producers[output_file] = task_id
            
            # Track consumers
            for input_file in task['inputFiles']:
                if input_file not in consumers:
                    consumers[input_file] = []
                consumers[input_file].append(task_id)
        
        # Compute dependencies
        for task in self.specification_tasks:
            task_id = task['id']
            parents = []
            children = []
            
            # Parents: tasks that produce this task's inputs
            for input_file in task['inputFiles']:
                if input_file in producers:
                    parent_id = producers[input_file]
                    if parent_id != task_id and parent_id not in parents:
                        parents.append(parent_id)
            
            # Children: tasks that consume this task's outputs
            for output_file in task['outputFiles']:
                if output_file in consumers:
                    for child_id in consumers[output_file]:
                        if child_id != task_id and child_id not in children:
                            children.append(child_id)
            
            task['parents'] = parents
            task['children'] = children

    def to_wfformat(self):
        """Convert workflow to WfFormat JSON (schema v1.5)"""
        # Compute dependencies
        self._compute_dependencies()
        
        # Build WfFormat structure
        wfformat = {
            'name': self.name,
            'schemaVersion': '1.5',
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'workflow': {
                'specification': {
                    'tasks': self.specification_tasks,
                    'files': list(self.specification_files.values())
                },
                'execution': {
                    'makespanInSeconds': 0.0,
                    'executedAt': datetime.utcnow().isoformat() + 'Z',
                    'tasks': [
                        {
                            'id': task['id'],
                            'runtimeInSeconds': 0.0
                        }
                        for task in self.specification_tasks
                    ],
                    'machines': [
                        {
                            'nodeName': 'montage-generator',
                            'cpu': {
                                'count': 1,
                                'speed': 0
                            }
                        }
                    ]
                }
            }
        }
        
        return wfformat

    def write(self, filename):
        """Write workflow to WfFormat JSON file"""
        wfformat = self.to_wfformat()
        
        with open(filename, 'w') as f:
            json.dump(wfformat, f, indent=2)
        
        print(f"WfFormat workflow written to {filename}")
        print(f"  Tasks: {len(self.specification_tasks)}")
        print(f"  Files: {len(self.specification_files)}")


# Copy all Montage-specific functions from montage-workflow-yaml.py
def which(file):
    for path in os.environ['PATH'].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
            return os.path.join(path, file)
    return None


def resolve_object_name(center):
    """Resolve object name to RA/Dec coordinates if needed"""
    # Try to parse as coordinates first
    parts = center.split()
    if len(parts) == 2:
        try:
            # Already coordinates
            return (float(parts[0]), float(parts[1]))
        except ValueError:
            pass

    # Must be an object name - resolve it
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u

        # Try to resolve using astropy
        coord = SkyCoord.from_name(center)
        ra = coord.ra.degree
        dec = coord.dec.degree
        return (ra, dec)
    except Exception as e:
        raise ValueError(f"Could not resolve object name '{center}': {e}")


def generate_region_hdr(wf, center, degrees):
    """Generate region header files"""

    (crval1, crval2) = resolve_object_name(center)
    crval1 = float(crval1)
    crval2 = float(crval2)

    cdelt = 0.000277778
    naxis = int((float(degrees) / cdelt) + 0.5)
    crpix = (naxis + 1) / 2.0

    # Generate region.hdr
    f = open('data/region.hdr', 'w')
    f.write('SIMPLE  = T\n')
    f.write('BITPIX  = -64\n')
    f.write('NAXIS   = 2\n')
    f.write('NAXIS1  = %d\n' %(naxis))
    f.write('NAXIS2  = %d\n' %(naxis))
    f.write('CTYPE1  = \'RA---TAN\'\n')
    f.write('CTYPE2  = \'DEC--TAN\'\n')
    f.write('CRVAL1  = %.6f\n' %(crval1))
    f.write('CRVAL2  = %.6f\n' %(crval2))
    f.write('CRPIX1  = %.6f\n' %(crpix))
    f.write('CRPIX2  = %.6f\n' %(crpix))
    f.write('CDELT1  = %.9f\n' %(-cdelt))
    f.write('CDELT2  = %.9f\n' %(cdelt))
    f.write('CROTA2  = %.6f\n' %(0.0))
    f.write('EQUINOX = %d\n' %(2000))
    f.write('END\n')
    f.close()

    wf.add_file('region.hdr',
                source_url='file://' + os.getcwd() + '/data/region.hdr',
                is_input=True)

    # Generate oversized region header
    f = open('data/region-oversized.hdr', 'w')
    f.write('SIMPLE  = T\n')
    f.write('BITPIX  = -64\n')
    f.write('NAXIS   = 2\n')
    f.write('NAXIS1  = %d\n' %(naxis + 3000))
    f.write('NAXIS2  = %d\n' %(naxis + 3000))
    f.write('CTYPE1  = \'RA---TAN\'\n')
    f.write('CTYPE2  = \'DEC--TAN\'\n')
    f.write('CRVAL1  = %.6f\n' %(crval1))
    f.write('CRVAL2  = %.6f\n' %(crval2))
    f.write('CRPIX1  = %.6f\n' %(crpix + 1500))
    f.write('CRPIX2  = %.6f\n' %(crpix + 1500))
    f.write('CDELT1  = %.9f\n' %(-cdelt))
    f.write('CDELT2  = %.9f\n' %(cdelt))
    f.write('CROTA2  = %.6f\n' %(0.0))
    f.write('EQUINOX = %d\n' %(2000))
    f.write('END\n')
    f.close()

    wf.add_file('region-oversized.hdr',
                source_url='file://' + os.getcwd() + '/data/region-oversized.hdr',
                is_input=True)




def add_band(wf, band_id, center, degrees, survey, band, color):
    """Add a band processing pipeline to the workflow"""

    band_id = str(band_id)

    print('\nAdding band %s (%s %s -> %s)' %(band_id, survey, band, color))

    # Data find - go a little bit outside the box
    degrees_datafind = str(float(degrees) * 1.42)
    cmd = 'mArchiveList %s %s \'%s\' %s %s data/%s-images.tbl' \
          %(survey, band, center, degrees_datafind, degrees_datafind, band_id)
    print('Running sub command: ' + cmd)
    if subprocess.call(cmd, shell=True) != 0:
        print('Command failed!')
        sys.exit(1)

    wf.add_file('%s-images.tbl' %(band_id),
                source_url='file://' + os.getcwd() + '/data/%s-images.tbl' %(band_id),
                is_input=True)

    # Generate image tables
    raw_tbl = '%s-raw.tbl' %(band_id)
    projected_tbl = '%s-projected.tbl' %(band_id)
    corrected_tbl = '%s-corrected.tbl' %(band_id)

    with open('data/' + raw_tbl, 'w') as f:
        f.write('')
    with open('data/' + projected_tbl, 'w') as f:
        f.write('')
    with open('data/' + corrected_tbl, 'w') as f:
        f.write('')

    wf.add_file(raw_tbl,
                source_url='file://' + os.getcwd() + '/data/' + raw_tbl,
                is_input=True)
    wf.add_file(projected_tbl,
                source_url='file://' + os.getcwd() + '/data/' + projected_tbl,
                is_input=True)
    wf.add_file(corrected_tbl,
                source_url='file://' + os.getcwd() + '/data/' + corrected_tbl,
                is_input=True)

    cmd = 'cd data && mDAGTbls %s-images.tbl region-oversized.hdr %s %s %s' \
          %(band_id, raw_tbl, projected_tbl, corrected_tbl)
    print('Running sub command: ' + cmd)
    if subprocess.call(cmd, shell=True) != 0:
        print('Command failed!')
        sys.exit(1)

    # Generate diff table
    cmd = 'cd data && mOverlaps %s-raw.tbl %s-diffs.tbl' \
          %(band_id, band_id)
    print('Running sub command: ' + cmd)
    if subprocess.call(cmd, shell=True) != 0:
        print('Command failed!')
        sys.exit(1)

    # Generate statfile table
    t = ascii.read('data/%s-diffs.tbl' %(band_id))
    t['stat'] = '                                                                  '
    for row in t:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['diff'])
        row['stat'] = '%s-fit.%s.txt' %(band_id, base_name)
    ascii.write(t, 'data/%s-stat.tbl' %(band_id), format='ipac')

    wf.add_file('%s-stat.tbl' %(band_id),
                source_url='file://' + os.getcwd() + '/data/%s-stat.tbl' %(band_id),
                is_input=True)

    # Add projection tasks for all input images
    data = ascii.read('data/%s-images.tbl' %(band_id))
    for row in data:
        base_name = re.sub('\.fits.*', '', row['file'])

        # Add input file
        in_fits = base_name + '.fits'
        wf.add_file(in_fits, source_url=row['URL'], is_input=True)

        # Add output files
        projected_fits = 'p' + base_name + '.fits'
        area_fits = 'p' + base_name + '_area.fits'
        wf.add_file(projected_fits)
        wf.add_file(area_fits)

        # Add mProject task
        wf.add_task(
            executable='mProject',
            args=['-X', in_fits, projected_fits, 'region-oversized.hdr'],
            inputs=['region-oversized.hdr', in_fits],
            outputs=[projected_fits, area_fits]
        )

    # Add mDiffFit tasks
    fit_txts = []
    data = ascii.read('data/%s-diffs.tbl' %(band_id))
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['diff'])

        plus = 'p' + row['plus']
        plus_area = re.sub('\.fits', '_area.fits', plus)
        minus = 'p' + row['minus']
        minus_area = re.sub('\.fits', '_area.fits', minus)
        fit_txt = '%s-fit.%s.txt' %(band_id, base_name)
        diff_fits = '%s-diff.%s.fits' %(band_id, base_name)

        wf.add_file(fit_txt)
        wf.add_file(diff_fits)

        wf.add_task(
            executable='mDiffFit',
            args=['-d', '-s', fit_txt, plus, minus, diff_fits, 'region-oversized.hdr'],
            inputs=[plus, plus_area, minus, minus_area, 'region-oversized.hdr'],
            outputs=[fit_txt]
        )
        fit_txts.append(fit_txt)

    # mConcatFit
    stat_tbl = '%s-stat.tbl' %(band_id)
    fits_tbl = '%s-fits.tbl' %(band_id)
    wf.add_file(fits_tbl)

    wf.add_task(
        executable='mConcatFit',
        args=[stat_tbl, fits_tbl, '.'],
        inputs=[stat_tbl] + fit_txts,
        outputs=[fits_tbl]
    )

    # mBgModel
    images_tbl = '%s-images.tbl' %(band_id)
    corrections_tbl = '%s-corrections.tbl' %(band_id)
    wf.add_file(corrections_tbl)

    wf.add_task(
        executable='mBgModel',
        args=['-i', '100000', images_tbl, fits_tbl, corrections_tbl],
        inputs=[images_tbl, fits_tbl],
        outputs=[corrections_tbl]
    )

    # mBackground tasks
    data = ascii.read('data/%s-raw.tbl' %(band_id))
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['file'])

        projected_fits = 'p' + base_name + '.fits'
        projected_area = 'p' + base_name + '_area.fits'
        corrected_fits = 'c' + base_name + '.fits'
        corrected_area = 'c' + base_name + '_area.fits'

        wf.add_file(corrected_fits)
        wf.add_file(corrected_area)

        wf.add_task(
            executable='mBackground',
            args=['-t', projected_fits, corrected_fits, projected_tbl, corrections_tbl],
            inputs=[projected_fits, projected_area, projected_tbl, corrections_tbl],
            outputs=[corrected_fits, corrected_area]
        )

    # mImgtbl - update corrected images table
    updated_corrected_tbl = '%s-updated-corrected.tbl' %(band_id)
    wf.add_file(updated_corrected_tbl)

    corrected_files = []
    data = ascii.read('data/%s-corrected.tbl' %(band_id))
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['file'])
        corrected_files.append(base_name + '.fits')

    wf.add_task(
        executable='mImgtbl',
        args=['.', '-t', corrected_tbl, updated_corrected_tbl],
        inputs=[corrected_tbl] + corrected_files,
        outputs=[updated_corrected_tbl]
    )

    # mAdd - create mosaic
    mosaic_fits = '%s-mosaic.fits' %(band_id)
    mosaic_area = '%s-mosaic_area.fits' %(band_id)
    wf.add_file(mosaic_fits)
    wf.add_file(mosaic_area)

    corrected_files_with_area = []
    data = ascii.read('data/%s-corrected.tbl' %(band_id))
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['file'])
        corrected_files_with_area.append(base_name + '.fits')
        corrected_files_with_area.append(base_name + '_area.fits')

    wf.add_task(
        executable='mAdd',
        args=['-e', updated_corrected_tbl, 'region.hdr', mosaic_fits],
        inputs=[updated_corrected_tbl, 'region.hdr'] + corrected_files_with_area,
        outputs=[mosaic_fits, mosaic_area]
    )
    wf.mark_output(mosaic_fits)

    # mViewer - create JPEG for this channel
    mosaic_png = '%s-mosaic.png' %(band_id)
    wf.add_file(mosaic_png)

    wf.add_task(
        executable='mViewer',
        args=['-ct', '1', '-gray', mosaic_fits, '-1s', 'max', 'gaussian',
              '-png', mosaic_png],
        inputs=[mosaic_fits],
        outputs=[mosaic_png]
    )
    wf.mark_output(mosaic_png)


def color_png(wf, red_id, green_id, blue_id):
    """Create color PNG from three bands"""

    red_id = str(red_id)
    green_id = str(green_id)
    blue_id = str(blue_id)

    mosaic_png = 'mosaic-color.png'
    red_fits = '%s-mosaic.fits' %(red_id)
    green_fits = '%s-mosaic.fits' %(green_id)
    blue_fits = '%s-mosaic.fits' %(blue_id)

    wf.add_file(mosaic_png)

    wf.add_task(
        executable='mViewer',
        args=[
            '-red', red_fits, '-0.5s', 'max', 'gaussian-log',
            '-green', green_fits, '-0.5s', 'max', 'gaussian-log',
            '-blue', blue_fits, '-0.5s', 'max', 'gaussian-log',
            '-png', mosaic_png
        ],
        inputs=[red_fits, green_fits, blue_fits],
        outputs=[mosaic_png]
    )
    wf.mark_output(mosaic_png)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--work-dir', action='store', dest='work_dir',
                        help='Work directory to chdir to')
    parser.add_argument('--center', action='store', dest='center',
                        help='Center of the output, for example M17 or 56.5 23.75')
    parser.add_argument('--degrees', action='store', dest='degrees',
                        help='Number of degrees of side of the output')
    parser.add_argument('--band', action='append', dest='bands',
                        help='Band definition. Example: dss:DSS2B:red')
    args = parser.parse_args()

    if args.work_dir:
        os.chdir(args.work_dir)

    if os.path.exists('data'):
        print('data/ directory already exists')
        sys.exit(1)
    os.mkdir('data')

    # Resolve object name to coordinates if needed
    (ra, dec) = resolve_object_name(args.center)
    center_coords = f"{ra} {dec}"

    # Create WfFormat workflow
    wf = WfFormatWorkflow('montage')

    # Generate region header files
    generate_region_hdr(wf, args.center, args.degrees)

    # Process each band (use resolved coordinates for mArchiveList)
    band_id = 0
    color_band = {}
    for band_def in args.bands:
        band_id += 1
        (survey, band, color) = band_def.split(':')
        add_band(wf, band_id, center_coords, args.degrees, survey, band, color)
        color_band[color] = band_id

    # Create color image if we have RGB bands
    if 'red' in color_band and 'green' in color_band and 'blue' in color_band:
        color_png(wf, color_band['red'], color_band['green'], color_band['blue'])

    # Write replica catalog (rc.txt) for Pegasus compatibility
    # Lists all input files with their source URLs
    with open('data/rc.txt', 'w') as rc:
        for filename, metadata in wf.file_metadata.items():
            if metadata.get('is_input') and metadata.get('source_url'):
                url = metadata['source_url']
                # Determine site label based on URL
                if url.startswith('file://'):
                    site_label = 'local'
                elif 'irsa.ipac.caltech.edu' in url or 'montage.ipac.caltech.edu' in url:
                    site_label = 'ipac'
                else:
                    site_label = 'remote'
                rc.write(f'{filename} "{url}"  pool="{site_label}"\n')

    # Write workflow to WfFormat JSON
    wf.write('data/montage-workflow.json')


if __name__ == '__main__':
    main()
