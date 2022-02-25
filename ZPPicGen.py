#Previous Commit of ZPPicGen.py
#Current Version is part of DDES propreitary codebase
#incomplete, may not run without specified software (IrfanView), or proper image format/size


from PIL import Image, ImageDraw
import pandas as pd
import argparse
import sys
import logging
import time
import os
import csv
import tarfile

# command line arguments
parser=argparse.ArgumentParser()
parser.add_argument('ComponentFile',help='Name of the file that contains the component dimensions in mils, ex. <ComponentFile>.csv')
parser.add_argument('BaseName', help='The identifier that the files required must have, ex. <BaseName> Top.png / ,<BaseName> Bottom.png in directory')
parser.add_argument('-p','--path', nargs='?', default='cwd', help='The absolute path to the directory where the input files are stored. Default : cwd')
parser.add_argument('-t','--tar', action='store_true', help='Tars the input files and places into <BaseName>_input_files.tar')
parser.add_argument('-d','--datafile', action='store_true', help='Generates a sorted CANDI file using data from config.csv')
args=parser.parse_args()


ComponentFile=args.ComponentFile
BaseName=args.BaseName
directory=args.path
tar=args.tar
datafile=args.datafile

logging.basicConfig(filename='ZPPicGen.log',level=logging.INFO,format="%(asctime)s:%(levelname)s:%(message)s")

#assigns Basename files to variables
pnp_csv=BaseName+' pnp.csv'
coord_csv=BaseName+' coord.csv'
config_csv=BaseName+' config.csv'
component_dim_csv=ComponentFile

try:
    if(directory != 'cwd'):
        board_im_top=Image.open(directory + '\\' + BaseName + ' Top.png')
        board_im_bottom=Image.open(directory + '\\' + BaseName +' Bottom.png')
    else:
        board_im_top=Image.open(BaseName+' Top.png')
        board_im_bottom=Image.open(BaseName+' Bottom.png')

except FileNotFoundError:
    print (sys.exc_info()[0], 'occurred, Image must be in .png format, BaseName may be incorrect')

logging.info('top image loaded')
logging.info('bottom image loaded')

#Processes pick and place file and places into pandas DataFrame
def process_pnp(pnp_csv):
    try:
        if(directory != 'cwd'):
            comp_data=pd.read_csv(directory + '\\' + pnp_csv, delimiter=',', skiprows=[0,1,2,3,4,5,6,7,8,9,10,11])
        else:
            comp_data=pd.read_csv(pnp_csv, delimiter=',', skiprows=[0,1,2,3,4,5,6,7,8,9,10,11])

    except FileNotFoundError:
        print (sys.exc_info()[0], 'occurred, pnp file must be .csv format')
    logging.info('read in pnp.csv')

    comp_data.rename(columns={'Center-X(mil)':'x_values', 'Center-Y(mil)':'y_values'}, inplace=True)

    try:
        comp_data.sort_values('Footprint',axis=0,ascending=True, inplace=True)

    except KeyError:
        print (sys.exc_info()[0], 'occurred, pnp.csv file must have column "Footprint" where component type is listed')

    logging.info('pnp.csv sorted by Footprint')

    comp_data=comp_data.reset_index(drop=True)

    return comp_data

#gets the dimensions of components in the Dimensions csv
def get_dimensions(component_dim_csv,comp_data):
    default=(200,200)
    dimensions_values=[]
    row_list = []

    try:
        if(directory != 'cwd'):
            component_dim=pd.read_csv(directory + '\\' + component_dim_csv, delimiter=',', names=['Footprint','Width','Length'])
        else:
            component_dim=pd.read_csv(component_dim_csv, delimiter=',', names=['Footprint','Width','Length'])

    except FileNotFoundError:
        print (sys.exc_info()[0], 'occurred, Component_Dimensions.csv file was not found')

    logging.info('ComponentFile read in')

    for i in comp_data.itertuples():

        for j in component_dim.itertuples():
            if i.Footprint==j.Footprint:
                dimensions=(j.Width,j.Length)
                dimensions_values.append(dimensions)
                break
        else:
            dimensions_values.append(default)
            row_list.append([i.Designator, i.Footprint])

    try:
        comp_data.insert(len(comp_data.columns), 'Dimensions', dimensions_values)
    except ValueError:
        print (sys.exc_info()[0], 'occurred, Footprint values in <ComponentFile> do not match with data in pnp.csv, there must be a (width, length) for every Footprint in pnp.csv')

    return  comp_data

