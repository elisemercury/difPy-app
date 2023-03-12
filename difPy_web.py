import streamlit as st
from PIL import Image
import shutil
import time
import os
import difPy
from difPy import dif
import io
from contextlib import redirect_stdout
from __version__ import __version__

st.set_page_config(
    page_title="difPy - Duplicate Image Finder",
    page_icon="📷",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def clean_directory(dir):
    shutil.rmtree(dir)
    os.makedirs(dir)

customized_button = st.markdown("""
    <style >
    div.stButton > button:first-child.css-firdtp {
        background-color: #cdcaff87;
        border: 1px solid rgb(190, 190, 190);
        font-weight: 550;
        color: #2d004a;
        }

    div.stButton > button:hover.css-firdtp {
        background-color: #cdcaffe6;
        border: 1px solid rgba(49, 51, 63, 0.2);
        }

    .css-184tjsw p {
        font-size: 16px;
        }

    .css-swapoz a {
        color: #a3a8b8;
        text-decoration: none!important;
        }

    .css-rvekum a {
        color: #31333f99;
        text-decoration: none!important;    
    }

    </style>""", unsafe_allow_html=True)

hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)
st.write('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

folder_upload_path = "uploads"
duplicate_path = "duplicates"
timestamp = None

if not os.path.isdir(folder_upload_path):
    os.makedirs(folder_upload_path)
if not os.path.isdir(duplicate_path):
    os.makedirs(duplicate_path)

if "difPy" not in st.session_state:
    st.session_state["difPy"] = False

if "difPy_info" not in st.session_state:
    st.session_state["difPy_info"] = ""

if "view_samples" not in st.session_state:
    st.session_state["view_samples"] = False

if "show_result" not in st.session_state:
    st.session_state["show_result"] = False

if isinstance(st.session_state["difPy"], bool):
    clean_directory(folder_upload_path)
    clean_directory(duplicate_path)

## App Functions ##

def display_result_metrics(search):
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    with metrics_col1:
        st.metric("Files searched", search.stats["files_searched"])
    if st.session_state["similarity"] == "duplicates":
        with metrics_col2:
            st.metric("Duplicate(s) found", search.stats["matches_found"]["duplicates"])
        with metrics_col3:
            st.metric("Invalid file(s)", search.stats["invalid_files"]["count"])
    else:
        with metrics_col2:
            st.metric("Duplicate(s) found", search.stats["matches_found"]["duplicates"])
        with metrics_col3:
            st.metric("Similar found", search.stats["matches_found"]["similar"])
        with metrics_col4:
            st.metric("Invalid file(s)", search.stats["invalid_files"]["count"])
    return search.stats["matches_found"]["duplicates"] + search.stats["matches_found"]["similar"]

def display_result_imgs(search):
    showing = len(search.result) if len(search.result) < 5 else "5"
    st.write(f"Showing {showing}/{len(search.result)} matches:")
    display_count = 0
    for image in search.result:
        if display_count < 5:
            with st.container():
                result_img, result_metrics = st.columns(2)
                with result_img:
                    try:                   
                        img_read = Image.open(search.result[image]["location"])
                    except:
                        head, tail = os.path.split(search.result[image]["location"])
                        img_read = Image.open(os.path.join(duplicate_path, tail))
                    finally:
                        st.image(img_read, width=200, use_column_width=False)
                with result_metrics:
                    st.markdown(f"Filename: **{os.path.split(search.result[image]['location'])[1]}**")
                    st.write(f"Number of matches: {len(search.result[image]['matches'])}")
            display_count += 1
        else:
            break
    if int(showing) < len(search.result):
        st.write(f"... and {len(search.result)-int(showing)} more files.")

def determine_error(e):
    if e.__class__.__name__== "FileNotFoundError":
        debug_info = str(e)
    elif e.__class__.__name__== "ValueError":
        error_code = 1001
        debug_info = f"Error code: {error_code}"
    elif e.__class__.__name__== "NameError":
        error_code = 1002
        debug_info = f"Error code: {error_code}"
    elif e.__class__.__name__== "AttributeError":
        error_code = 1003
        debug_info = f"Error code: {error_code}"
    elif e.__class__.__name__== "MemoryError":
        error_code = 1004
        debug_info = f"Error code: {error_code}"
    elif e.__class__.__name__== "RuntimeError":
        error_code = 1005
        debug_info = f"Error code: {error_code}"
    else:
        error_code = 1000
        debug_info = f"Error code: {error_code}"    
    result_placeholder.error(f"""
                            ⚠ Oops, something went wrong! 😯  
                            {debug_info}.  
                            """)    
    return debug_info

def get_info(stdout):
    stdout = stdout.replace("\r", "\n").split("\n")
    for info in stdout:
        if "Found" in info:
            return info

def clear_result():
    if st.session_state["view_samples"]:
        pass
    elif st.session_state["show_result"]:
        st.session_state["show_result"] = not st.session_state["show_result"]
    else:
        pass

max_upload = 50

## App Logic ##

with st.sidebar:
    st.title("difPy Web")
    st.caption(f"Version {difPy.__version__} / {__version__}")
    st.write('[How to use difPy Web?](https://difpy.readthedocs.io/en/latest/app.html)')
    st.write('difPy is an open-source project with the aim of facilitating offline image deduplication - for everyone.')
    #st.write(f'**Need to compare more than {max_upload} images?** [Download the difPy App](https://difpy.readthedocs.io/en/latest/app.html)')
    st.markdown('difPy is free of charge for anyone to use. Like difPy? Consider donating to support the project 🫶')
    st.markdown('[![PayPal Support](https://img.shields.io/badge/Support-difPy-yellow?style=flat&logo=paypal&labelColor=white&logoWidth=20.svg)](https://paypal.me/eliselandman)&nbsp;&nbsp;&nbsp;[![Revolut Support](https://img.shields.io/badge/Support-difPy-blueviolet?style=flat&logo=revolut&logoColor=black&labelColor=white&logoWidth=20.svg/)](https://revolut.me/elisemercury)')
    st.caption("[Open a bug](https://test.com)")

st.title("📷 difPy Duplicate Image Finder")
st.info("✨ Supports all popular image formats - JPG, PNG, BMP, etc.")

st.write(f"difPy automates the search for duplicate images for you. difPy Web lets you compare up to {max_upload} images. Upload images to start.")

uploaded_files = st.file_uploader("Upload Images", 
                                  accept_multiple_files=True, 
                                  label_visibility="collapsed",
                                  key="upload")
if len(uploaded_files) > max_upload:
    st.warning(f"😯 difPy Web does not support upload of more than {max_upload} images!")

# Button: Advanced Options
with st.expander("Advanced options", expanded=False):
    st.markdown('<span style="font-size: 12px">For more information on advanced options, please see the [difPy Usage Documentation](https://difpy.readthedocs.io/en/latest/app.html).</span>', unsafe_allow_html=True)
    adv_col1, adv_col2, adv_col3 = st.columns(3)
    with adv_col1:
        option_fsa = st.checkbox("Fast Search (FSA)", value=True, help="Enable/disable difPy's **Fast Search Algorithm**. [Read more](https://test.com)", key="FSA", on_change=clear_result())
    with adv_col2:
        option_similarity = st.selectbox("Similarity", ("duplicates", "similar"), index=0, help="Set the **similarity level** for the comparison. [Read more](https://test.com)", key="similarity", on_change=clear_result())
    with adv_col3:
        option_pxsize = st.selectbox("Pixel size", (25, 50, 100, 200), index=1, help="**Recommended not to change default value!** Adjust the **pixel size** of the images before being compared. [Read more](https://test.com)", key="px_size", on_change=clear_result())

# Button: Run difPy
submit_btn = st.button("Run difPy!", type="primary", key="run") 

result_placeholder = st.empty()

# Run difPy logic
if submit_btn:
    if not uploaded_files:
        st.error("⚠ Please upload at least two images! 😯")
        st.session_state["show_result"] = False
    elif len(uploaded_files) < 2:
        st.error("⚠ Please upload at least two images! 😯")
        st.session_state["show_result"] = False
    else:
        with st.spinner(f"Working... 💫"):
            for uploaded_file in uploaded_files:
                with open(os.path.join(folder_upload_path,uploaded_file.name),"wb") as f:
                    f.write((uploaded_file).getbuffer())
            try:
                f = io.StringIO()
                with redirect_stdout(f):
                    search = dif(folder_upload_path, fast_search=st.session_state["FSA"], recursive=True, 
                                similarity=st.session_state["similarity"], px_size=st.session_state["px_size"], show_progress=False, show_output=False, 
                                move_to=duplicate_path, delete=False, silent_del=False, logs=False)
                info = get_info(f.getvalue())
                st.session_state["difPy"] = search
                st.session_state["difPy_info"] = info
                shutil.make_archive(f"difPy", 'zip', 'uploads')
                st.session_state["show_result"] = True
            except Exception as e: 
                debug_info = determine_error(e)
                st.session_state["difPy"] = not st.session_state["difPy"]

if not isinstance(st.session_state["difPy"], bool) and st.session_state["show_result"] == True:
    st.write(st.session_state["difPy_info"])
    match_count = display_result_metrics(st.session_state["difPy"])
    timestamp = str(time.time()).replace('.', '_')
    if match_count > 0:
        st.json(st.session_state["difPy"].result, expanded=False)
        col1, col2 = st.columns([1, 3])
        with col1:
            with open(f"difPy.zip", "rb") as fp:
                btn = st.download_button("⬇️ Download result", data=fp, file_name=f"difPy_{timestamp}.zip", mime="application/zip", disabled=False, 
                                        help="Download a ZIP file of the deduplicated images.")
        with col2:
            st.button("View sample result!", key="view_samples")

if st.session_state["view_samples"]:
    display_result_imgs(st.session_state["difPy"])
        
#st.caption("difPy Web Version - for full difPy functionalities, [download the app](https://test.com).")
st.markdown('<br><hr><center>Made with ❤️<br><span style="font-size: 14px">[difPy](https://github.com/elisemercury/Duplicate-Image-Finder) by [Elise Landman](https://github.com/elisemercury)</span></center><hr>', unsafe_allow_html=True)