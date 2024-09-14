from glob import glob
import pandas as pd
import numpy as np
import tabula   # tabula 사용 시 JAVA JDK 설치 필수
import PyPDF2
from datetime import datetime, timedelta
import pickle
from tqdm import tqdm
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET


# Dict 데이터 Pickle 저장
def save_pickle(data, path):
    with open(path,'wb') as fw:
        pickle.dump(data, fw)

def load_pickle(path):
    with open(path, 'rb') as fr:
        return pickle.load(fr)

# def detect_target_page(path):
#     process_pdf_files(base_dirs, xml_dir)
    


# PDF 파일 불러와서 DataFrame 형태로 변환
def convert_pdf_to_dict(paths, output_path):
    if not isinstance(paths, list):
            raise TypeError("파일 경로는 리스트 타입이어야 합니다.")
    
    print(f"PDF 파일 {len(paths)}개 변환 시작")
        
    columns = [
        "Hour", "Min", "#QRS's", "Min.", 
        "Ave.", "Max.", "Pauses", "V_Iso", "V_Cplt", "V_Runs", "V_Max_Run", "V_Max_Rate", 
        "S_Iso", "S_Cplt", "S_Runs", "S_Max_Run", "S_Max_Rate"
        ] 
    
    total_dict = {}
    for path in tqdm(paths):
        for page in range(1,5):
            
            try:
                _pdf = tabula.read_pdf(path, pages=page)
                if len(_pdf) > 0:
                    _pdf = _pdf[0].astype(str)
                    if not _pdf.isin(["Hourly Summary"]).any().any():
                        continue
                else:
                    continue
            except IndexError:
                break
            
            pid = _pdf.columns[0].replace(" ", "").split(":")[1]
            hourly_summary_df = _pdf.iloc[6:-1]

            # 완전한 Hourly Summary Dataframe으로 변형
            new_df = pd.DataFrame()
            for col in hourly_summary_df.columns:
                new_df = pd.concat([new_df, hourly_summary_df[col].str.split(" ", expand=True)], axis=1)
            
            # TODO : 결측값 처리 0 or NaN
            new_df.replace('---', np.nan, inplace=True)
            new_df.reset_index(drop=True, inplace=True) 
            new_df.columns = columns
            
            # NaN 값을 제외한 모든 값을 정수형으로 변환하는 함수 정의
            def convert_to_int(value):
                if pd.isna(value): return value
                else: return int(value)
            new_df = new_df.map(convert_to_int)
            
            # 제대로 변형 되었는지 검증 (HR #QRS's 비교)
            _sum_str = ' '.join(_pdf.iloc[-1].astype(str))
            _sum_list = [int(value) for value in _sum_str.split()]
            df_sum = new_df["#QRS's"].sum()
            if _sum_list[1] != df_sum:
                raise Exception(f"Dataframe이 정상적으로 변형되지 않았습니다. 데이터를 확인하세요. PID : {pid} raw_sum : {_sum_list[0]} / df_sum : {df_sum}")

            # Hourly Summary Dict로 변형
            _dict = {'HR':pd.DataFrame(), 'VT':pd.DataFrame(), 'SVT':pd.DataFrame()}
            _dict['HR'] = pd.concat([new_df.loc[:, "Hour":"Min"], new_df.loc[:, "#QRS's":"Pauses"]], axis=1)
            _dict['VT'] = pd.concat([new_df.loc[:, "Hour":"Min"],new_df.loc[:, "V_Iso":"V_Max_Rate"]], axis=1)
            _dict['VT'].columns = ["Hour", "Min", "Iso", "Cplt", "Runs", "Max_Run", "Max_Rate"]
            _dict['SVT'] = pd.concat([new_df.loc[:, "Hour":"Min"], new_df.loc[:, "S_Iso":"S_Max_Rate"]], axis=1)
            _dict['SVT'].columns = ["Hour", "Min", "Iso", "Cplt", "Runs", "Max_Run", "Max_Rate"]
            
            total_dict[pid] = _dict
            
            break
    
    
    print(f"{len(total_dict)}개의 Hourly Summary 테이블을 저장했습니다.")
    save_pickle(total_dict, f"{output_path}/hourly_summary.pickle")
    return total_dict


def plot_from_SIG(pid, signal_segment, target_dt, length=60):
    time_axis = [target_dt + timedelta(milliseconds=x) for x in np.linspace(0, 60000, num=(length*125))]
    num_channels = signal_segment.shape[1]
    
    fig, axs = plt.subplots(num_channels, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"PID : {pid}")
    for i in range(num_channels):
        axs[i].plot(time_axis, signal_segment[:, i])
        axs[i].set_title(f'Channel {i+1}')
        axs[i].set_ylabel('Amplitude')
        axs[i].grid()
    
    plt.xlabel('Time (s)')
    plt.show()
    
def get_segments_from_SIG(label_path, xml_path, sig_path, length=60):
    
    # PID 추출
    reader = PyPDF2.PdfReader(label_path)
    page = reader.pages[0]
    text_list = page.extract_text(0).split("\n")
    pid_ = text_list[1].split(": ")[1]

    # Dataframe 추출
    event_labeling_df = tabula.read_pdf(label_path, pages='all', area=(100,40,750,600))[0]
    # event_labeling_df["Date/Time"] = pd.to_datetime(event_labeling_df["Date/Time"])
    
    # PID, Hookup DateTime 추출
    root = ET.parse(xml_path).getroot()
    items = root.findall('PatientInfo')      # XML 파일 불러오기
    for item in items:
        pid = item.find('PID').text
        HookupDate = item.find('HookupDate').text
        HookupTime = item.find('HookupTime').text
    hookup_dt = datetime.strptime(f"{HookupTime} {HookupDate}", "%H:%M:%S %d-%b-%Y")
    
    if pid != pid_:
        raise TypeError("Label 파일과 xml 파일의 PID가 일치하지 않습니다.")

    record = wfdb.rdrecord(sig_path)
    
    fmt = "%H:%M:%S %d-%b-%Y"
    target_dt_list = event_labeling_df["Date/Time"].astype(str)
    signal_segment = {}
    for target_dt in tqdm(target_dt_list):
        target_dt = datetime.strptime(target_dt, fmt)
        start_time = (target_dt - hookup_dt).total_seconds()

        signal = record.p_signal
        start_index = int(start_time * 125)         # 125HZ
        end_index = int((start_time+length) * 125)

        index_dt = target_dt.strftime(fmt)
        signal_segment[index_dt] = signal[start_index:end_index]
    
    return pid, signal_segment

if __name__ == '__main__':
    # root_dir = './sample/holter_report'
    # paths = glob(f"{root_dir}/sample_*.pdf")
    # total_dict = convert_pdf_to_dict(paths, root_dir)

    root_dir = 'C:\\extract\\'
    paths = glob(f"{root_dir}*.pdf")
    total_dict = convert_pdf_to_dict(paths, root_dir)