#splits DataFrame into sub-DataFrames that coorespond to number of pages requested
def splitDataFrameIntoSmaller(df, breakspots = [10000]):
    listOfDf = list()
    counter1=0
    counter2=1
    for j in range(0,len(breakspots)):
        if j==0:
            listOfDf.append(df[j:breakspots[j]])
        elif (j!=0) and (j+1)!=len(breakspots):
            listOfDf.append(df[breakspots[j-1]-counter1:breakspots[j]-counter2])
            counter1+=1
            counter2+=1
        elif (j+1)==len(breakspots):
            listOfDf.append(df[breakspots[j-1]-counter1:len(df)])

    return listOfDf

#gets the data set and organizes it into page DataFrames
def get_data_set(comp_data,config_csv):
    data_set=[]
    counter=0
    user_values=[]
    color_values=[]
    breaks=[]
    nominals = []
    nom_des = []
    confrim = 0
    res_num = 0

    try:
        if(directory != 'cwd'):
            config=pd.read_csv(directory + '\\' + config_csv,delimiter=',',names=['Designator', 'Color', 'Part_Number', 'Nominal'],na_values=['no info','.'])
        else:
            config=pd.read_csv(config_csv,delimiter=',',names=['Designator', 'Color', 'Part_Number', 'Nominal'],na_values=['no info','.'])

    except FileNotFoundError:
        print (sys.exc_info()[0], 'occurred, config.csv file was not found')

    logging.info('read in config.csv')

    for z in config.itertuples():
        if '-' in z.Color:
            color_values.append('PH')
        else:
            color_values.append(z.Color)
        if '-' in z.Designator:
            user_values.append('PH')
        else:
            user_values.append(z.Designator)
        if (z.Nominal[0] == 'R') and (z.Designator[0] == 'R'):
            nominals.append(z.Nominal)
            nom_des.append(z.Designator)
            res_num += 1

    nom_values = list()

    for string in nominals:
        split_str = string.split('-')
        nom_values.append(split_str[1])

    nom_floats = list()

    for nom in nom_values:
        if(nom[-1] == 'K'):
            nom_floats.append(float(nom[:-1]) * 1000)
        elif(nom[-1] == 'M'):
            nom_floats.append(float(nom[:-1]) * 1000000)
        elif(nom[-1] == 'G'):
            nom_floats.append(float(nom[:-1]) * 1000000000)
        else:
            nom_floats.append(float(nom))

    for i in user_values:
        confirm = 0
        counter+=1
        if i=='PH':
            breaks.append(counter-1)
        for j in comp_data.itertuples():
            if i==j.Designator:
                data_set.append(j)
                confirm = 1
        if((i != 'PH') and (confirm != 1)):
            print('Error: Component %s was not found in pnp.csv' % i)
            exit(1)

    breaks.append((len(data_set))+len(breaks))

    data_set=pd.DataFrame(data=data_set)

    for x in color_values:
        if (x != 'PH') and (int(x) not in [1,2,3,4]):
            print('Error: Color Values must be withing range [1-4]')
            exit(1)
        elif(x == 'PH'):
            color_values.remove(x)

    try:
        color_values=[int(x) for x in color_values]

    except ValueError:
        print( sys.exc_info()[0], 'occurred, make sure config.csv is formatted correctly, refer to README.txt')

    return data_set,user_values,color_values,breaks,nom_floats,nom_des,res_num

#returns list of board coordinates
def get_page_coor(data_set):
    board_coordinates=[]
    for i in data_set.itertuples():
        x=i.x_values
        y=i.y_values
        board_coor=(x,y)
        board_coordinates.append(board_coor)

    return board_coordinates

