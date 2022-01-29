from cgitb import small
from collections import defaultdict
import shapefile
import pandas as pd
from matplotlib import pyplot as plt
from descartes import PolygonPatch
import random

df = pd.read_excel('All_Tract_Demographics.xlsx')

houston_tract_codes = set(df['TRACT'].tolist())

print('dataset loaded')

print(len(houston_tract_codes))

sf = shapefile.Reader("tl_2020_48_tract/tl_2020_48_tract.dbf")

print('shapefile loaded')

houston_tract_indices = []
tracts_data = dict()

starting_tract_codes = [231300, 320500, 340203, 554600, 430600, 453100 , 533100 , 330801, 222401, 521300, 252400]
    
n = 11

def random_color():
    return "#"+''.join([random.choice('0123456789ef') for i in range(6)])

districts = [set() for i in range(n)]
random.seed(5)
district_colors = [random_color() for i in range(n)]
adjacents = [set() for i in range(n)]
districts_data = []

def init_district(i, tract_index):
    districts[i].add(tract_index)
    my_data = tracts_data[tract_index]
    district_data = my_data.copy()
    district_data['Lat'] = float(sf.record(tract_index)[10])
    district_data['Lng'] = float(sf.record(tract_index)[11])
    districts_data.append(district_data)

for i in range(len(sf.shapes())):
    # shape = sf.shape(i)
    record = sf.record(i)
    if int(record[2]) in houston_tract_codes and int(record[1]) == 201:
        houston_tract_indices.append(i)
        tract_data = df[df['TRACT'] == int(record[2])].iloc[0]
        tracts_data[i] = tract_data
        if int(record[2]) in starting_tract_codes:
            district_number = starting_tract_codes.index(int(record[2]))
            init_district(district_number, i)
            print('initialized', starting_tract_codes[district_number])

print('houston tracts identified')

print(len(houston_tract_indices))


# for i in range(n):
#     init_district(i, houston_tract_indices[i*89 + 2])

plt.ion()

fig = plt.figure() 
ax = fig.gca()

for i in houston_tract_indices:
    poly= sf.shape(i).__geo_interface__
    ax.add_patch(PolygonPatch(poly, fc='#ffffff', ec='#000000', alpha=0.5, zorder=2 ))
    
ax.axis('scaled')


occupied = set.union(*districts)

def draw_tract(tract_index, color):
    poly= sf.shape(tract_index).__geo_interface__
    ax.add_patch(PolygonPatch(poly, fc=color, ec='#000000', alpha=0.5, zorder=2 ))

for i in range(len(districts)):
    tract_index = next(iter(districts[i]))
    draw_tract(tract_index, district_colors[i])
    fig.canvas.draw()
# input()

def find_neighbors(my_index):
    my_record = sf.record(my_index)
    nbrs = set()
    for other_index in houston_tract_indices:
        if other_index == my_index or other_index in occupied:
            continue
        other_record = sf.record(other_index)
        d_lat = abs(float(my_record[10]) - float(other_record[10]))
        if d_lat > 0.06:
            continue
        d_lng = abs(float(my_record[11]) - float(other_record[11]))
        if d_lng > 0.06:
            continue
        points_required = 2
        for point in sf.shape(my_index).points:
            if point in sf.shape(other_index).points:
                points_required -= 1
            if points_required == 0:
                nbrs.add(other_index)
                break
    return nbrs
    

for i in range(n):
    my_index = next(iter(districts[i]))
    nbrs = find_neighbors(my_index)
    for nbr in nbrs:
        adjacents[i].add(nbr)
        # draw_tract(nbr, '#aaaaaa')
    # fig.canvas.draw()

plt.show()

# print('Finished random picking. Press enter to start the districting algorithm.')
# input()

def distance(district_i, tract_j):
    data_i = districts_data[district_i]
    data_j = tracts_data[tract_j]
    record_j = sf.record(tract_j)
    d_lat = abs(data_i['Lat'] - float(record_j[10]))
    d_lng = abs(data_i['Lng'] - float(record_j[11]))
    d_hisp = abs(data_i['Hispanic Proportion'] - data_j['Hispanic Proportion'])
    d_white = abs(data_i['White Proportion'] - data_j['White Proportion'])
    d_black = abs(data_i['Black Proportion'] - data_j['Black Proportion'])
    return d_lat + d_lng + 0.1 * (d_hisp + d_white + d_black)

def combine_data(district, tract):
    data_district = districts_data[district]
    data_tract = tracts_data[tract]
    record_tract = sf.record(tract)

    district_pop = data_district['Total Population']
    tract_pop = data_tract['Total Population']

    k_old = district_pop / (district_pop + tract_pop)
    k_new = tract_pop / (district_pop + tract_pop)
    data_district['Lat'] = k_old * data_district['Lat'] + k_new * float(record_tract[10])
    data_district['Lng'] = k_old * data_district['Lng'] + k_new * float(record_tract[11])

    data_district['Total Population'] += data_tract['Total Population']

    district_hisp = data_district['Hispanic']
    tract_hisp = data_tract['Hispanic']
    data_district['Hispanic'] = district_hisp + tract_hisp
    data_district['Hispanic Proportion'] = data_district['Hispanic'] / data_district['Total Population']

    district_white = data_district['White']
    tract_white = data_tract['White']
    data_district['White'] = district_white + tract_white
    data_district['White Proportion'] = data_district['White'] / data_district['Total Population']

    district_black = data_district['Black']
    tract_black = data_tract['Black']
    data_district['Black'] = district_black + tract_black
    data_district['Black Proportion'] = data_district['Black'] / data_district['Total Population']

    return data_district

open_districts = n


while open_districts != 0:
    smallest_district = 0
    for i in range(1, n):
        if districts_data[i]['Total Population'] < districts_data[smallest_district]['Total Population']:
            smallest_district = i
    
    avail_nbrs = adjacents[smallest_district].difference(occupied)
    if len(avail_nbrs) == 0:
        print('hit the boundary')
        open_districts -= 1
        districts_data[smallest_district]['Actual Population'] = districts_data[smallest_district]['Total Population']
        districts_data[smallest_district]['Total Population'] = 10000000
        continue

    closest_nbr = next(iter(avail_nbrs))
    closest_distance = distance(smallest_district, closest_nbr)
    for nbr in avail_nbrs:
        if nbr == closest_nbr:
            continue
        if distance(smallest_district, nbr) < closest_distance:
            closest_nbr = nbr
    adjacents[smallest_district].remove(closest_nbr)
    districts[smallest_district].add(closest_nbr)
    occupied.add(closest_nbr)
    draw_tract(closest_nbr, district_colors[smallest_district])
    fig.canvas.draw()

    new_nbrs = find_neighbors(closest_nbr)
    for nbr in new_nbrs:
        if not nbr in adjacents[smallest_district]:
            adjacents[smallest_district].add(nbr)
            # draw_tract(nbr, '#ffff00')
    # fig.canvas.draw()
    # plt.pause(0.1)

    districts_data[smallest_district] = combine_data(smallest_district, closest_nbr)

print(districts_data)

distr_df = pd.DataFrame(districts_data)
distr_df.to_excel('districts.xlsx')

input()