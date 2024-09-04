import neurokit2 as nk
import pandas as pd
import numpy as np

# Load your Holter data (.txt file)
file_path = r"C:\Users\구시영\OneDrive\바탕 화면\AI연구\holter_data\child_sample\output\whole_data\155_7_73455754.txt"
data = np.loadtxt(file_path)

# Check the shape and content of the data to identify the ECG column
print("Data shape:", data.shape)
print("First few data points:", data[:10])

# Select the third channel (index 2) as the ECG signal
ecg_signal = data[:, 2]

# Check the length of the ECG signal
print("ECG signal length:", len(ecg_signal))

# Assuming the data is loaded and contains only the ECG signal, and sampling rate is known
sampling_rate = 125  # Adjust based on your data

# Calculate the number of data points in 1 hour
points_per_hour = 60 * 60 * sampling_rate
total_hours = len(ecg_signal) // points_per_hour

print("Points per hour:", points_per_hour)
print("Total hours in data:", total_hours)

# Initialize lists to store HR statistics for each hour
mean_hr = []
min_hr = []
max_hr = []

# Loop through each 1-hour segment
for i in range(total_hours):
    # Extract the 1-hour segment
    segment = ecg_signal[i * points_per_hour:(i + 1) * points_per_hour]
    
    # Check the size of the segment
    print(f"Processing hour {i+1}, segment size: {len(segment)}")
    
    # Process the segment with neurokit2
    try:
        signals, info = nk.ecg_process(segment, sampling_rate=sampling_rate)
        
        # Extract heart rate
        hr = signals['ECG_Rate']
        
        # Print the HR to verify
        print(f"Hour {i+1}: HR values = {hr}")
        
        # Calculate and store HR statistics
        if len(hr) > 0:
            mean_hr.append(np.mean(hr))
            min_hr.append(np.min(hr))
            max_hr.append(np.max(hr))
        else:
            print(f"Warning: No HR detected in hour {i+1}")
            mean_hr.append(np.nan)
            min_hr.append(np.nan)
            max_hr.append(np.nan)
    
    except Exception as e:
        print(f"Error processing hour {i+1}: {e}")
        mean_hr.append(np.nan)
        min_hr.append(np.nan)
        max_hr.append(np.nan)

# Combine the results into a DataFrame for easier analysis
results = pd.DataFrame({
    'Hour': range(1, total_hours + 1),
    'Mean_HR': mean_hr,
    'Min_HR': min_hr,
    'Max_HR': max_hr
})

# Display the results
print(results)

# Optionally save the results to a CSV file
results.to_csv('hr_statistics.csv', index=False)