def get_trans_im(listOfDf, trans_im_top, trans_im_bottom):
    trans_ims=[]

    for i in range(len(listOfDf)):
        trans_ims.append(trans_im_top)

    return trans_ims

#gets coordinates of the corners of the baord in mils
def get_mil_corners(coord_csv):
    try:
        if(directory != 'cwd'):
            coord=pd.read_csv(directory + '\\' + coord_csv,sep=',',dtype=int)
        else:
            coord=pd.read_csv(coord_csv,sep=',',dtype=int)

    except FileNotFoundError:
        print (sys.exc_info()[0], 'occurred, coord.csv file was not found')

    corners=list(coord.columns.values)

# PSM, 7/30/19, I don't understand why the conversion to integer fails.  It will fail if the contents of the
# coord file is    -150,4150,3350,-150
# In this case (80992-100-01), the last coordinate retains the value of -150.1, and I think it is a string.
# I can't seem to figure out why this is going on, so I changed the coord file to the following, and
# everything works file:   -151,4150,3350,-150
# ***Bug Solved***

    try:
        corners=[int(float(i)) for i in corners]
    except TypeError:
        print (sys.exc_info()[0],'coord.csv values must be <class "int">')
#    for x in range(len(corners)):
#        print (corners[x])
    return corners

#gets the length and width of components
def get_len_wid(a,c,data_set):
    len_wid=[]
    rotation_values=[0,90,180,270,360]

    try:
        for i in data_set.itertuples():
            if i.Layer=='TopLayer':
                if (i.Rotation==90) or (i.Rotation==270):
                    rot_top=(i.Dimensions[1]*abs(c),i.Dimensions[0]*abs(a))
                    len_wid.append(rot_top)
                if (i.Rotation==180) or (i.Rotation==360) or (i.Rotation==0) or (i.Rotation not in rotation_values):
                    str_top=(i.Dimensions[0]*abs(a),i.Dimensions[1]*abs(c))
                    len_wid.append(str_top)
#               if i.Rotation not in rotation_values:
#                   raise ValueError('Rotation value must be 90, 180, 270, or 360')

            if i.Layer=='BottomLayer':
                if (i.Rotation==90) or (i.Rotation==270):
                    rot_bot=(i.Dimensions[1]*abs(c),i.Dimensions[0]*abs(a))
                    len_wid.append(rot_bot)
                if (i.Rotation==180) or (i.Rotation==360) or (i.Rotation==0) or (i.Rotation not in rotation_values):
                    str_bot=(i.Dimensions[0]*abs(a),i.Dimensions[1]*abs(c))
                    len_wid.append(str_bot)
 #              if i.Rotation not in rotation_values:
 #                  raise ValueError('Rotation value must be 0, 90, 180, 270, or 360')

    except AttributeError:
        print(sys.exc_info(),'occurred, pnp.csv column with rotation values must be titled "Rotation"')

    return len_wid

#gets the pixel coordinates of components
def get_pixel_coor(a,b,c,d,board_coordinates,data_set):
    #gets a coordinate for the transparent image (in pixels) that correlates with a coordinate in the csv in mils
    pixel_coordinates=[]

    center_axis=(board_im_bottom.size[0]/2)#4329.5

    for j, i in enumerate(data_set.itertuples()):
        if i.Layer=='TopLayer':
            try:
                trans_coor=round((a*(board_coordinates[j])[0])+b),round((c*(board_coordinates[j])[1])+d)
                pixel_coordinates.append(trans_coor)
            except TypeError:
                print (sys.exc_info(),'occurred, pnp.csv center x/y coordinates must be <class "int">, or columns are misaligned')

        elif i.Layer=='BottomLayer':
            try:
                trans_coor=round((a*(board_coordinates[j])[0]+b)),round((c*(board_coordinates[j])[1]+d))
                axis_distance=abs(trans_coor[0]-center_axis)

                if trans_coor[0]<=center_axis:
                    new_x=trans_coor[0]+(axis_distance*2)
                else:
                    new_x=trans_coor[0]-(axis_distance*2)

                pixel_coordinates.append((new_x,trans_coor[1]))

            except TypeError:
                print (sys.exc_info()[0],'occurred, pnp.csv center x/y coordinates must be <class "int"> or <class "float">, or columns are misaligned')


    return pixel_coordinates

