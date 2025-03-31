from pdfreader import PDFDocument
import pymupdf4llm
import ast
import json
import openai
import time
from openai import OpenAIError
from glob import glob
from PyPDF2 import PdfReader

openai.api_key = 'sk-APIKey'

list_exception = ["SYNTHESE", "GENERALES", "Synthèse"]

def GetNumberPages(pdf_path):
    for file in glob(pdf_path):
        with open(file, 'rb') as pdf:
            doc = PDFDocument(pdf)
            return len(list(doc.pages()))

def ProcessPDF2(pdf_path):
    reader = PdfReader(pdf_path)
    number_of_pages = len(reader.pages)
    textList = []
    for i in range(number_of_pages):
      page = reader.pages[i]
      text = page.extract_text()
      textList.append(text)
    return textList


def ProcessPDFPyMu(pdf_path, pages):
    textList = []
    for i in range(pages):
      md_text_pages = pymupdf4llm.to_markdown(pdf_path, pages=[i])
      textList.append(md_text_pages)
    return textList

def get_chatgpt_response_trans(prompt):
    retry_attempts = 5
    for attempt in range(retry_attempts):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user",
                     "content": [
                         {"type": "text", "text": prompt}
                     ],
                     }
                ],
                response_format={
                    "type": "text"
                },
            )
            return response.choices[0].message['content']
        except OpenAIError as e:
            if attempt < retry_attempts - 1:
                wait_time = 2 ** attempt  # Chậm lại theo cấp số nhân
                print(f"Vượt quá giới hạn tốc độ. Đang thử lại sau {wait_time} giây...")
                time.sleep(wait_time)
            else:
                raise e

def get_chatgpt_response_trans_text(text_data, prompt):
    retry_attempts = 5
    for attempt in range(retry_attempts):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user",
                     "content": [
                         {"type": "text", "text": prompt},
                         {
                             "type": "text",
                             "text": text_data,
                         },
                     ],
                     }
                ],
                response_format={
                    "type": "text"
                },
            )
            return response.choices[0].message['content']
        except OpenAIError as e:
            if attempt < retry_attempts - 1:
                wait_time = 2 ** attempt  # Chậm lại theo cấp số nhân
                print(f"Vượt quá giới hạn tốc độ. Đang thử lại sau {wait_time} giây...")
                time.sleep(wait_time)
            else:
                raise e

def get_chatgpt_response_info(text_data, prompt):
    retry_attempts = 5
    for attempt in range(retry_attempts):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user",
                     "content": [
                         {"type": "text", "text": prompt},
                         {
                             "type": "text",
                             "text": text_data,
                         },
                     ],
                     }
                ],
                response_format={
                    "type": "json_object"
                },
            )
            return response.choices[0].message['content']
        except OpenAIError as e:
            if attempt < retry_attempts - 1:
                wait_time = 2 ** attempt  # Chậm lại theo cấp số nhân
                print(f"Vượt quá giới hạn tốc độ. Đang thử lại sau {wait_time} giây...")
                time.sleep(wait_time)
            else:
                raise e

