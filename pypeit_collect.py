'''
This scripts collects all relevant pypeit output for one night and one instrument:
* Science targets spectra
* Reduction pipeline log files and PDF/PNG files

This script should be run in the folder that contains the raw data (the 'rawfldr'). 

The script makes the following assumptions:
* Only one science target was extracted from each raw image (i.e., no more than one science target in the slit)
* All reduction pipeline products are in a folder called rawfldr/reduce/, where rawfldr is the folder where the raw data lies, and where this script is run from (change FLDR_REDUCE below if you want/need to re-name the reduce/ folder)
* The same instrument configuration was used for all targets (edit FLDR_INST below if you used an instrument configuration other than MDM+OSMOS4k)
* Co-added spectra have "coadd" somewhere in the fits filename

The collected output will be stored in /rawfldr/reduce/finalspectra/ and /rawfldr/reduce/finallog/ folders.
'''

import os
import shutil
from datetime import date
import numpy as np
import astropy.io.fits as pf
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pdb

# Edit these as necessary -----------------------------------------------------
FLDR_REDUCE = 'reduce/' # Change this if you're naming the main reduction folder differently
FLDR_INST = 'mdm_osmos_mdm4k_A/' # Change this if instrument changes

# Define some variables -------------------------------------------------------
curdir = os.getcwd() + '/'
fldr_sci = curdir + FLDR_REDUCE + FLDR_INST + 'Science/'
fldr_png = curdir + FLDR_REDUCE + FLDR_INST + 'QA/PNGs/'
fldr_finalsp = curdir + FLDR_REDUCE + 'finalspectra/'
fldr_finallog = curdir + FLDR_REDUCE + 'finallog/'
today = date.today()
todaystr = today.strftime('%Y/%m/%d')

if not os.path.isdir(fldr_finalsp):
    os.mkdir(fldr_finalsp)
if not os.path.isdir(fldr_finallog):
    os.mkdir(fldr_finallog)

# Gather names of relevant files ----------------------------------------------
# 1dspec filenames from the Science/ folder
tmpfiles = os.listdir(fldr_sci)
specfiles = []
for f in tmpfiles:
    if f.startswith('spec1d') and f.endswith('.fits'):
        specfiles.append(f)
specfiles.sort()

# PNG files from the QA/ folder
tmpfiles = os.listdir(fldr_png)
pngfiles = []
for f in tmpfiles:
    if f.find('_obj_') != -1:
        pngfiles.append(f)
pngfiles.sort()

# Loop through PNG files to get user input ------------------------------------
plt.ion()
extnums = [] # To store the relevant extension number from each image
for f in pngfiles:
    plt.close()
    img = mpimg.imread(fldr_png + f)
    imgplot = plt.imshow(img)
    plt.axis('off')
    plt.margins(0,0)
    fig = plt.gcf()
    fig.set_tight_layout(True)
    plt.show()
    # User must identify which object is the relevant science target
    tmpCommand = None
    while tmpCommand is None:
        tmpCommand = input('Which object is the science target? (left to right 1, 2... Enter zero if none) ')
        try:
            tmpCommand = int(tmpCommand) # It'll check if input is integer
        except ValueError:
            tmpCommand = None
        extnums.append(tmpCommand)
plt.close()

# Create new fits -------------------------------------------------------------
for ispec, specf in enumerate(specfiles):

    # Co-added files can just be copy/pasted (and re-named)
    if specf.find('coadd') != -1:
        h = pf.open(fldr_sci + specf)
        primaryHDU = h[0]
        sciobjname = primaryHDU.header['TARGET']
        x=shutil.copy2(fldr_sci + specf, fldr_finalsp + sciobjname + '_coadd.fits') 
        continue

    # Match specfile with png file
    filenum = specf[specf.find('_')+1:specf.find('-')]
    pngfmatch = None
    for ipng, pngf in enumerate(pngfiles):
        if pngf.find(filenum) != -1:
            pngfmatch = ipng
            break
    
    if pngfmatch is not None:
        extn = extnums[pngfmatch]
        # If user entered zero, then skip file
        if extn == 0: continue
        
        # Collect the primary hdu to use as the primary hdu in the new fits file
        h = pf.open(fldr_sci + specf)
        primaryHDU = h[0]
        sciobjname = primaryHDU.header['TARGET']

        # Add and edit some keys
        primaryHDU.header['TELESCOP'] = 'MDM 2.4m'
        primaryHDU.header['HISTORY'] = 'This file was built on ' + todaystr + ' by simplifying'
        primaryHDU.header['HISTORY'] = 'the pypeit reduction pipeline output, assuming'
        primaryHDU.header['HISTORY'] = 'only one science target per OSMOS image.'
        primaryHDU.header['HISTORY'] = 'A. Nunez: alejo.nunez@gmail.com'
        # Delete the some keys that are not relevant anymore
        deletestuff = True
        try:
            nspec = primaryHDU.header['NSPEC']
        except KeyError:
            deletestuff = False
        if deletestuff:
            for ispec in range(nspec):
                keynm = 'EXT' + str(ispec).zfill(4)
                del primaryHDU.header[keynm]
            del primaryHDU.header['NSPEC']

        # Copy the table HDU indicated by the user to collect
        tableHDU = h[extn]

        # Create new fits file
        hdul = pf.HDUList([primaryHDU, tableHDU])
        newfitsname = fldr_finalsp + sciobjname + '.fits'
        ctr = 1
        while os.path.isfile(newfitsname):
            ctr = ctr + 1
            newfitsname = fldr_finalsp + sciobjname + '_' + str(ctr) + '.fits'
        hdul.writeto(newfitsname, output_verify='warn', overwrite=True)
    else:
        print('Could not find a matching aperture PNG for file ' + specf + '. Skipping it.')

# Collect all log, PDF, and PNG files -----------------------------------------
# logs and pars
x=shutil.copy2(curdir + FLDR_REDUCE + FLDR_INST + FLDR_INST[:-1] + '.log', fldr_finallog) # total log
x=shutil.copy2(curdir + FLDR_REDUCE + FLDR_INST + FLDR_INST[:-1] + '.pypeit', fldr_finallog) # input table
x=shutil.copy2(fldr_sci + 'fluxing.par', fldr_finallog) # parameters for fluxing step
x=shutil.copy2(fldr_sci + 'sensfunc.par', fldr_finallog) # parameters for sensitivity function
if os.path.isfile(curdir + 'README.txt'):
    x=shutil.copy2(curdir + 'README.txt', fldr_finallog)
if os.path.isfile(curdir + 'readme.txt'):
    x=shutil.copy2(curdir + 'readme.txt', fldr_finallog)

# PNGs
for fname in os.listdir(fldr_png):
    if fname.endswith('.png'):
        x=shutil.copy2(fldr_png + fname, fldr_finallog)

# PDFs
for fname in os.listdir(fldr_sci):
    if fname.endswith('.pdf'):
        x=shutil.copy2(fldr_sci + fname, fldr_finallog)

print('Output consolidated in the finalspectra/ and finallog/ folders.')
