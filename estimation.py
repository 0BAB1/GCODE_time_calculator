try :
    from timeEstimator.machines import FanucLathe
except ModuleNotFoundError or ImportError:
    from .timeEstimator.machines import FanucLathe
import os

def run(file_path : str, excel_mode= False) -> (float,list):
    """simulate the given file, returns total time and csv data a table that i can turn into csv later on"""
    lathe = FanucLathe()
    i = 0

    with open(file_path, "r") as file:
        for line in file:
            i+=1
            #get data from the line to insert into a csv file
            try:
                lathe.interpret(line, excel_mode=excel_mode)
            except Exception as e:
                #error handling
                raise e
            
        lathe.save_csv_data(excel_mode=excel_mode) #last csv Data save to put the last cached data into to lathe.csvData variable
        
    return (round(lathe.globalTime,2), lathe.csvData)

def makeCsv(filepath : str, data : list = []) -> None:
    """creates a csv from array of line (csvData from a machine for example)"""
    print(data[0])
    with open(filepath, "w+") as csvFile:
        for line in data[1]:
            for element in line:
                csvFile.write(str(element).replace(".", ",") + ";")
            csvFile.write("\n")