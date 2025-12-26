import os
from src.lib.data_loader import Enabl3sDataLoader

PATH_ROOT = 'data'
SUBJECT = 'AB156'
SENSOR_CONFIG = ['TA', 'MG', 'RF', 'Ankle_Angle']

def main():
    loader = Enabl3sDataLoader(PATH_ROOT, SUBJECT)
    circuits_len = len(os.listdir(os.path.join(PATH_ROOT, SUBJECT, 'Raw')))
    df_train = loader.load_dataset_batch(range(1, circuits_len + 1), config=SENSOR_CONFIG)

    if not df_train.empty:
        print("\n--- Data Preview ---")
        print(df_train.head())
    else:
        print("Failed to load data.")

if __name__ == "__main__":
   main()