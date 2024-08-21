"""
Created on Mon Aug 20 21:16:37 2024

@author: wadat2
"""
import json
import requests
from xml.etree.ElementTree import *

import streamlit as st
import pdf2doi
pdf2doi.config.set('verbose',False)

# タイトル
st.title('Pubmed Citation App')
st.caption('文献のPDFファイルからPubmedリンクを生成します')

# UploarderからPDFを取得
uploaded_files = st.file_uploader("Choose a PDF file", type=['pdf'], accept_multiple_files=True)

for uploaded_file in uploaded_files:

    if uploaded_file is not None:
        
        result = pdf2doi.pdf2doi_singlefile(uploaded_file)
        doi = result['identifier']
        st.write("DOI extracted: ", doi)

        esearch_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term={doi}'
        res = requests.get(esearch_url)
        jsonData = res.json()
        pmid = jsonData['esearchresult']['idlist'][0]

        efetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id={pmid}"
        res = requests.get(efetch_url)
        element = fromstring(res.text)
        title = element.findtext(".//ArticleTitle")

        iso_abb = element.findtext(".//ISOAbbreviation")
        pub_year = element.findtext(".//PubDate//Year")
        pub_month = element.findtext(".//PubDate//Month")
        pub_day = element.findtext(".//PubDate//Day")
        pub_volume = element.findtext(".//JournalIssue//Volume")
        pub_issue = element.findtext(".//JournalIssue//Issue")
        if pub_issue:
            pub_issue = f'({pub_issue})'
        else:
            pub_issue = ''
        start_page = element.findtext(".//Pagination//StartPage")
        end_page = element.findtext(".//Pagination//EndPage")
        if end_page:
            end_page = f'-{end_page}'
        else:
            end_page = ''        
        citation = f"{iso_abb}. {pub_year} {pub_month};{pub_volume}{pub_issue}:{start_page}{end_page}." # {pub_year} {pub_month} {pub_day}; 

        pubmed_url = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'

        f"""
        ```markdown
        {title}
        {citation}
        {pubmed_url}
        ```
        """
