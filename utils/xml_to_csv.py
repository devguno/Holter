from glob import glob
import xml.etree.ElementTree as ET
import csv

def preprocessing_tag_list(tag_list):
    for i, tag in enumerate(tag_list):
        if 'HolterReport_' in tag :
            tag_list[i] = tag.replace('HolterReport_', '')
            
        if 'PatientInfo_' in tag:
            tag_list[i] = tag.replace('PatientInfo_', '')
        elif 'General_' in tag:
            tag_list[i] = tag.replace('General_', '')
        elif 'HeartRates_' in tag:
            tag_list[i] = tag.replace('HeartRates_', 'HR_')
        elif 'Ventriculars_' in tag:
            tag_list[i] = tag.replace('Ventriculars_', 'VT_')
        elif 'Supraventriculars' in tag:
            tag_list[i] = tag.replace('Supraventriculars_', 'SVT_')
            
    tag_list.pop(0)
    tag_list.remove('PatientInfo')
    tag_list.remove('General')
    tag_list.remove('HeartRates')
    tag_list.remove('Ventriculars')
    tag_list.remove('Supraventriculars')
    tag_list.extend(['SIG_file_path', 'hea_file_path'])
    return tag_list


def xml_to_csv(xml_paths):
    if not isinstance(xml_paths, list):
        raise TypeError("파일 경로는 리스트 타입이어야 합니다.")
    
    def read_all_elements(row, tag_list, element, parent_tag=''):
        _text = element.text.strip() if element.text else None
        cur_tag = f"{parent_tag}_{element.tag}" if parent_tag else element.tag
        tag_list.append(cur_tag)
        if _text != '':
            row.append(_text)
        for child in element:
            if cur_tag == 'HolterReport':
                cur_tag = ''
            read_all_elements(row, tag_list, child, cur_tag)
        
        return tag_list, row

    elements_list = []
    for xml_path in xml_paths:
        root = ET.parse(xml_path).getroot()
        row, tag_list = [], []
        tag_list, row = read_all_elements(row, tag_list, root)
        
        # TODO : SIG & hea file link
        sig_path = ""
        hea_path = ""
        row.extend([sig_path, hea_path])
        
        elements_list.append(row)
    
    tag_list = preprocessing_tag_list(tag_list)
    
    return tag_list, elements_list