def ProcessPDF(folder_process, uploadsFolder, filename, list_choose_pages, language, list_keywords):
    print(list_keywords)
    pdf_path = uploadsFolder + filename

    # Use LLM for translation keywords and map for filtering pages
    prompt_trans = "Please translate keywords in list " + str(list_choose_pages) + " to " + str(language) + "," \
    "At the same time, generate more synonyms or semantically similar words to each word in this list (take the first 2 results, keep the original words)." \
    "The result returns a new list in the form [..]"

    filter_pages_pymu = []
    filter_pages_pdf2 = []
    list_page_number_pymu = []
    list_page_number_pdf2 = []

    numPages = GetNumberPages(pdf_path)

    textRes_pymu = ProcessPDFPyMu(pdf_path, numPages)
    textRes_pdf2 = ProcessPDF2(pdf_path)

    # Trich xuat thong tin voi LLM

    # Filter Page
    result = get_chatgpt_response_trans(prompt_trans)
    new_result = result[result.find("["):result.find("]") + 1].replace("'", "\"")
    new_list_keywords_translate = ast.literal_eval(new_result)

    for i in range(len(textRes_pymu)):
        if any(elem in textRes_pymu[i] for elem in new_list_keywords_translate) and not any(
                elem in textRes_pymu[i] for elem in list_exception):
            filter_pages_pymu.append(textRes_pymu[i])
            list_page_number_pymu.append(str(i + 1))

    for i in range(len(textRes_pdf2)):
        if any(elem in textRes_pdf2[i] for elem in new_list_keywords_translate) and not any(
                elem in textRes_pdf2[i] for elem in list_exception):
            filter_pages_pdf2.append(textRes_pdf2[i])
            list_page_number_pdf2.append(str(i + 1))

    prompt_key_en = "Please translate keywords in list " + str(list_keywords) + " to " + str(language) + "." \
    "The result returns a new list in the form like [..]"

    result_en = get_chatgpt_response_trans(prompt_key_en)
    new_result_en = result_en[result_en.find("["):result_en.find("]") + 1].replace("'", "\"")
    new_list_keywords_translate_en = ast.literal_eval(new_result_en)

    strRes = "[{"
    for kw in new_list_keywords_translate_en:
        strRes = strRes + "\"" + str(
            kw) + "\": <The information to be extracted has the closest semantics to the keyword>"
    strRes = strRes + "}]}"

    # Extract information
    prompt = "I want to extract information from the text with the following request: " \
             "- I have a list of keywords as follows: " + str(new_list_keywords_translate_en) + \
             "- Please extract the information in json format as follows: " \
             "{'result':" + strRes + "." \
             "Requests:" \
             "1. Information with the same semantics complements each other completely. Absolutely do not combine this information, each information must be separated." \
             "2. If the information quoted is misspelled, please correct the spelling." \
             "3. Does not generate or create new information beyond the original text" \
             "4. Do not generate other json formats, each json information must have enough keywords to extract" \
             "5. The information about From, To usually are taken in the information of Inspection Direction" \
             "6. If the information is observations, the information extracted must have a meaning indicating abnormalities or problems encountered."

    prompt_text_en = "Translate the following text literally into " + str(language) + "." \
    "At the same time, rearrange the information to make it reasonable and not lose the original meaning." \
    "Do not add new information to avoid noise."

    list_res = ""
    result = "{\"result\": []}"
    json_data = json.loads(result)

    if len(filter_pages_pymu) >= len(filter_pages_pdf2):
        final_length = len(filter_pages_pymu)
    else:
        final_length = len(filter_pages_pdf2)
    for i in range(final_length):
        print("Processing..." + str(i+1) + "/" + str(len(filter_pages_pymu)))
        result_text_en = get_chatgpt_response_trans_text(filter_pages_pymu[i] + ' ' + filter_pages_pdf2[i], prompt_text_en)
        result = get_chatgpt_response_info(result_text_en, prompt)
        json_data_kq = json.loads(result)
        json_data_combine = dict(
            list(json_data.items()) + list(json_data_kq.items()) + [(k, json_data[k] + json_data_kq[k]) for k in
                                                                    set(json_data_kq) & set(json_data)])
        json_data = json_data_combine

    list_observations_trans = new_list_keywords_translate_en[0:3]
    list_general_trans = new_list_keywords_translate_en[3:]
    print(list_observations_trans)
    print(list_general_trans)
    # Grouped result
    grouped_result = {"result": []}

    # Process each item in the original data
    for item in json_data["result"]:
        # Define the key to group by
        key = tuple(item[list_general_trans[i]] for i in range(0, 2))

        # Use setdefault to find or create the appropriate group
        group = next((grp for grp in grouped_result["result"] if
                      (tuple(grp[list_general_trans[i]] for i in range(0, 2))) == key), None)

        if not group:
            group = {
                list_general_trans[i]: item[list_general_trans[i]] for i in range(0, 2)
            }
            group["Problems"] = []

            grouped_result["result"].append(group)

        # Add the current item as a problem
        problem = {
            list_observations_trans[i]: item[list_observations_trans[i]] for i in range(0, len(list_observations_trans))
        }
        for j in range(2, len(list_general_trans)):
            problem[list_general_trans[j]] = item[list_general_trans[j]]

        group["Problems"].append(problem)
    jsonFile = folder_process + '_finalInfo.json'
    with open(uploadsFolder + "\\" + jsonFile, 'w') as f:
        f.write(json.dumps(grouped_result, ensure_ascii=False, indent=4))
    return jsonFile, new_list_keywords_translate_en
