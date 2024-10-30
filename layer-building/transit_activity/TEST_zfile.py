import zipfile
import pandas as pd

zf = r"I:\Projects\Darren\PPA3_GIS\ConveyalLayers\GTFS\datemod_versions\pct.zip"
file_in_zip = 'stops.txt'


def load_zip_item_to_df(zipdir, filename):
    # Open the zip file
    with zipfile.ZipFile(zipdir, 'r') as zip_ref:
        # Extract the file you want to read
        with zip_ref.open(filename) as file:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(file)

    return df

df = load_zip_item_to_df(zf, file_in_zip)

print(df.head())