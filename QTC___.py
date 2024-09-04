import neurokit2 as nk
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def load_holter_data(file_path):
    # Load the data as a numpy array
    data = np.loadtxt(file_path)
    # Convert to DataFrame with column names
    df = pd.DataFrame(data, columns=['channel_1', 'channel_2', 'channel_3'])
    return df

def calculate_qtc(ecg_signal, sampling_rate):
    # ECG 신호에서 QTc 계산
    try:
        _, rpeaks = nk.ecg_peaks(ecg_signal, sampling_rate=sampling_rate)
        _, waves = nk.ecg_delineate(ecg_signal, rpeaks, sampling_rate=sampling_rate, method="peak")
        
        q_onsets = waves['ECG_Q_Onsets']
        t_offsets = waves['ECG_T_Offsets']
        
        # QT 간격 계산
        qt_intervals = (t_offsets - q_onsets) / sampling_rate * 1000  # ms로 변환
        
        # RR 간격 계산
        rr_intervals = np.diff(rpeaks['ECG_R_Peaks']) / sampling_rate * 1000  # ms로 변환
        
        # Bazett's formula를 사용한 QTc 계산
        qtc_intervals = qt_intervals[:-1] / np.sqrt(rr_intervals / 1000)
        
        return qtc_intervals
    except Exception as e:
        print(f"QTc 계산 중 오류 발생: {e}")
        return None

# 시작
file_path = r"C:\Users\구시영\OneDrive\바탕 화면\AI연구\holter_data\child_sample\preprocssing\preprocessed_155_7_73455754.txt"
sampling_rate = 125  # Hz

# 데이터 로드
data = load_holter_data(file_path)

# 시작 시간 설정
start_time = datetime.strptime("2007-02-27 14:33:00", "%Y-%m-%d %H:%M:%S")

# 분석할 시간 범위 설정
analysis_start = datetime.strptime("2007-02-28 13:09:00", "%Y-%m-%d %H:%M:%S")
analysis_end = datetime.strptime("2007-02-28 13:10:00", "%Y-%m-%d %H:%M:%S")

# 시작 시간부터의 경과 시간 계산 (초 단위)
start_index = int((analysis_start - start_time).total_seconds() * sampling_rate)
end_index = int((analysis_end - start_time).total_seconds() * sampling_rate)

print(start_index, end_index)

# 채널별 QTc 계산
results = []
for channel in range(1, 4):  # 채널 1, 2, 3에 대해 반복
    ecg_signal = data[f'channel_{channel}'].iloc[start_index:end_index].values
    qtc_values = calculate_qtc(ecg_signal, sampling_rate)
    
    if qtc_values is not None and len(qtc_values) > 0:
        avg_qtc = np.mean(qtc_values)
        min_qtc = np.min(qtc_values)
        max_qtc = np.max(qtc_values)
    else:
        avg_qtc = min_qtc = max_qtc = "NULL"
    
    results.append({
        'Channel': channel,
        'Avg_QTc': avg_qtc,
        'Min_QTc': min_qtc,
        'Max_QTc': max_qtc
    })

results_df = pd.DataFrame(results)

# CSV 파일로 저장
results_df.to_csv('qtc_results.csv', index=False)
print("결과가 qtc_results.csv 파일로 저장되었습니다.")