# Gcode Time estimator V1.0 by Hugo.B

## Future work :

- Allow the user to choose what data to store when machine state is altred.
- Generalize GCODEs and implement other CNC brands codes.
- Clean the machine code to really put the emphasis on the "state machine" logic (and externalise CSV methods)

### PLATFORM SUPPORT :
- FANUC      OK
- ISO        X
- HEIDENHEIN X

![image](https://github.com/0BAB1/gcodeEstimator/assets/62248962/c089e62d-b073-45a9-a495-fc66f3cf5ddd)

## Estimate your machinning time... Instantly !

Cost estimation on legacy CNC Code has never been easier... Woo said you need CAM software ?

## Use the power of spreadsheets to make changes directly into excel and estmate the costs !

This python script interprets a gcode file and resturns a list containing the time data and relevant infos by interpreting the G Code.

This output has been designed to be converted as a CSV file. meaning each list element is a line, containing column elements.

# DOCUMENTATION

First, import the estimation package :

```import estimation```

or if you downloaded gcodeEstimator as a package :

```from gcodeEstimator import estimation```

then use the run method to interpret you gcode :

```python
timeEstimation = estimation.run("<path to your gcode>") # returns tuple : (total_time, detailled_operations_list)
print(timeEstimation[0]) #display total time estimated
print(timeEstimation[1]) #display each operation time
```

This (the run method) returns a tuple : (totalTime, detailledTimeData). DetailedTimeData is a list giving details on every single operation so your can identify time consuming operations or see if the cutting speeds are to your liking.

To have more details on the cutting speeds you can use the "excel mode" when using the run method :

```python
timeEstimation = estimation.run("<path to your gcode>", excel_mode = True) # returns tuple : (total_time, detailled_operations_+cuttingSpeeds_list)
print(timeEstimation[0]) #display total time estimated
print(timeEstimation[1]) #display each detailled operation time
```

More details on the data structure in the sections below.

gcodeEstimator has been design with spread sheet data visualisation in mind. You can convert the output data list in csv using the makeCsv method :

```python
timeEstimation = estimation.run("<path to your gcode>", excel_mode = True)
timeEstimation = timeEstimation[1] # keep only the list of the opration details
estimation.makeCsv("<CSV destination file>", timeEstimation)
```

## Output structure 

input : the path to your gcode file

Here is how to use is and the data structure :

```python
from gcodeEstimator import estimation
#data output lis :
data = estimation.run(file_path) #run returns a tuple : (total time, output data list)
data = data[1] # use the data list 
# list stucture : [ [line1], [line2], [line3], ... ]
# line structure : lineX = [operation, tool, machinning time,  feedRate, line number in code]
```

If you want to use Excel, Librecalc or any spreadsheet softawre to lookup the data, you can use excel_mode :

```python
from gcodeEstimator import estimation
#data output lis :
data = estimation.run(file_path, excel_mode=True)[1] #run returns a list in excel mode
estimation.makeCsv("pathToYourCsvFile", data)
# list stucture : [ [line1], [line2], [line3], ... ]
# line structure : lineX = [operation, tool, diameter (tool or part in mm) ,  cutting speed Vc (m/min), rev/min, f (mm/rev), Vf(mm/min), machinnning distance (mm), time (s), line in g code]
```

## Ouput description

```python
# line structure : lineX = [operation, tool, machinning time, line number in code, feedRate]
```

- operation : The operation name as a string (example : G00, G01, G03, ...)
- tool : the tool currently in use as a string (example : T1000, T5012, ...)
- machining time : the estimated time the operation will take to execute itself in seconds as a float (example : 5, 10.12, ...)
- feed rate : the feed rate at which the opération is executed to imediatly spot the sow machining and make optimisations as a float ( example : 40, 200, 89.54, ...)
- line number in code : The line at which the opération is called in the gcode file in order to find it easily when editing huge files as an integer (exemple : 2, 75, ...)

IMPORTANT NOTE : if the time took is below 0.001 secs, it will not be in the output ! Thus making some G00 disapear.

and for Excel mode :

```python
# line structure : lineX = [operation, tool, diameter (tool or part in mm) ,  cutting speed Vc (m/min), rev/min, f (mm/rev), Vf(mm/min), machinnning distance (mm), time (s), line in g code]
```

- everything speaks for itself here
- the particularity is that some fields are "calculed" using spreadsheet syntax (like "=B1*C1"). You also have more details. This is nice to make changes directly in the spreadsheet and see the results on the time imediatly.
- Vf, rev/min and time are calculated except if cannot (example : constant rotation is used) Cf changlog V1.1 for more details
- G71,72,74,76,etc.. (special cycles) only diplay time and time is not calculated, Cf changlog V1.1 for more details
- Please note that parameters that doeas NOT HAVE AN EFFECT in the gcode programmation are set to 0 ! (example : if rev/min is constant, Vc is set to 0) Cf changlog V1.1 for more details

## Supported languages and Opérations

### Warning : This script has been developped for a Biglia mLathe using Fanuc encoder.

I made this for the needs of my compagny, meaning it might not fit yours. Designed for a lathe with Y axis, but as the Y axis was added later on, the fonctionnality might not be the best.

Feel free to read the code, understand the architecture and add you own interpreter in machines.py for your own needs and push it to this repo :)

## Supported operations : 

FANUC for Lathes (Biglia constructor):

- G0, G1 (linear interpolation and positionning *note taht G0 uses tha max speed of the machine, set by default at 12500m/min in machines.py*)
- G2, G3 (circular interpolations, using I,J,K or just R)
- G71, G72 (stock removal, facing nd turning ! **this is an estimation and might be wrong with complex profiles or syntax**)
- G74 (peck drilling)
- G76 (thead cycle **this is an estimation and might be wrong with complex profiles or syntax**)
- Y axis support
- incremental support (U,V,W)
- G28 (reset tool position to 0,0,0)
- cutting parameters => G94, G94, G99, G98 (per revolution or per minute feed) G97, G96 (constant rotation or not) G92 (max spindle speed)

## Non supported and might be added :

- G33 (thead cutting)
- G53, G54, .. (set origin) (not sure to add this one)

# Testing the code

When modifying the logic, some code samples are provided to see

Go to ./tests folder and add your test file named like this : `test_yourFileNameHere.py`

if you need to add a gcode test file, add it in ./tests/g_test_files

to test, run : `python -m pytest`

to install pytests : `pip install pytest`
