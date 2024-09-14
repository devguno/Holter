import os
import re
import fitz  # PyMuPDF
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from tqdm import tqdm

def extract_match(pattern, text, default="Unknown"):
    match = re.search(pattern, text)
    return match.group(1) if match else default

def extract_grouped_matches(pattern, text, groups, default="Unknown"):
    match = re.search(pattern, text)
    if match:
        return [match.group(i + 1) for i in range(groups)]
    return [default] * groups

def parse_general_section(text):
    general_section = re.search(r"General\n(.+?)Heart Rates", text, re.DOTALL)
    if general_section:
        general_text = general_section.group(1)
        qrs_complexes = extract_match(r"(\d+) QRS complexes", general_text)
        ventricular_beats = extract_match(r"(\d+) Ventricular beats", general_text)
        supraventricular_beats = extract_match(r"(\d+) Supraventricular beats", general_text)
        noise_percentage = extract_match(r"(<\s*\d+|\d+) % of total time classified as noise", general_text, "0")
        paced_beats = extract_match(r"(\d+) Paced beats", general_text)
        af_afl_percentage = extract_match(r"(<\s*\d+|\d+) % of total time in AF/AFL", general_text)
        bb_beats = extract_match(r"(\d+) BB beats", general_text)
        junctional_beats = extract_match(r"(\d+) Junctional beats", general_text)
        aberrant_beats = extract_match(r"(\d+) Aberrant beats", general_text)
    else:
        qrs_complexes = ventricular_beats = supraventricular_beats = noise_percentage = "Unknown"
        paced_beats = af_afl_percentage = bb_beats = junctional_beats = aberrant_beats = "Unknown"
    return {
        'QRScomplexes': qrs_complexes,
        'VentricularBeats': ventricular_beats,
        'SupraventricularBeats': supraventricular_beats,
        'NoisePercentage': noise_percentage,
        'PacedBeats': paced_beats,
        'AFAFLPercentage': af_afl_percentage,
        'BBBeats': bb_beats,
        'JunctionalBeats': junctional_beats,
        'AberrantBeats': aberrant_beats
    }

def parse_heart_rates_section(text):
    heart_rates_data = {}
    patterns = [
        (r"(\d+) Minimum at ([\d:]+ \d+-\w+)", 'MinimumRate', 'Timestamp'),
        (r"(\d+) Average", 'AverageRate', None),
        (r"(\d+) Maximum at ([\d:]+ \d+-\w+)", 'MaximumRate', 'Timestamp'),
        (r"(\d+)\s*Beats in tachycardia \(>=?\d+\s*bpm\),\s*(\d+)% total", 'TachycardiaBeats', 'TachycardiaPercentage'),
        (r"(\d+)\s*Beats in bradycardia \(<=?\d+\s*bpm\),\s*(\d+)% total", 'BradycardiaBeats', 'BradycardiaPercentage')
    ]
    for pattern, main_tag, sub_tag in patterns:
        match = re.search(pattern, text)
        if match:
            heart_rates_data[main_tag] = (match.group(1), match.group(2) if sub_tag else None)
        else:
            heart_rates_data[main_tag] = ("Unknown", "Unknown" if sub_tag else None)
    return heart_rates_data

def parse_section(section_text, patterns):
    section_data = {}
    for pattern, tags in patterns:
        matches = extract_grouped_matches(pattern, section_text, len(tags))
        for tag_index, tag in enumerate(tags):
            section_data[tag] = matches[tag_index]
    return section_data

def create_xml(patient_info, general_data, heart_rates_data, ventriculars_data, supraventriculars_data, xml_path):
    root = Element('HolterReport')
    patient_info_element = SubElement(root, 'PatientInfo')
    for key, value in patient_info.items():
        SubElement(patient_info_element, key).text = value

    general_element = SubElement(root, 'General')
    for key, value in general_data.items():
        SubElement(general_element, key).text = value

    heart_rates_element = SubElement(root, 'HeartRates')
    for key, (value, sub_value) in heart_rates_data.items():
        element = SubElement(heart_rates_element, key)
        if sub_value:
            SubElement(element, 'Timestamp').text = sub_value
        element.text = value

    ventriculars_element = SubElement(root, 'Ventriculars')
    for key, value in ventriculars_data.items():
        SubElement(ventriculars_element, key).text = value

    supraventriculars_element = SubElement(root, 'Supraventriculars')
    for key, value in supraventriculars_data.items():
        SubElement(supraventriculars_element, key).text = value

    xml_str = tostring(root, 'utf-8')
    parsed_str = parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="   ")

    with open(xml_path, "w") as xml_file:
        xml_file.write(pretty_xml_str)

