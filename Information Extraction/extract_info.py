import time
import timeit
import json
import ast
from glob import glob
from openai import OpenAIError
from pdfreader import PDFDocument
import pymupdf4llm
import openai
from PyPDF2 import PdfReader

start_general = timeit.default_timer()
openai.api_key = 'sk-YOUR_API_KEY'

root_path = ''
filename = 'ROV-Voir-ITV _160313 Peugeot Zone 4-1_.pdf'
list_exception = ["SYNTHESE", "GENERALES", "Synthèse"]
list_choose_pages = ["PHOTO", "DISTANCE", "OBSERVATIONS"]
language = "English"
list_keywords = [
    "PHOTO", "DISTANCE", "OBSERVATIONS", 
    "From", "To", "Pipe Length", "Inspected Length", "Material"
]
list_observations = list_keywords[0:3]

print(list_observations)
list_general = list_keywords[3:]
print(list_general)

def get_number_pages(root_path, file_name):
    for file in glob(root_path + file_name):
        with open(file, 'rb') as pdf:
            doc = PDFDocument(pdf)
            return len(list(doc.pages()))

def process_pdf2(root_path, file_name):
    reader = PdfReader(root_path + file_name)
    number_of_pages = len(reader.pages)
    text_list = []
    for i in range(number_of_pages):
        page = reader.pages[i]
        text = page.extract_text()
        text_list.append(text)
    return text_list

def process_pdf_pymu(root_path, file_name, pages):
    pdf_path = root_path + file_name
    text_list = []
    for i in range(pages):
        md_text_pages = pymupdf4llm.to_markdown(pdf_path, pages=[i])
        text_list.append(md_text_pages)
    return text_list

def get_chatgpt_response_trans(prompt):
    retry_attempts = 5
    for attempt in range(retry_attempts):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user", 
                        "content": [{"type": "text", "text": prompt}]
                    }
                ],
                response_format={"type": "text"},
            )
            return response.choices[0].message['content']
        except OpenAIError as e:
            if attempt < retry_attempts - 1:
                wait_time = 2 ** attempt
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
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
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "text", "text": text_data}
                        ]
                    }
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message['content']
        except OpenAIError as e:
            if attempt < retry_attempts - 1:
                wait_time = 2 ** attempt
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise e

# Use LLM for translation keywords and map for filtering pages
prompt_trans = (
    "Hãy dịch các từ khóa trong danh sách " + str(list_choose_pages) + 
    " sang tiếng " + str(language) + ", đồng thời sinh ra thêm các từ đồng nghĩa "
    "hoặc gần giống với các từ trong danh sách này (lấy 2 kết quả đầu tiên, "
    "giữ lại các từ gốc). Kết quả trả về dạng danh sách các từ khóa mới ở dạng [...]"
)
filter_pages_pymu = []
filter_pages_pdf2 = []
list_page_number_pymu = []
list_page_number_pdf2 = []

num_pages = get_number_pages(root_path, filename)

startIt_pymu = timeit.default_timer()
text_res_pymu = process_pdf_pymu(root_path, filename, num_pages)
stop_pymu = timeit.default_timer()
print('Time PyMuPDF: ', stop_pymu - startIt_pymu)

startIt_pdf2 = timeit.default_timer()
text_res_pdf2 = process_pdf2(root_path, filename)
stop_pdf2 = timeit.default_timer()
print('Time PyPDF2: ', stop_pdf2 - startIt_pdf2)

# Extract information with LLM
startIt_LLM = timeit.default_timer()
result = get_chatgpt_response_trans(prompt_trans)
print(result)
new_result = result[result.find("["):result.find("]")+1].replace("'", "\"")
print(new_result)
new_list_keywords_translate = ast.literal_eval(new_result)
print(new_list_keywords_translate)

for i in range(len(text_res_pymu)):
    if (any(elem in text_res_pymu[i] for elem in new_list_keywords_translate) and 
            not any(elem in text_res_pymu[i] for elem in list_exception)):
        filter_pages_pymu.append(text_res_pymu[i])
        list_page_number_pymu.append(str(i+1))