board_im_top.putalpha(0)
board_im_bottom.putalpha(0)

# Draws componenets onto images
def draw_mapped_image(pixel_coordinates,data_set,len_wid,color_values,color_list):
    top=False
    bottom=False
    trans_im=Image.new('RGBA',board_im_top.size,color=(255,255,255,0))

    draw=ImageDraw.Draw(trans_im)

    for j, i in enumerate(data_set.itertuples()):

        if i.Layer=='TopLayer':
            top=True
            if (((len_wid[j]) [0]) == 0):
                print('Detected 0 length - 1st dimension')
                draw.ellipse([ ( (pixel_coordinates [j]) [0]) - ( ( (len_wid[j]) [1]) ), ( (pixel_coordinates [j]) [1]) - ( ( (len_wid[j]) [1]) ), ( (pixel_coordinates [j]) [0]) + ( ( (len_wid[j]) [1]) ), ( (pixel_coordinates [j]) [1]) + ( ( (len_wid[j]) [1]) ) ],color_list[color_values[j]-1],outline="black",width=2)
            elif (((len_wid[j]) [1]) == 0):
                print('Detected 0 length - 2nd dimension')
                draw.ellipse([ ( (pixel_coordinates [j]) [0]) - ( ( (len_wid[j]) [0]) ), ( (pixel_coordinates [j]) [1]) - ( ( (len_wid[j]) [0]) ), ( (pixel_coordinates [j]) [0]) + ( ( (len_wid[j]) [0]) ), ( (pixel_coordinates [j]) [1]) + ( ( (len_wid[j]) [0]) ) ],color_list[color_values[j]-1],outline="black",width=2)
            else:
                draw.rectangle([ ( (pixel_coordinates [j]) [0]) - ( ( (len_wid[j]) [0]) /2), ( (pixel_coordinates [j]) [1]) - ( ( (len_wid[j]) [1]) /2), ( (pixel_coordinates [j]) [0]) + ( ( (len_wid[j]) [0]) /2), ( (pixel_coordinates [j]) [1]) + ( ( (len_wid[j]) [1]) /2) ],color_list[color_values[j]-1],outline="black",width=2)

        if i.Layer=='BottomLayer':
            bottom=True
            if (((len_wid[j]) [0]) == 0):
                print('Detected 0 length - 1st dimension')
                draw.ellipse([ ( (pixel_coordinates [j]) [0]) - ( ( (len_wid[j]) [1]) ), ( (pixel_coordinates [j]) [1]) - ( ( (len_wid[j]) [1]) ), ( (pixel_coordinates [j]) [0]) + ( ( (len_wid[j]) [1]) ), ( (pixel_coordinates [j]) [1]) + ( ( (len_wid[j]) [1]) ) ],color_list[color_values[j]-1],outline="black",width=2)
            elif (((len_wid[j]) [1]) == 0):
                print('Detected 0 length - 2nd dimension')
                draw.ellipse([ ( (pixel_coordinates [j]) [0]) - ( ( (len_wid[j]) [0]) ), ( (pixel_coordinates [j]) [1]) - ( ( (len_wid[j]) [0]) ), ( (pixel_coordinates [j]) [0]) + ( ( (len_wid[j]) [0]) ), ( (pixel_coordinates [j]) [1]) + ( ( (len_wid[j]) [0]) ) ],color_list[color_values[j]-1],outline="black",width=2)
            else:
                draw.rectangle([ ( (pixel_coordinates [j]) [0]) - ( ( (len_wid[j]) [0]) /2), ( (pixel_coordinates [j]) [1]) - ( ( (len_wid[j]) [1]) /2), ( (pixel_coordinates [j]) [0]) + ( ( (len_wid[j]) [0]) /2), ( (pixel_coordinates [j]) [1]) + ( ( (len_wid[j]) [1]) /2) ],color_list[color_values[j]-1],outline="black",width=2)

    if top==True:
        im_t = board_im_top.copy()
        im_t.paste(trans_im,(0,0),trans_im)
        return im_t, top, bottom

    if bottom==True:
        im_b = board_im_bottom.copy()
        im_b.paste(trans_im,(0,0),trans_im)
        return im_b, top, bottom

