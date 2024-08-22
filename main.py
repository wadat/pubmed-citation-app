"""
Created on Mon Aug 20 21:16:37 2024

@author: wadat2
"""
import json
import requests
from xml.etree.ElementTree import *
# import sys
# sys.path.append("lib.bs4")
from bs4 import BeautifulSoup
import lxml

import streamlit as st
# import pdf2doi
# pdf2doi.config.set('verbose',False)

# import logging
from os import path, listdir
import io

import finders
# import config

# __init__.py
import logging
import importlib.util

# Setup logging
logger = logging.getLogger("pdf2doi")
logger.setLevel(level=logging.INFO)
if not logger.handlers:
    formatter = logging.Formatter("[pdf2doi]: %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
logger.propagate = False


######## config

import configparser
import os
import logging

# ''' 
# method_dxdoiorg                         It sets which method is used when querying dx.doi.org to retrieve the bibtex info
#                                         Two possible values are 'text/bibliography; style=bibtex' , 'application/x-bibtex' and
#                                         'application/citeproc+json'

#                                         The 'application/x-bibtex' method was the one originally used in the first version of
#                                         pdf2doi. However, since October 2021 this method does not return the 
#                                         Journal info, as a result of a bug in dx.doi.org (Last time checked = 2021 Nov 06)
#                                         I added the method 'text/bibliography; style=bibtex' to overcome this problem
#                                         However, with 'text/bibliography; style=bibtex' the authors string is returned in
#                                         the format "LastName1, FirstName1 SecondName1.. and LastName2, FirstName2 SecondName2.. and etc."
#                                         which is not the format expect by the script pdf-renamer, which uses pdf2doi 
                                               
#                                         pdf2doi automatically parses the string obtained by dx.doi.org differently based on
#                                         the value of method_dxdoiorg
#                                         The method "application/citeproc+json" is the best one, because it returns everythin as 
#                                         a json dictionary, and it requires no parsing
# check_online_to_validate

# websearch

# numb_results_google_search              How many results should it look into when doing a google search

# N_characters_in_pdf

# save_identifier_metadata                Sets the default value of the global setting save_identifier_metadata
#                                         If set True, when a valid identifier is found with any method different than the metadata lookup the identifier
#                                         is also written inside the file metadata with key "/identifier". If set False, this does not happen.
                                 
# 'replace_arxivID_by_DOI_when_available' 

# '''


class config():
    __params={'verbose'   :   True,
            'separator' : os.path.sep,
            'method_dxdoiorg' : 'application/citeproc+json',
            'webvalidation' : True,
            'websearch' : True,
            'numb_results_google_search' : 6,
            'N_characters_in_pdf' : 1000,
            'save_identifier_metadata' : True,
            'replace_arxivID_by_DOI_when_available' : True
            }
    __setters = __params.keys()


    @staticmethod
    def update_params(new_params):
        config.__params.update(new_params)

    @staticmethod
    def get(name):
        return config.__params[name]

    @staticmethod
    def set(name, value):
        if name in config.__setters:
             config.__params[name] = value
        else:
            raise NameError("Name not accepted in set() method")
        #Here we define additional actions to perform when specific parameters are modified
        if name == 'verbose':
            # We change the logger verbosity
            if value: loglevel = logging.INFO
            else: loglevel = logging.CRITICAL
            logger = logging.getLogger("pdf2doi")
            logger.setLevel(level=loglevel)

    @staticmethod
    def ReadParamsINIfile():
        '''
        Reads the parameters stored in the file settings.ini, and stores them in the dict self.params
        If the .ini file does not exist, it creates it with the default values.
        '''
        path_current_directory = os.path.dirname(__file__)
        path_config_file = os.path.join(path_current_directory, 'settings.ini')
        if not(os.path.exists(path_config_file)):
            config.WriteParamsINIfile()
        else:
            config_object = configparser.ConfigParser()
            config_object.optionxform = str
            config_object.read(path_config_file)
            config.__params.update(dict(config_object['DEFAULT']))
            config.ConvertParamsToBool()
            config.ConvertParamsToNumb()

    @staticmethod
    def ConvertParamsToBool():
        for key,val in config.__params.items():
            if isinstance(val, str):
                if val.lower() == 'true':
                    config.__params[key]=True
                if val.lower() == 'false':
                    config.__params[key]=False

    @staticmethod
    def ConvertParamsToNumb():
        for key,val in config.__params.items():
            if isinstance(val, str) and val.isdigit():
                config.__params[key]=int(val)
    @staticmethod
    def print():
        '''
        Prints all settings
        '''
        for key,val in config.__params.items():
            print(key + " : " + str(val) + ' ('+type(val).__name__+')')

    @staticmethod
    def WriteParamsINIfile():
        '''
        Writes the parameters currently stored in in the dict self.params into the file settings.ini
        '''
        path_current_directory = os.path.dirname(__file__)
        path_config_file = os.path.join(path_current_directory, 'settings.ini')
        config_object = configparser.ConfigParser()
        config_object.optionxform = str
        config_object['DEFAULT'] = config.__params
        with open(path_config_file, 'w') as configfile: #Write them on file
            config_object.write(configfile)


###########################################



# from .config import config
# config.ReadParamsINIfile()  # Load all current configuration from the .ini file. If the .ini file is not present, it generates it using default values

# Determine the list of libraries to be used to extract text from pdf files
reader_libraries = ['PyPdf','pdfminer'] 
# Using PyPdf before pdfminer makes sure that, in arxiv pdf files, the DOI which is sometimes written on the left margin of the first page is correctly detected

is_textract_installed = importlib.util.find_spec('textract')
if is_textract_installed:
    reader_libraries.append('textract')
    

config.set('verbose',config.get('verbose')) #This is a quick and dirty way (to improve in the future) to make sure that the verbosity of the pdf2doi logger is properly set according
                                            #to the current value of config.get('verbose') (see config.py file for details)
# from .main import pdf2doi, pdf2doi_singlefile
# from .finders import *
# from .bibtex_makers import *
from utils_registry import install_right_click, uninstall_right_click




def pdf2doi_singlefile(file):
    """
    Try to find an identifier of the file specified by the input argument file.  This function does not check wheter filename is a valid path to a pdf file.

    Parameters
    ----------
    file : ether a string or an object file
                if it's a string, it is the absolute path of a single .pdf file

    Returns
    -------
    result, dictionary
        The output is a single dictionary with the following keys

        result['identifier'] = DOI or other identifier (or None if nothing is found)
        result['identifier_type'] = string specifying the type of identifier (e.g. 'doi' or 'arxiv')
        result['validation_info'] = Additional info on the paper. If config.get('webvalidation') = True, then result['validation_info']
                                    will typically contain raw bibtex data for this paper. Otherwise it will just contain True
        result['path'] = path of the pdf file
        result['method'] = method used to find the identifier

    """

    logger = logging.getLogger("pdf2doi")

    result = {'identifier': None}

    try:
        with open(file, 'rb') as f:
            result = __find_doi(f)
    except TypeError:
        try:
            result = __find_doi(file)
        except Exception:
            logger.exception("File processing error")
    except Exception:
        logger.exception("File(open) processing error")

    return result


def __find_doi(file: io.IOBase) -> dict:
    logger = logging.getLogger("pdf2doi")

    # Several methods are now applied to find a valid identifier in the .pdf file identified by filename

    # First method: we look into the pdf metadata (in the current implementation this is done
    # via the getDocumentInfo() method of the library PyPdf) and see if any of them is a string which containts a
    # valid identifier inside it. We first look for the elements of the dictionary with keys '/doi' or /pdf2doi_identifier'(if the they exist),
    # and then any other field of the dictionary
    logger.info(f"Method #1: Looking for a valid identifier in the document infos...")
    result = finders.find_identifier(file, method="document_infos", keysToCheckFirst=['/doi', '/pdf2doi_identifier'])
    if result['identifier']:
        return result

    # Second method: We look for a DOI or arxiv ID inside the filename
    logger.info(f"Method #2: Looking for a valid identifier in the file name...")
    result = finders.find_identifier(file, method="filename")
    if result['identifier']:
        return result

    # Third method: We look in the plain text of the pdf and try to find something that matches a valid identifier.
    logger.info(f"Method #3: Looking for a valid identifier in the document text...")
    result = finders.find_identifier(file, method="document_text")
    if result['identifier']:
        return result

    # Fourth method: We look for possible titles of the paper, do a google search with them,
    # open the first results and look for identifiers in the plain text of the searcg results.
    logger.info(f"Method #4: Looking for possible publication titles...")
    result = finders.find_identifier(file, method="title_google")
    if result['identifier']:
        return result

    # Fifth method: We extract the first N characters from the file (where N is set by config.get('N_characters_in_pdf')) and we use it as
    # a query for a google seaerch. We open the first results and look for identifiers in the plain text of the searcg results.
    logger.info(
        f"Method #5: Trying to do a google search with the first {config.get('N_characters_in_pdf')} characters of this pdf file...")
    result = finders.find_identifier(file, method="first_N_characters_google")
    if result['identifier']:
        return result

    #If execution arrived to this point, it means that no identifier was found. We still return the dictionary returned by the last attempt, for further processing
    #In this case result['identifier']=None
    return result 



# タイトル
st.title('Pubmed Citation App')
st.caption('文献のPDFファイルからPubmed形式のCitationを生成します')

# UploarderからPDFを取得
uploaded_files = st.file_uploader("Upload PDF files", type=['pdf'], accept_multiple_files=True)

for i, uploaded_file in enumerate(uploaded_files):

    if uploaded_file is not None:
        
        f"""
        ##### {i+1}: {uploaded_file.name}
        """

        result = pdf2doi_singlefile(uploaded_file)
        doi = result['identifier']
        # st.write("DOI extracted: ", doi)

        esearch_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term={doi}'
        res = requests.get(esearch_url)
        jsonData = res.json()
        pmid = jsonData['esearchresult']['idlist'][0]

        pubmed_url = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
        pubmed_res = requests.get(pubmed_url)
        soup = BeautifulSoup(pubmed_res.text, 'html.parser')
        
        title = soup.find("h1", class_="heading-title").text
        title = title.replace('\n', '').strip()
        
        journal = soup.find("button", class_="journal-actions-trigger trigger").text
        journal = journal.replace('\n', '').strip()
        
        pagination = soup.find("span", class_="cit").text
        pagination = pagination.replace('\n', '').strip()
        
        citation = f"{journal}. {pagination}"

        f"""
        ```markdown
        {title}
        {citation}
        {pubmed_url}
        ```
        """
