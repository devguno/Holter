import numpy as np
import matplotlib.pyplot as plt
import neurokit2 as nk
from scipy import signal
import os
import csv

def preprocess_ecg(ecg_signal, sampling_rate, amplification_factor=5):
    b, a = signal.butter(3, [0.5, 40], btype='bandpass', fs=sampling_rate)
    filtered_ecg = signal.filtfilt(b, a, ecg_signal)
    normalized_ecg = (filtered_ecg - np.mean(filtered_ecg)) / np.std(filtered_ecg)
    amplified_ecg = normalized_ecg * amplification_factor
    return amplified_ecg

def safe_peak_extraction(info, key):
    peaks = info.get(key, [])
    if isinstance(peaks, np.ndarray):
        return peaks[~np.isnan(peaks)].astype(int)
    elif isinstance(peaks, list):
        return [int(p) for p in peaks if not np.isnan(p)]
    else:
        return []

def find_q_onsets(ecg_signal, r_peaks):
    q_onsets = []
    for r_peak in r_peaks:
        search_window = min(50, r_peak)
        segment = ecg_signal[r_peak-search_window:r_peak]
        gradient = np.diff(segment)
        zero_crossings = np.where(np.diff(np.sign(gradient)))[0]
        if len(zero_crossings) > 0:
            q_onset = r_peak - search_window + zero_crossings[-1]
            q_onsets.append(q_onset)
    return np.array(q_onsets)

def find_s_peaks(ecg_signal, r_peaks):
    s_peaks = []
    for r_peak in r_peaks:
        search_window = min(50, len(ecg_signal) - r_peak)
        s_peak = r_peak + np.argmin(ecg_signal[r_peak:r_peak+search_window])
        s_peaks.append(s_peak)
    return np.array(s_peaks)

def find_t_offsets_tangent(ecg_signal, r_peaks, t_peaks):
    t_offsets = []
    for i, t_peak in enumerate(t_peaks):
        if i == len(r_peaks) - 1:  # 마지막 T-peak
            next_r_peak = len(ecg_signal) - 1
        else:
            next_r_peak = r_peaks[i+1]
        
        segment = ecg_signal[t_peak:next_r_peak]
        
        try:
            gradient = np.gradient(segment)
            max_slope_idx = np.argmin(gradient)
            slope = gradient[max_slope_idx]
            intercept = segment[max_slope_idx] - slope * max_slope_idx
            t_offset = int(t_peak + max_slope_idx - intercept / slope)
            if t_peak < t_offset < next_r_peak:
                t_offsets.append(t_offset)
        except ValueError as e:
            print(f"Warning: Could not calculate T offset for T peak at {t_peak}. Error: {e}")
            continue

    return np.array(t_offsets)

def calculate_qtc_intervals(q_onsets, toffsets, rpeaks, fs):
    qtc_intervals = []
    min_length = min(len(q_onsets), len(toffsets), len(rpeaks) - 1)
    for i in range(min_length):
        qt = (toffsets[i] - q_onsets[i]) / fs
        rr = (rpeaks[i+1] - rpeaks[i]) / fs
        qtc = qt / np.sqrt(rr)
        qtc_intervals.append(qtc * 1000)
    return np.array(qtc_intervals)