# Organizes coordinates of components into horizonatal sectors for more readability of mapped images
def list_add(coord_list, data_set, max_y, side):
    sector = list()
    checkpoint = max_y - 300 # Number of pixels that the sector

    for i in data_set.itertuples():
        if (i.y_values >= checkpoint) and (i.y_values <= max_y) and (i.Layer == side) and (i.Designator[0] == 'R'):
            sector.append([i.x_values, i.y_values, i.Layer])

    coord_list.append(sector)

    return coord_list

def run_main(BaseName, datafile):
    #pulls data from pnp file
    comp_data=process_pnp(pnp_csv)

    #pulls data with added dimensions
    comp_data=get_dimensions(component_dim_csv, comp_data)

    #pulls the user component data from config.csv and corresponding pnp.csv data
    data_list = get_data_set(comp_data,config_csv)

    data_set=data_list[0]
    user_values=data_list[1]
    color_values=data_list[2]
    breaks=data_list[3]
    nominals=data_list[4]
    nom_des=data_list[5]
    res_num = data_list[6]

    logging.info('config.csv subdata pulled from pnp.csv')

    row_list = list()
    csv_name = BaseName + "_missing.csv"

    for row in data_set.itertuples():
        if(row.Dimensions == (200,200)):
            row_list.append([row.Designator, row.Footprint])

    with open(csv_name, 'w', newline = '') as file:
        writer = csv.writer(file)
        writer.writerow(["Designator", "Footprint"])
        for row in row_list:
            writer.writerow(row)

    #creates a list that keeps track of the first values of the subdataframes in split_data_frames
    first_values=[0]
    a=1
    for f in breaks:
        if (f==breaks[0]) or (f==breaks[1]):
            first_values.append(f)
        else:
            a+=1
            first_values.append(f-a)

    #splits data_set and color_values into seperate DataFrames based on config page break format
    split_data_frame=splitDataFrameIntoSmaller(data_set, breakspots=breaks)
    color_values=splitDataFrameIntoSmaller(color_values, breakspots=breaks)
    logging.info('config.csv data split into sub-dataframes for each image')
    for v in split_data_frame:
        logging.info(v)

    #gets the x,y mil coordinates from split_data_frame
    board_coordinates_list=[]
    for l in range(len(split_data_frame)):
        board_coordinates=get_page_coor(split_data_frame[l])
        board_coordinates_list.append(board_coordinates)
    logging.info('board coordinates pulled from pnp.csv for config.csv Designators')

    #gets corners from coords.csv for images
    corners=(get_mil_corners(coord_csv))
    board_orig=(corners[0],corners[1])
    trans_orig=(0,0)
    board_conc=(corners[2],corners[3])
    trans_conc=(board_im_top.size)
    logging.info('xy origin and conclusion coordinates pulled from coord.csv')

    #constants for math operations
    try:
        a=(trans_orig[0]-trans_conc[0])/(board_orig[0]-board_conc[0])
    except TypeError:
        print (sys.exc_info()[0],'occurred, pnp.csv center x/y coordinates must be <class "int"> or <class "float">, or columns are misaligned')
    try:
        b=trans_orig[0]-(a*board_orig[0])
    except TypeError:
        print (sys.exc_info()[0],'occurred, pnp.csv center x/y coordinates must be <class "int"> or <class "float">, or columns are misaligned')
    try:
        c=(trans_orig[1]-trans_conc[1])/(board_orig[1]-board_conc[1])
    except TypeError:
        print (sys.exc_info()[0],'occurred, pnp.csv center x/y coordinates must be <class "int"> or <class "float">, or columns are misaligned')
    try:
        d=trans_orig[1]-(c*board_orig[1])
    except TypeError:
        print (sys.exc_info()[0],'occurred, pnp.csv center x/y coordinates must be <class "int"> or <class "float">, or columns are misaligned')

    logging.info('constants calculated for mils to pixels conversions, variables for these operations pulled from coords.csv')
    logging.info('constants:')
    logging.info('a=%s', a)
    logging.info('b=%s', b)
    logging.info('c=%s', c)
    logging.info('d=%s', d)

    #gets len and width in pixels for components
    len_wid_list=[]

    if(datafile == True):
        coord_list = list()
        max_y = corners[1] - corners[3]

        while(max_y > 0):
            coord_list = list_add(coord_list, data_set, max_y, "TopLayer")
            max_y -= 300

        max_y = corners[1] - corners[3]

        while(max_y > 0):
            coord_list = list_add(coord_list, data_set, max_y, "BottomLayer")
            max_y -= 300

        for num, sector in enumerate(coord_list):
            for n in range(len(sector)):
                if sector[0][2] == "TopLayer":
                    sorted_coor = sorted(sector)
                    coord_list[num] = sorted_coor
                    break
                else:
                    sorted_coor = sorted(sector, reverse=True)
                    coord_list[num] = sorted_coor
                    break

        x_coords = list()
        y_coords = list()
        layers = list()

        for sector in coord_list:
            for tuple in sector:
                x_coords.append(tuple[0])
                y_coords.append(tuple[1])
                layers.append(tuple[2])

        res_list = list()

        for e in range(len(x_coords)):
            for row in data_set.itertuples():
                if (x_coords[e] == row.x_values) and (y_coords[e] == row.y_values) and (layers[e] == row.Layer) and (row.Designator[0] == 'R'):
                    res_list.append(row.Designator)

        sorted_nom = list()

        for res in res_list:
            for num, des in enumerate(nom_des):
                if (res == des):
                    sorted_nom.append(nominals[num])

        seen = {}

        for index, x in enumerate(res_list):
            if x not in seen:
                seen[x] = 1
            else:
                if seen[x] == 1:
                    res_list[index] = 'DUP'
                    sorted_nom[index] = 'DUP'
                seen[x] += 1

        for elem in res_list:
            if(elem == 'DUP'):
                res_list.remove(elem)
                sorted_nom.remove(elem)

        if(res_num != len(res_list)):
            print("Number of resistors in config does not match number of resistors in output file")

        datafile_name = BaseName + "_ResistorValues.csv"

        with open(datafile_name, 'w', newline = '') as datafile:
            writer = csv.writer(datafile)
            writer.writerow(['CANDI MASTER LIST','RESVAL','V2'])
            writer.writerows([[BaseName],[]])
            writer.writerow(['Resistor', 'ZP Sheet Ref', 'Nominal', 'Lower Limit', 'Upper Limit', 'Note'])
            for i, res in enumerate(res_list):
                    writer.writerow([res, 'N/A', round(sorted_nom[i], 2), '0', round(1.01 * sorted_nom[i], 2), ''])

    for s in range(len(split_data_frame)):
        len_wid=get_len_wid(a,c,split_data_frame[s])
        len_wid_list.append(len_wid)

    logging.info('len/width values assigned to config.csv Designators in pixels')

    #list that keeps track of color values
    #color_list=['red','green','blue','yellow', 'orange']

    # Or, specify as RGB in this manner (red, green, orange, blue)

    # These are the official colors per Stacy, 5/21/19
    color_list=['#FF000080','#00FF0080','#00ffff80','#FFA50080','#FFFF0080']

    #gets coordinates in pixels for components
    pixel_coordinates_list=[]

    for u in range(len(split_data_frame)):
        pixel_coordinates=get_pixel_coor(a,b,c,d,board_coordinates_list[u],split_data_frame[u])
        pixel_coordinates_list.append(pixel_coordinates)
    logging.info('xy coordinates assigned to config.csv Designators in pixels')
    logging.info('List of pixel coordinates of config.csv Designators:')

    for h, n in enumerate(pixel_coordinates_list):
        logging.info('image#%s:',h)
        logging.info(n)

    # Keep track of sheet number
    BotSheet = 1;
    TopSheet = 1;

    # Note that irfanview is required to generate the PNG images.  The PNG images from the PIL module are not correct.
    # The path to irfanview needs to be defined in the system variables.
    # The irfanview quality for PNG should be set to 9 (maximum) in the irfanview program.

    #draws an image with rectangles drawn at spots based on data parameters
    for j, frame in enumerate(split_data_frame):
        drawn_ims=draw_mapped_image(pixel_coordinates_list[j],split_data_frame[j],len_wid_list[j],color_values[j],color_list)
        logging.info('image #%s drawn', j)

        for r in frame.itertuples():
            if (r.Index in first_values) and (r.Layer=='TopLayer'):
                top_name=r.Designator
                if drawn_ims[1]==True:
