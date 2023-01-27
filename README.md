NOTE : This is meant to be a demo of the old version of the code (developed around 2019)


TO run this build of ZPPicGen.py:
  - You will need python installed (pip/python, pip3/python3)
  - You will need pandas / PIL
    - install --> pip install pandas
              --> python -m pip install --upgrade Pillow
    - may need to update pip
  - or compile using PyInstaller or other python executable packager
  - The zip file includes the necessary files to run the program for BaseName <42221-100-91>
  - command in Windows 10 cmd, or Linux
    - python ZPPicGen.py Component_Dimensions.csv 42221-100-91

File information:
  - The included BaseName is 42221-100-91
  - The BaseName is just a file naming scheme to organize sets of input files
  - The board image names are "<BaseName> Top.png" and "<BaseName> Bottom.png"
    - each board has a bottom and top layer so each board has 2 images
  - The Component_Dimensions.csv file just lists the (x,y) dimensions of the electrical components
    - This file was modified and added to many times to include new components or resize existing ones
  - The <BaseName> config.csv file specifies which components to draw onto the board
    - It also designates how many images to generate, which components will go on which page, and what color the
      components will be drawn in
  - The <BaseName> pnp.csv file is a database file that contains information about the components
  - The <BaseName> missing.csv file will include any components contained in the config file but not found in the
    <BaseName> pnp.csv database
  - The <BaseName> coord.csv designates where the corners of the board is located.

Optional Arguments:
  - [-p] Specify an absolute PATH for input files.
  - [-t] tars input files and places them into <BaseName>_input_files.tar. (Works for Windows but not linux)
    - In order for this to run properly, use the [-p] option to specify the path you want the tar file to be
      generated in.
    - For .gz compression, need to make small change to tar codeblock at bottom of script.
      
New changes
    - Also later builds are able to read the input files from a <BaseName>_input_files.tar file.
  - [-d] Generates a <BaseName>_ResistorValues.csv file.
    - This file contains useful information about the resistors in the <BaseName> pnp.csv file
    - Was helpful to some engineers who worked at DDES
