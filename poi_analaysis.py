from pydoc import describe
import arcpy
import sys
import csv

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
    valueSet = []
    try:
        # Iterate through fc and populate valueSet with unique attribute values
        with arcpy.da.SearchCursor(fc, attribute) as cursor:
            for row in cursor:
                if row[0] not in valueSet:
                    valueSet.append(row[0])
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
        
    # return list of unique attribute values
    return valueSet

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

    checkIfPolygonFeatureClass(fcPolygon)

    try:
        arcpy.management.AddField(fcPolygon,"area_sqmiles", "DOUBLE")
        arcpy.CalculateGeometryAttributes_management(fcPolygon, 
                                                [["area_sqmiles", "AREA_GEODESIC"]], 
                                                "MILES_US", 
                                                "SQUARE_MILES_US")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])

# Takes a list of summary layers containing a richness field and writes averages to a csv file
# unit is normalized_richness per square mile per fcPolygon unit
def getAverageRichness (fcPolygonList, richnessField, workspace, csvFile):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    #clear csv file of old data
    f = open(csvFile, "w")
    f.truncate()
    f.close()


    try:
        # Calculate richnessField average for each fc in fcPolygonList
        for fcPolygon in fcPolygonList:
            # Check for correct FC type
            checkIfPolygonFeatureClass(fcPolygon)
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

            #write average to csv file
            with open(csvFile, 'a', encoding='UTF8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([fcPolygon, avg])
            print(fcPolygon + " has average block richness per sq mile: " + str(avg))
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

    # Check for correct fc types
    checkIfPolygonFeatureClass(fcPolygon)
    checkIfPointFeatureClass(fcPoint)

    #Creates data layer and data table with the point count
    summaryLayer = outputName
    summaryTable = outputName + "_table"

    try:
        # Execute summarize within
        arcpy.SummarizeWithin_analysis(fcPolygon, 
        	                       fcPoint,
                                   summaryLayer, 
                                   "KEEP_ALL", 
                                   group_field = pointFieldName,
                                   out_group_table = summaryTable)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Adds new field to polygon layer. This field will be an integer and will store the amount of
        # Points with the specefied attribute values that are inside of each polygon.
        newField = "species_richness"  
        arcpy.management.AddField(summaryLayer, newField, "LONG")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Creates a dictionary where the amount of points in the polygon is mapped to the join value
        species_richness = {}
        # Iterate through summary table and count the amount of unique entries
        with arcpy.da.SearchCursor(summaryTable, ["Join_ID", "Point_Count"]) as cursor:
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
        createAreaField(summaryLayer, input_geodatabase)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Populating new point count field of input fc with the point count calculated by SummarizeWithin
        with arcpy.da.UpdateCursor(summaryLayer, ["Join_ID", newField]) as cursor:
            for row in cursor:
                if row[0] in species_richness.keys():
                    row[1] = species_richness[row[0]]
                else:
                    row[1] = 0
                cursor.updateRow(row)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        arcpy.Delete_management(summaryTable)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    


    return summaryLayer

###################################################################################################
#   This function normalizes the species_richness with area in square meters and normal richness
###################################################################################################
def calculateSpeciesRichness(fcPolygon, fcPoint, pointFieldName, outputName, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    # Check for correct fc types
    checkIfPolygonFeatureClass(fcPolygon)
    checkIfPointFeatureClass(fcPoint)

    try:
        # Creates summary layer with unique count
        summaryLayer = countUniquePointsWithinPolygon(fcPolygon, fcPoint, pointFieldName, outputName, workspace)
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])

    try:
        #Creates richness field, will be populated later
        arcpy.management.AddField(summaryLayer, "species_richness_norm", "FLOAT")
    except Exception:
        e = sys.exc_info()[1]
        print(e.args[0])
    
    try:
        # Normalizes poi richness with block area
        with arcpy.da.UpdateCursor(summaryLayer, ["species_richness_norm", "species_richness", "area_sqmiles"]) as cursor:
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

# calculateLayerRichnessByPolygon creates a new feature class for every object in containerFc.
# These new layers consist of polygons with a new richness and normalized richness field
# richness is unique point categories in polygon
# normalized richness is richness per square mile of the block

# containerFc = polygon feature class that will clip the fcPoint and fcPolygon layers. (Ex: layer of cities in a state)
# containerFcFieldName  = id to indentify objects. (Ex: city names)
# fcPolygon = polygon feature class that will have point richness calculated. (Ex: census blocks)
# fcPoint = point feature class that will be analyzed for richness. (Ex: points of interest)
# pointFieldName = attribute in point feature class that defines point type. (Ex: category)
# workspace = gdb containing all needed feature classes

def calculateLayerRichnessByPolygon (containerFc, containerFcFieldName, fcPolygon, fcPoint, pointFieldName, workspace):
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = workspace

    outputLayers = [] #list of names of the output files. Can be used for average block richness analysis
    

    with arcpy.da.SearchCursor(containerFc,[containerFcFieldName, 'SHAPE@']) as cursor:
        # Loop through rows in containerFc
        for row in cursor:
            outputName = row[0].replace(" ", "") + "_richness"
            
            # Feature classes for richness calculations
            polyClipped = "clipped_poly"
            pointsClipped = "clipped_points"
            
            try:
                # Clip fcPolygon and fcPoint by current container object
                arcpy.analysis.Clip(fcPolygon, row[1], polyClipped) 
                arcpy.analysis.Clip(fcPoint, row[1], pointsClipped) 
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
            

            try:
                # Calculate richness for clipped layers and append output name to outputLayers
                calculateSpeciesRichness(polyClipped, pointsClipped, pointFieldName, outputName, workspace)
                outputLayers.append(outputName)
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
            
            try:
                #delete clipped layers. No longer needed.
                arcpy.Delete_management(polyClipped)
                arcpy.Delete_management(pointsClipped)
            except Exception:
                e = sys.exc_info()[1]
                print(e.args[0])
    
    return outputLayers #return outputLayers for average richness calculations if needed



richness = "species_richness_norm" # Name of richness attribute in the created summary layers
containerFc = "compare_cities"
containerAttribute = "CITY_NAME"
fcPolygon = "blocks"
fcPoint = "poi"
pointFieldName = "top_category" # Field name for category in the POI data
workspace = "C:/Users/Ethan/Documents/ArcGIS/Projects/MixedUse/MixedUse.gdb"
csvFile = "averages.csv"


outputs = calculateLayerRichnessByPolygon(containerFc, containerAttribute, fcPolygon, fcPoint, pointFieldName, workspace)
getAverageRichness (outputs, richness, workspace, csvFile)