def main():
    try:
        # 파일 경로 설정
        file_path = r"C:\Users\구시영\OneDrive\바탕 화면\AI연구\holter data\child_sample\preprocssing\preprocessed_155_3_74895083.txt"
        
        # 저장할 디렉토리 설정
        save_dir = r"C:\Users\구시영\OneDrive\바탕 화면\AI연구\holter data\child_sample\annotation"
        
        # 디렉토리가 없으면 생성
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 데이터 로딩
        data = np.loadtxt(file_path)
        print(f"Original data shape: {data.shape}")

        # 채널 수 확인
        if len(data.shape) == 1:
            num_channels = 1
            data = data.reshape(-1, 1)  # 2D 배열로 변환
        else:
            num_channels = data.shape[1]
        print(f"Number of channels: {num_channels}")

        # 샘플링 레이트 설정
        fs = 125

        # 30초 데이터 선택
        data = data[:30*fs]

        print(f"Data shape after selection: {data.shape}")
        print(f"Data type: {data.dtype}")

        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        # CSV 파일을 저장할 경로 설정
        csv_path = os.path.join(save_dir, f"{base_filename}_qtc_intervals.csv")

        # CSV 파일 헤더 작성
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Channel', 'Average QTc Interval (ms)', 'Minimum QTc Interval (ms)', 'Maximum QTc Interval (ms)'])
            
            amplification_factor = 5  # 진폭 확대 factor 설정

        for i in range(num_channels):
            ecg_signal = preprocess_ecg(data[:, i], fs, amplification_factor)
            
            signals, info = nk.ecg_process(ecg_signal, sampling_rate=fs)
            
            rpeaks = safe_peak_extraction(info, 'ECG_R_Peaks')
            
            if len(rpeaks) == 0:
                print(f"No R-peaks detected in channel {i+1}. Skipping this channel.")
                continue

            q_onsets = find_q_onsets(ecg_signal, rpeaks)
            speaks = find_s_peaks(ecg_signal, rpeaks)
            tpeaks = safe_peak_extraction(info, 'ECG_T_Peaks')
            toffsets = find_t_offsets_tangent(ecg_signal, rpeaks, tpeaks)
            
            # 각 배열의 길이 확인
            print(f"Channel {i+1}:")
            print(f"  Length of rpeaks: {len(rpeaks)}")
            print(f"  Length of q_onsets: {len(q_onsets)}")
            print(f"  Length of tpeaks: {len(tpeaks)}")
            print(f"  Length of toffsets: {len(toffsets)}")


            # QTc 간격 계산
            qtc_intervals = calculate_qtc_intervals(q_onsets, toffsets, rpeaks, fs)
            
            if len(qtc_intervals) > 0:
                avg_qtc = np.mean(qtc_intervals)
                min_qtc = np.min(qtc_intervals)
                max_qtc = np.max(qtc_intervals)
                
                # QTc 간격 통계를 CSV 파일에 추가
                with open(csv_path, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([f'Channel {i+1}', avg_qtc, min_qtc, max_qtc])
            
            print(f"R-peaks found in channel {i+1}:", len(rpeaks))
            print(f"Q-onsets found in channel {i+1}:", len(q_onsets))
            print(f"S-peaks found in channel {i+1}:", len(speaks))
            print(f"T-peaks found in channel {i+1}:", len(tpeaks))
            print(f"T-offsets found in channel {i+1}:", len(toffsets))
            print(f"QTc intervals calculated in channel {i+1}:", len(qtc_intervals))
            print(f"Number of R-peaks detected: {len(rpeaks)}")
            print(f"Number of T-peaks detected: {len(tpeaks)}")
            print(f"Number of T-offsets calculated: {len(toffsets)}")
            
            # 그래프 그리기
            plt.figure(figsize=(20, 5))
            plt.plot(ecg_signal, color='#3366cc', linewidth=1)
            
            if len(rpeaks) > 0:
                plt.plot(rpeaks, ecg_signal[rpeaks], 'rx', markersize=8, label='R-peaks')
            if len(q_onsets) > 0:
                plt.plot(q_onsets, ecg_signal[q_onsets], 'mo', markersize=8, label='Q-onsets')
            if len(speaks) > 0:
                plt.plot(speaks, ecg_signal[speaks], 'go', markersize=8, label='S-peaks')
            if len(tpeaks) > 0:
                plt.plot(tpeaks, ecg_signal[tpeaks], 'b^', markersize=8, label='T-peaks')
            if len(toffsets) > 0:
                plt.plot(toffsets, ecg_signal[toffsets], 'ys', markersize=4, label='T-offsets')
            
            plt.title(f'ECG Signal with Q-onsets, R, S, T peaks and T offsets (Channel {i+1}, 30 seconds)', fontsize=16)
            plt.xlabel('Sample', fontsize=12)
            plt.ylabel('Amplitude (mV)', fontsize=12)
            plt.legend(fontsize=10)
            plt.xlim(0, 30*fs)
            
            save_path = os.path.join(save_dir, f"{base_filename}_channel_{i+1}_30sec.png")
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Image saved: {save_path}")
            
            plt.close()

        print(f"QTc interval statistics saved to: {csv_path}")

    except Exception as e:
        print(f"Error processing ECG data: {e}")
        import traceback
        traceback.print_exc()   

if __name__ == "__main__":
    main()