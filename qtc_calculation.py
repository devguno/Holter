import os
import neurokit2 as nk
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

# 파일 경로
file_path = r"C:\Users\구시영\OneDrive\바탕 화면\AI연구\holter data\child_sample\preprocssing"

# 결과를 저장할 리스트 생성
all_results = []

# 디렉토리 내의 모든 .txt 파일에 대해 처리
for filename in os.listdir(file_path):
    if filename.endswith('.txt'):
        full_path = os.path.join(file_path, filename)
        
        try:
            # 데이터 불러오기 (가정: 텍스트 파일이 콤마로 구분된 CSV 형식)
            data = pd.read_csv(full_path, delimiter=',')  # 파일 형식에 맞게 delimiter 조정

            # 1시간 데이터 자르기 (여기서는 1초당 1000 샘플링, 3600초 = 1시간)
            one_hour_data = data.iloc[:3600000, :]  # 첫 1시간 데이터 사용, 샘플링 레이트에 맞게 조정 필요

            # ECG 신호를 채널별로 분리 (예시로 채널 1, 2, 3이 있다고 가정)
            channels = ['ECG_1', 'ECG_2', 'ECG_3']

            for channel in channels:
                ecg_signal = one_hour_data[channel].values
                
                # R peak, Q onset, T offset detection
                signals, info = nk.ecg_process(ecg_signal, sampling_rate=1000)  # 샘플링 레이트는 데이터에 맞게 조정

                r_peaks = info['ECG_R_Peaks']
                q_onsets = info['ECG_Q_Peaks']
                t_offsets = info['ECG_T_Offsets']
                
                # T peak detection
                t_peaks, _ = find_peaks(signals["ECG_T_Wave"], height=0)  # T peak 검출

                # T offset 재계산 (설명한 기울기 방법 사용)
                new_t_offsets = []
                for t_peak in t_peaks:
                    # T peak에서의 기울기 최대 지점 찾기
                    slope = np.gradient(signals["ECG_T_Wave"][t_peak:])
                    max_slope_idx = np.argmax(slope)
                    
                    # T offset 지점과 교차하는 선 계산
                    t_offset = t_peak + max_slope_idx
                    new_t_offsets.append(t_offset)
                
                # QT interval 및 RR 간격 계산
                qt_intervals = np.array(new_t_offsets) - np.array(q_onsets)
                rr_intervals = np.diff(r_peaks) / 1000  # ms 단위로 변환

                # QTc 계산 (Bazett's formula)
                qtcs = qt_intervals[:len(rr_intervals)] / np.sqrt(rr_intervals)

                # QTc 통계 (min, max, mean)
                mean_qtc = np.mean(qtcs)
                min_qtc = np.min(qtcs)
                max_qtc = np.max(qtcs)

                # 결과 리스트에 추가
                all_results.append({
                    'File': filename,
                    'Channel': f'Channel {channels.index(channel) + 1}',
                    'Average QTc (ms)': mean_qtc,
                    'Min QTc (ms)': min_qtc,
                    'Max QTc (ms)': max_qtc
                })

            print(f"파일 {filename} 처리 완료")

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

# 모든 결과를 데이터프레임으로 변환
results_df = pd.DataFrame(all_results)

# 결과 저장 경로
save_dir = r"C:\Users\구시영\OneDrive\바탕 화면\AI연구\holter data\QTc information"
os.makedirs(save_dir, exist_ok=True)

# 엑셀 파일로 저장
results_df.to_excel(os.path.join(save_dir, "QTc_results.xlsx"), index=False)

print("모든 파일의 분석이 완료되었습니다. 결과가 저장되었습니다.")