for i in range(len(text_res_pdf2)):
    if (any(elem in text_res_pdf2[i] for elem in new_list_keywords_translate) and 
            not any(elem in text_res_pdf2[i] for elem in list_exception)):
        filter_pages_pdf2.append(text_res_pdf2[i])
        list_page_number_pdf2.append(str(i+1))

print(len(filter_pages_pymu))
print(list_page_number_pymu)
print(len(filter_pages_pdf2))
print(list_page_number_pdf2)

strRes = "[{"
for kw in list_keywords:
    strRes += "\"" + str(kw) + "\": <Thông tin cần trích có ngữ nghĩa gần nhất với từ khóa>"
strRes += "}]"

prompt = (
    "Tôi muốn trích thông tin từ đoạn văn bản với yêu cầu sau: "
    "- Tôi có một danh sách các từ khóa như sau: " + str(list_keywords) + 
    ". Hãy dịch danh sách từ khóa cùng đoạn văn bản sang tiếng Anh "
    "- Hãy thực hiện trích xuất thông tin theo định dạng json như sau: "
    "{'result':" + strRes + ". Yêu cầu: "
    "1. Thông tin trích ra phải giữ nguyên ngôn ngữ ban đầu trước khi dịch. "
    "2. Các thông tin có ngữ nghĩa như nhau thì bổ sung cho nhau đầy đủ, "
    "tuyệt đối không được gộp các thông tin này lại, phải tách riêng từng thông tin ra "
    "3. Nếu thông tin trích ra sai chính tả thì hãy sửa lỗi chính tả lại cho đúng "
    "4. Không tự sinh ra hay sáng tạo thêm thông tin mới ngoại trừ đoạn văn bản ban đầu "
    "5. Không tự sinh ra định dạng json khác, mỗi thông tin json phải đủ các từ khóa cần trích xuất "
    "6. Thông tin từ điểm ... đến điểm ... thì lấy theo hướng khảo sát, không theo hướng dòng chảy"
)

list_res = ""
result = "{\"result\": []}"
json_data = json.loads(result)

for i in range(len(filter_pages_pymu)):
    print("Call lần thứ: " + str(i + 1))
    result = get_chatgpt_response_info(filter_pages_pymu[i] + " " + filter_pages_pdf2[i], prompt)
    json_data_kq = json.loads(result)
    json_data_combine = dict(
        list(json_data.items()) + list(json_data_kq.items()) + 
        [(k, json_data[k] + json_data_kq[k]) for k in set(json_data_kq) & set(json_data)]
    )
    json_data = json_data_combine

stop_LLM = timeit.default_timer()
print('Time LLM: ', stop_LLM - startIt_LLM)
print(json_data)

list_filter = []
for js in json_data['result']:
    flag = 1
    for key in list_keywords:
        if key not in js:
            flag = -1
            break
    if flag == 1:
        list_filter.append(js)

json_data_new = {'result': list_filter}
print(json_data_new)
print(len(json_data_new['result']))

# Grouped result
grouped_result = {"result": []}

for item in json_data_new["result"]:
    key = tuple(item[list_general[i]] for i in range(len(list_general)))
    group = next(
        (grp for grp in grouped_result["result"] 
         if (tuple(grp[list_general[i]] for i in range(len(list_general))) == key)
        ),
        None
    )
    if not group:
        group = {list_general[i]: item[list_general[i]] for i in range(len(list_general))}
        group["Problems"] = []
        grouped_result["result"].append(group)

    problem = {list_observations[i]: item[list_observations[i]] for i in range(len(list_observations))}
    group["Problems"].append(problem)

print(grouped_result)

json_file = 'finalJSON.json'
with open(json_file, 'w') as f:
    f.write(json.dumps(grouped_result, ensure_ascii=False, indent=4))

stop_general = timeit.default_timer()
print('Time General: ', stop_general - start_general)