def process_pdf_files(file_dirs, xml_dir):
    pdf_files = []
    for file_dir in file_dirs:
        for root, _, files in os.walk(file_dir):
            for file in files:
                if file.endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    
    failed_files = []

    for pdf_path in tqdm(pdf_files, desc="Processing PDF Files"):
        try:
            filename = os.path.basename(pdf_path)
            pdf_doc = fitz.open(pdf_path)
            page = pdf_doc.load_page(0)
            extracted_text = page.get_text()

            patient_info = {
                'PID': extract_match(r"Patient Name:?\n(\d+)\nID:?", extracted_text, filename.split('_')[-1].replace('.pdf', '')),
                'HookupDate': extract_match(r"Medications:?\n(\d+-\w+-\d+)\nHookup Date:?", extracted_text, "Unknown"),
                'HookupTime': extract_match(r"Hookup Date:?\n(\d+:\d+:\d+)\nHookup Time:?", extracted_text, "Unknown"),
                'Duration': extract_match(r"Hookup Time:?\n(\d+:\d+:\d+)\nDuration:?", extracted_text, "Unknown"),
                'Age': extract_match(r"(\d+)\s*yr\s*Age:", extracted_text, "Unknown"),
                'Gender': extract_match(r"(Male|Female)\s*Gender:", extracted_text, "Unknown")
            }

            general_data = parse_general_section(extracted_text)

            heart_rates_data = parse_heart_rates_section(extracted_text)

            ventriculars_section = extract_match(r"Ventriculars \(V, F, E, I\)\n([\s\S]+?)\nSupraventriculars \(S, J, A\)", extracted_text, "")
            supraventriculars_section = extract_match(r"Supraventriculars \(S, J, A\)\n([\s\S]+?)Interpretation", extracted_text, "")

            ventriculars_patterns = [
                (r"(\d+) Isolated", ['Isolated']),
                (r"(\d+) Couplets", ['Couplets']),
                (r"(\d+) Bigeminal cycles", ['BigeminalCycles']),
                (r"(\d+) Runs totaling (\d+) beats", ['Runs', 'TotalBeats']),
                (r"(\d+) Beats longest run (\d+) bpm ([\d:]+ \d+-\w+)", ['LongestRunBeats', 'LongestRunBPM', 'LongestRunTimestamp']),
                (r"(\d+) Beats fastest run (\d+) bpm ([\d:]+ \d+-\w+)", ['FastestRunBeats', 'FastestRunBPM', 'FastestRunTimestamp'])
            ]

            supraventriculars_patterns = [
                (r"(\d+) Isolated", ['Isolated']),
                (r"(\d+) Couplets", ['Couplets']),
                (r"(\d+) Bigeminal cycles", ['BigeminalCycles']),
                (r"(\d+) Runs totaling (\d+) beats", ['Runs', 'TotalBeats']),
                (r"(\d+) Beats longest run (\d+) bpm ([\d:]+ \d+-\w+)", ['LongestRunBeats', 'LongestRunBPM', 'LongestRunTimestamp']),
                (r"(\d+) Beats fastest run (\d+) bpm ([\d:]+ \d+-\w+)", ['FastestRunBeats', 'FastestRunBPM', 'FastestRunTimestamp'])
            ]

            ventriculars_data = parse_section(ventriculars_section, ventriculars_patterns)
            supraventriculars_data = parse_section(supraventriculars_section, supraventriculars_patterns)

            xml_path = os.path.join(xml_dir, os.path.splitext(filename)[0] + '.xml')
            create_xml(patient_info, general_data, heart_rates_data, ventriculars_data, supraventriculars_data, xml_path)

            print(f"Processed {filename}, Saved XML file: {xml_path}")

        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            failed_files.append(filename)

    return failed_files

def main():
    base_dirs = [
        'D:\\extract'
    ]
    xml_dir = 'E:\\xml'

    if not os.path.exists(xml_dir):
        os.makedirs(xml_dir)

    print("Starting to process PDF files...")
    failed_files_record = process_pdf_files(base_dirs, xml_dir)

    if failed_files_record:
        print("\nFailed to process the following files:")
        for failed_file in failed_files_record:
            print(failed_file)
    else:
        print("\nAll PDF files processed successfully.")

    print("Completed processing all files.")

if __name__ == "__main__":
    main()
