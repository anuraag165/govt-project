import streamlit as st
import base64
import json
import mysql.connector
import re

# --- Streamlit Setup ---
st.set_page_config("📜 Emigration Government Records Scanner", layout="wide")
st.title("📜 Government Emigration Record Scanner")

# --- MySQL DB Setup ---
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Update as needed
    database="emigration_db"
)
my_cursor = mydb.cursor()

def insert_to_db(data, image_bytes):
    query = '''
    INSERT INTO emigration_data (
        SHIP_NAME, SHIP_NO, EMIGRATION_DATE, DEPOT_NO,
        NAME, SEX, CASTE, FATHER_NAME, AGE,
        ZILLAH, PERGUNNAH, VILLAGE, OCCUPATION,
        NEXT_OF_KIN, KIN_VILLAGE, MARKS, IMAGE
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    values = list(data.values()) + [base64.b64encode(image_bytes)]
    my_cursor.execute(query, values)
    mydb.commit()

def ask_gpt4_vision(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    prompt = """
You are an AI that extracts data from historical Fiji emigration forms.
Return JSON with the following fields:

SHIP_NAME, SHIP_NO, EMIGRATION_DATE, DEPOT_NO,
NAME, SEX, CASTE, FATHER_NAME, AGE,
ZILLAH, PERGUNNAH, VILLAGE, OCCUPATION,
NEXT_OF_KIN, KIN_VILLAGE, MARKS
"""

    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are an AI that extracts data from scanned documents."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }}
            ]}
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else "{}"

# --- File Upload ---
uploaded_file = st.file_uploader("📤 Upload scanned emigration form", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image_bytes = uploaded_file.read()
    st.session_state["image_bytes"] = image_bytes  # persist image
    st.image(image_bytes, caption="📄 Uploaded Document", use_column_width=True)

    if st.button("🔍 Extract with GPT-4 Vision"):
        with st.spinner("Extracting fields with GPT-4..."):
            try:
                gpt_response = ask_gpt4_vision(image_bytes)
                cleaned_json = extract_json(gpt_response)
                parsed = json.loads(cleaned_json)
                st.session_state["parsed_data"] = parsed  # persist fields
            except Exception as e:
                st.error(f"❌ GPT-4 Error: {e}")

# --- Form Display ---
if "parsed_data" in st.session_state:
    parsed = st.session_state["parsed_data"]
    st.subheader("🧾 Review & Confirm Extracted Fields")

    with st.form("confirm_form"):
        col1, col2 = st.columns(2)
        with col1:
            parsed["SHIP_NAME"] = st.text_input("Ship Name", parsed.get("SHIP_NAME", ""))
            parsed["SHIP_NO"] = st.text_input("Ship No", parsed.get("SHIP_NO", ""))
            parsed["EMIGRATION_DATE"] = st.text_input("Emigration Date", parsed.get("EMIGRATION_DATE", ""))
            parsed["DEPOT_NO"] = st.text_input("Depot No", parsed.get("DEPOT_NO", ""))
            parsed["NAME"] = st.text_input("Name", parsed.get("NAME", ""))
            parsed["SEX"] = st.text_input("Sex", parsed.get("SEX", ""))
            parsed["CASTE"] = st.text_input("Caste", parsed.get("CASTE", ""))
            parsed["FATHER_NAME"] = st.text_input("Father's Name", parsed.get("FATHER_NAME", ""))

        with col2:
            parsed["AGE"] = st.text_input("Age", parsed.get("AGE", ""))
            parsed["ZILLAH"] = st.text_input("Zillah", parsed.get("ZILLAH", ""))
            parsed["PERGUNNAH"] = st.text_input("Pergunnah", parsed.get("PERGUNNAH", ""))
            parsed["VILLAGE"] = st.text_input("Village", parsed.get("VILLAGE", ""))
            parsed["OCCUPATION"] = st.text_input("Occupation", parsed.get("OCCUPATION", ""))
            parsed["NEXT_OF_KIN"] = st.text_input("Next of Kin", parsed.get("NEXT_OF_KIN", ""))
            parsed["KIN_VILLAGE"] = st.text_input("Kin's Village", parsed.get("KIN_VILLAGE", ""))
            parsed["MARKS"] = st.text_input("Marks", parsed.get("MARKS", ""))

        save = st.form_submit_button("💾 Save to MySQL")
        if save:
            try:
                if "image_bytes" not in st.session_state:
                    st.error("⚠️ Image not found in memory. Please re-upload.")
                else:
                    insert_to_db(parsed, st.session_state["image_bytes"])
                    st.success("✅ Record successfully saved to MySQL.")
                    del st.session_state["parsed_data"]
                    del st.session_state["image_bytes"]
            except Exception as e:
                st.error(f"❌ DB Error: {e}")