#                   top_image_name=('top%s.bmp' % top_name)
                    top_image_name=('IMAGE FILE TOP Aid %s.bmp' % TopSheet)
                    top_image_name_png=('IMAGE FILE TOP Aid %s.png' % TopSheet)
                    TopSheet +=1
                    drawn_ims[0].save(top_image_name)
                    logging.info('image:%s saved', top_image_name)

                    ReadBackIn = Image.open(top_image_name)
                    ReadBackIn.save(top_image_name_png,compress_level=1)

#                   This method relies on an external program
#                   CommandName = 'C:\Program Files (x86)\IrfanView\i_view32.exe "IMAGE FILE TOP Aid ' + str(TopSheet-1) + '.bmp" /convert="IMAGE FILE TOP Aid ' + str(TopSheet-1) + '.png"'
#                   print("Calling external command --> " + CommandName)
#                   subprocess.run(CommandName)

                    FileName  = 'IMAGE FILE TOP Aid ' + str(TopSheet-1) + '.bmp'
                    print("Removing TOP BMP File")
                    os.remove(FileName)

            if (r.Index in first_values) and (r.Layer=='BottomLayer'):
                bottom_name=r.Designator
                if drawn_ims[2]==True:
                    bottom_image_name=('IMAGE FILE BOT Aid %s.bmp' % BotSheet)
                    bottom_image_name_png=('IMAGE FILE BOT Aid %s.png' % BotSheet)
                    BotSheet += 1
                    drawn_ims[0].save(bottom_image_name)
                    logging.info('image:%s saved', bottom_image_name)

                    ReadBackIn = Image.open(bottom_image_name)
                    ReadBackIn.save(bottom_image_name_png,compress_level=1)

                    FileName = 'IMAGE FILE BOT Aid ' + str(BotSheet-1) + '.bmp'
                    print("Removing BOT BMP File")
                    os.remove(FileName)

    return None

run_main(BaseName, datafile)

input_files = [directory + "\\" + BaseName + " coord.csv", directory + "\\" + BaseName + " config.csv", directory + "\\" + BaseName + " pnp.csv", directory + "\\" + BaseName + " Top.png", directory + "\\" + BaseName + " Bottom.png"]
input_names = [BaseName + " coord.csv", BaseName + " config.csv", BaseName + " pnp.csv", BaseName + " Top.png", BaseName + " Bottom.png"]
#to add .gz compression change "w" to "w:gz" and add .gz fo filename

if(tar == True):
    with tarfile.open(BaseName + "_input_files.tar", "w") as tar:
        for index, file in enumerate(input_files):
            print(file, 'was sucessfully added to .tar file')
            tar.add(file, arcname=input_names[index])
        tar.add(directory + "\\" + "Component_Dimensions.csv", arcname="Component_Dimensions.csv")
        print(directory + "\\" + "Component_Dimensions.csv" + " was successfully added to .tar file")
        tar.close()
