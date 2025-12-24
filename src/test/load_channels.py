from load import Enabl3sDataLoader

PATH_ROOT = '../data'
SUBJECT = 'AB156'
SENSOR_CONFIG = ['TA', 'MG', 'RF', 'Ankle_Angle']

def main():
    loader = Enabl3sDataLoader(PATH_ROOT, SUBJECT)
    df_train = loader.load_dataset_batch(range(1, 6), config=SENSOR_CONFIG)
    df_train = loader.add_gait_phase_label(df_train, angle_col='Ankle_Angle', threshold=2.0)

    if not df_train.empty:
        print("\n--- Data Preview ---")
        print(df_train.head())
    else:
        print("Failed to load data.")

if __name__ == "__main__":
   main()