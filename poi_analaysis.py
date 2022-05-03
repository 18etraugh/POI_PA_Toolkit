from pydoc import describe
import arcpy
import sys

# Ethan Traugh
# 5-2-2022

# This module's function is to calculate the richness of points in a polygon feature class and give descriptive
# information about the new layers as well as the existing layers

################################################################################
################################################################################
################################################################################
# HELPER FUNCTIONS
################################################################################
################################################################################
################################################################################

# this function returns a unique list of all the attribute values
# fc is a feature class
# attribute must be the exact name of a field in the feature class
# workspace 
def listValues(fc, attribute, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    # Will contain all unique attribute values
    value_set = []
    try:
        # Iterate through fc and populate value_set with unique attribute values
        with arcpy.da.SearchCursor(fc, attribute) as cursor:
            for row in cursor:
                if row[0] not in value_set:
                    value_set.append(row[0])
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
        
    # return list of unique attribute values
    return value_set

# Determines whether given feature class is a Point feature class
def checkIfPointFeatureClass(fcPoint):
    if arcpy.Describe(fcPoint).shapeType !=  "Point":
        print(fcPoint + " is not a Point feature class.")
        exit()
# Determines whether given feature class is a Polygon feature class
def checkIfPolygonFeatureClass(fcPolygon):
    if arcpy.Describe(fcPolygon).shapeType !=  "Polygon":
        print(fcPolygon + " is not a Polygon feature class.")
        exit()
# Determines whether given feature class is a Polyline feature class
def checkIfPolylineFeatureClass(fcPolyline):
    if arcpy.Describe(fcPolyline).shapeType != "Polyline":
        print(fcPolyline + " is not a Polyline feature class.")

# This function takes a polygon feature class and creates an area field in square miles
def createAreaField(fcPolygon, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    try:
        arcpy.management.AddField(fcPolygon,"area_sqmiles", "DOUBLE")
        arcpy.CalculateGeometryAttributes_management(fcPolygon, 
                                                [["area_sqmiles", "AREA_GEODESIC"]], 
                                                "MILES_US", 
                                                "SQUARE_MILES_US")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])

# Takes a list of summary layers containing a richness field and prints average block richness for each fc
def getAverageRichness (fcPolygonList, richnessField, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    try:
        # Calculate richnessField average for each fc in fcPolygonList
        for fcPolygon in fcPolygonList:
            richnessValues = [] # Will contain all richnes values from current fc
            # Append richness values to list
            with arcpy.da.SearchCursor(fcPolygon, richnessField) as cursor:
                for row in cursor:
                    richnessValues.append(float(row[0]))
            # Sum all richness values
            richnessSum = 0
            for value in richnessValues:
                richnessSum += value
            # Calculate average
            avg = richnessSum/len(richnessValues)
            # Print average to console
            print("Feature class: " + fcPolygon + " has mean block normalized poi richness " + str(avg))
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    

##################################################################################################
##################################################################################################
##################################################################################################
##################################################################################################
##################################################################################################
##################################################################################################



##################################################################################################
# Creates a new layer with unique species count and returns it
##################################################################################################
def countUniquePointsWithinPolygon(fcPolygon, fcPoint, pointFieldName, outputName, input_geodatabase):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = input_geodatabase


    #Creates data layer and data table with the point count
    summary_layer = outputName
    summary_table = outputName + "_table"

    try:
        # Execute summarize within
        arcpy.SummarizeWithin_analysis(fcPolygon, 
        	                       fcPoint,
                                   summary_layer, 
                                   "KEEP_ALL", 
                                   group_field = pointFieldName,
                                   out_group_table = summary_table)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Adds new field to polygon layer. This field will be an integer and will store the amount of
        # Points with the specefied attribute values that are inside of each polygon.
        newField = "species_richness"  
        arcpy.management.AddField(summary_layer, newField, "LONG")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Creates a dictionary where the amount of points in the polygon is mapped to the join value
        species_richness = {}
        # Iterate through summary table and count the amount of unique entries
        with arcpy.da.SearchCursor(summary_table, ["Join_ID", "Point_Count"]) as cursor:
            for row in cursor:
                if row[0] in species_richness.keys():
                    species_richness[row[0]] += 1
                else:
                    species_richness[row[0]] = 1
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Create area field
        createAreaField(summary_layer, input_geodatabase)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Populating new point count field of input fc with the point count calculated by SummarizeWithin
        with arcpy.da.UpdateCursor(summary_layer, ["Join_ID", newField]) as cursor:
            for row in cursor:
                if row[0] in species_richness.keys():
                    row[1] = species_richness[row[0]]
                else:
                    row[1] = 0
                cursor.updateRow(row)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    return summary_layer

###################################################################################################
#   This function normalizes the species_richness with area in square meters and normal richness
###################################################################################################
def calculateSpeciesRichness(fcPolygon, fcPoint, pointFieldName, outputName, workspace):
    try:
        # Creates summary layer with unique count
        summary_layer = countUniquePointsWithinPolygon(fcPolygon, fcPoint, pointFieldName, outputName, workspace)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])

    try:
        #Creates richness field, will be populated later
        arcpy.management.AddField(summary_layer, "species_richness_norm", "FLOAT")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Normalizes poi richness with block area
        with arcpy.da.UpdateCursor(summary_layer, ["species_richness_norm", "species_richness", "area_sqmiles"]) as cursor:
            for row in cursor:
                row[0] = row[1]/row[2]
                cursor.updateRow(row)
        print(outputName + " has been created")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])

###################################################################################################
###################################################################################################
###################################################################################################


# Iowa City Feature Classes
icPoints = "poi_iowa_city"
icBlocks = "blocks_iowa_city"
# Cedar Rapids Feature Classes
crPoints = "poi_cedar_rapids"
crBlocks = "blocks_cedar_rapids"
# Davenport Feature Classes
davenportPoints = "poi_davenport"
davenportBlocks = "blocks_davenport"


richness = "species_richness_norm" # Name of richness attribute in the created summary layers
attribute = "top_category" # Field name for category in the POI data
workspace = "C:/Users/Ethan/Documents/ArcGIS/Projects/MixedUse/MixedUse.gdb"

# Create new block layers with richness field
calculateSpeciesRichness(icBlocks,icPoints, attribute, "IC_MIXED_USE", workspace)
calculateSpeciesRichness(davenportBlocks, davenportPoints, attribute, "DP_MIXED_USE", workspace)
calculateSpeciesRichness(crBlocks, crPoints, attribute, "CR_MIXED_USE", workspace)

# Find Average 
getAverageRichness(["IC_MIXED_USE","DP_MIXED_USE", "CR_MIXED_USE"], richness, workspace)