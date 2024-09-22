import streamlit as st
import openai
import time
import sys
import ast
from openai import OpenAI
import os
import re
#from streamlit_markmap import markmap
import json
from investigations import create_patient_document
from st_audiorec import st_audiorec
import whisper
import time


ASSISTANT_ID = "asst_wTfRitYZNaIGHByiYw2SmQrn"

st.set_page_config(page_title="Investigation Table Maker", layout="wide")

# Add a custom title with styling
st.markdown("""
    <div style="
        background-color: #1c39bb; 
        padding: 10px; 
        border-radius: 10px;
        text-align: center; 
        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
        ">
        <h1 style='color: #FFFFFF; font-family: Arial, sans-serif; font-weight: bold;'>
            Investigation Table Maker
        </h1>
    </div>
    """, unsafe_allow_html=True)

# API Key setup

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

openai.api_key = os.getenv("OPENAI_API_KEY")

#st.write(openai.api_key)

try:
    client = OpenAI(api_key=openai.api_key)
except Exception as e:
    st.error(f"Error initializing OpenAI client: {str(e)}")
    


st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown('<p></p>', unsafe_allow_html=True)

if st.button("Reset App"):
    st.session_state.clear()


# Initialize session state
if 'final_input_data' not in st.session_state:
    st.session_state.final_input_data = None
if 'api_result' not in st.session_state:
    st.session_state.api_result = None
    

if 'text_received' not in st.session_state:
    st.session_state.text_received = []

# Display columns for speech to text


st.title("Input Investigations/Medications/Advises:")


# Audio recording component
wav_audio_data = st_audiorec()

if wav_audio_data:
    file_path = 'save_recorded_audio.wav'
    
    # Save the audio file as .wav
    with open(file_path, "wb") as f:
        f.write(wav_audio_data)
    
    st.success(f"WAV file saved successfully as {file_path}")

    # Load the 'tiny' model to ensure compatibility with Streamlit Cloud
    model = whisper.load_model("tiny")

    # Transcribe the recorded audio
    start = time.time()
    result = model.transcribe(file_path)
    end = time.time()
    
    st.write("Transcription time: ", end - start)

    # Show the transcription result
    transcription_text = result['text']
    st.write("Transcribed Text: ", transcription_text)

    # Text input for additional content
    additional_text = st.text_input("If you have anything else to add, type it here:")
    final_transcription = None
    # Proceed button
    if st.button("Proceed"):
        # Merge transcription with additional text
        final_transcription = transcription_text + " " + additional_text.strip()
        st.session_state.final_input_data=final_transcription
        st.write("Final Input Data: ", final_transcription)
    
# st.session_state.final_input_data = final_transcription


if final_transcription:
    thread = client.beta.threads.create(
    messages=[
        {
          "role": "user",
          "content": final_transcription
          
        }
      ]
    )
    
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    progress = 0
    max_time = 100  # Maximum progress steps, adjust as needed
    timeout = 60  # Timeout set to 90 seconds
    start_time = time.time() 
    
    while run.status != "completed":
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            # Stop the process if it takes more than 90 seconds and show an error
            st.error("Server error occurred. Please retry. Reset The App")
            st.stop()  # This stops the app execution
            break  # Exit the loop
            
        # Increment progress step
        progress += 1
        if progress >= max_time:
            progress = max_time - 1  # Keep progress under 100 until completion
    
        # Update the progress bar and status text
        progress_bar.progress(progress)
        status_text.text(f"Digging in ...")
    
        # Simulate the check by retrieving the run status again
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    
        # Sleep for 1 second between checks
        time.sleep(1)
    
    progress_bar.progress(100)
    
    # Store the API result in session state to avoid reruns
    st.session_state.api_result = client.beta.threads.messages.list(thread_id=thread.id).data[0].content[0].text.value
    st.success("Successfully Retrieved The Table Data!")
    input_string = (st.session_state.api_result)
    #st.write(input_string)
    
    ################################################################################################################
    try:
        start_pos = input_string.find("investigations_example=")
    
        if start_pos == -1:
            st.write("Could not find investigations_example.")
            
    # Find the first '{' after 'investigations_example='
        first_open_brace = input_string.find("{", start_pos)
    
    # Initialize the brace counter and find the matching closing brace '}'
        brace_count = 0
        for i in range(first_open_brace, len(input_string)):
            if input_string[i] == '{':
                brace_count += 1
            elif input_string[i] == '}':
                brace_count -= 1
            if brace_count == 0:
                last_closing_brace = i
                break
    
    # Extract the dictionary-like string between the opening and closing braces
        investigations_str = input_string[first_open_brace:last_closing_brace + 1].strip()
    
    # Debugging print to show the extracted string
        #st.write(f"Extracted investigations_str:\n{investigations_str}\n")

        try:
            # Convert the extracted string to a Python dictionary using ast.literal_eval
            investigations_dict = ast.literal_eval(investigations_str)
            st.session_state.investigations_dict = investigations_dict
            #st.write(investigations_dict)
        
            
        except (SyntaxError, ValueError) as e:
            st.write(f"Error parsing dictionary: {e}")
            
        ######################################################################################################################
        advise_pattern = r"advise_example\s*=\s*\{"
    
        # Find the starting position for advise_example dictionary
        start_match = re.search(advise_pattern, input_string)
        if not start_match:
            st.write("Could not find advise_example.")
    
    
        # Find the starting position and extract from the opening { till the closing }
        start_pos = start_match.end() - 1  # Start from the opening brace `{`
        
        # Find the closing brace for advise_example
        end_pos = input_string.find('}', start_pos) + 1  # The closing } that matches the opening one
    
        # Extract the content between the starting and closing brackets
        advise_str = input_string[start_pos:end_pos].strip()
    
        # Replace single quotes with double quotes for JSON compatibility
        advise_str = advise_str.replace("'", '"')
    
        # Debugging print to show the string before attempting to parse
        #print(f"Extracted advise_str:\n{advise_str}\n")
    
        try:
            # Load the string as a JSON-compatible dictionary
            advise_dict = json.loads(advise_str)
            st.session_state.advise_dict = advise_dict
            #st.write(advise_dict)
            
        except json.JSONDecodeError as e:
            st.write(f"Error parsing dictionary: {e}")

    except Exception as e:
        st.write("Rerun the app") 
    try:
        create_patient_document(st.session_state.investigations_dict,st.session_state.advise_dict)
        file_path = "final_dis_summary.docx"
        with open(file_path, "rb") as file:
            file_data = file.read()
        
        # Create the download button
        st.download_button(
            label="Download DOCX file",   # The label for the download button
            data=file_data,               # Binary content of the file
            file_name="discharge_summary.docx",     # Filename for the downloaded file
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'  # Mime type for .docx
        )
    except Exception as e:
        st.write("Reset and Rerun The app")
