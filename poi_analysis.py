from pydoc import describe
import arcpy
import sys

# Ethan Traugh
# 4-13-2022

# this function returns a unique list of all the attribute values
# fc is a feature class
# attribute must be the exact name of a field in the feature class
# workspace 
def listValues(fc, attribute, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    value_set = []

    with arcpy.da.SearchCursor(fc, attribute) as cursor:
        for row in cursor:
            if row[0] not in value_set:
                value_set.append(row[0])

    return value_set


def createAreaField(fcPolygon, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    arcpy.management.AddField(fcPolygon,"area_meters", "DOUBLE")
    arcpy.CalculateGeometryAttributes_management(fcPolygon, 
                                                [["area_meters", "AREA_GEODESIC"]], 
                                                "METERS", 
                                                "SQUARE_METERS")



#create a function that counts the amount of points in a polygon

# Creates a new layer with unique species count
##################################################################################################
##################################################################################################
##################################################################################################
def countUniquePointsWithinPolygon(fcPolygon, fcPoint, pointFieldName, input_geodatabase):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = input_geodatabase


    #Creates data layer and data table with the point count
    summary_layer = "summary_layer"
    summary_table = "summary_table"
    arcpy.SummarizeWithin_analysis(fcPolygon, 
        	                       fcPoint,
                                   summary_layer, 
                                   "KEEP_ALL", 
                                   group_field = pointFieldName,
                                   out_group_table = summary_table)

    # Adds new field to polygon layer. This field will be an integer and will store the amount of
    # Points with the specefied attribute values that are inside of each polygon.
    newField = "species_richness"  
    arcpy.management.AddField(summary_layer, newField, "LONG")
    
    # Creates a dictionary where the amount of points in the polygon is mapped to the join value
    
    species_richness = {}
    print("entering summary table cursor")
    fields = arcpy.ListFields(summary_table)
    for field in fields:
        print(field)
    with arcpy.da.SearchCursor(summary_table, ["Join_ID", "Point_Count"]) as cursor:
        for row in cursor:
            if row[0] in species_richness.keys():
                species_richness[row[0]] += 1
            else:
                species_richness[row[0]] = 1
    # Create area field
    createAreaField(summary_layer, input_geodatabase)

    # Populating new point count field of input fc with the point count calculated by SummarizeWithin
    print("entering summary layer cursor")
    with arcpy.da.UpdateCursor(summary_layer, ["Join_ID", newField]) as cursor:
        for row in cursor:
            if row[0] in species_richness.keys():
                row[1] = species_richness[row[0]]
            else:
                row[1] = 0
            cursor.updateRow(row)

    return summary_layer

###################################################################################################
#   This function normalizes the species_richness with area in square meters and normal richness
###################################################################################################
def calculateSpeciesRichness(fcPolygon, fcPoint, pointFieldName, workspace):
    
    summary_layer = countUniquePointsWithinPolygon(fcPolygon, fcPoint, pointFieldName, workspace) # Creates summary layer with unique count

    arcpy.management.AddField(summary_layer, "species_richness_norm", "FLOAT") #Creates richness field, will be populated later

    with arcpy.da.UpdateCursor(summary_layer, ["species_richness_norm", "species_richness", "area_meters"]) as cursor:
        for row in cursor:
            row[0] = row[1]/row[2]
            cursor.updateRow(row)

###################################################################################################
###################################################################################################
###################################################################################################



points = "poi_iowa_city"
blocks = "blocks"
attribute = "top_category"
workspace = "C:/Users/Ethan/Documents/ArcGIS/Projects/IowaCityPOI/IowaCityPOI.gdb"

#print("amount of categories p\resent in POI data is: " + str(len(listValues(points, attribute, workspace))))
#print("amount of categories present in POI data is: " + str(len(listValues(points, "sub_category", workspace))))

# calculateSpeciesRichness(blocks, points, attribute, workspace)
# Create a function that takes a polygon, point, attribute name, and attribute value
# and counts the am

#create a function that counts the amount of points in a buffer

#create a function that counts the amount of unique points in a buffer