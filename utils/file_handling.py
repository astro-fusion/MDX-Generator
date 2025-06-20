from datetime import datetime, timedelta
import os
import csv

WORKSPACE_DIR = os.getcwd()
TEMPLATE_DIR = os.path.join(WORKSPACE_DIR, 'templates')
CONTENT_DIR = os.path.join(WORKSPACE_DIR, 'content')
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, 'generated')

def readTemplate(templateName):

    templatePath = os.path.join(TEMPLATE_DIR, templateName)
    """Read the markdown template file."""
    with open(templatePath, 'r') as file:
        return file.read()

# def saveMarkdown(metaData, content, file_name):
#     """Save generated content to a markdown file."""
#     with open(os.path.join(OUTPUT_DIR, file_name), 'w') as file:
#         file.write(metaData + content)


def saveMarkdown(metaData, content, file_name):
    """Save generated content to a markdown file."""
    # Convert metaData and content to strings if they are generators
    if not isinstance(metaData, str):
        metaData = ''.join(metaData)
    if not isinstance(content, str):
        content = ''.join(content)

    with open(os.path.join(OUTPUT_DIR, file_name), 'w') as file:
        file.write(metaData + content)


def readCsv(filePath, fieldnames):
    """Read CSV file and return a list of dictionaries."""
    # this is temporary will be looped in a directory to read all the blog metadata
    with open(filePath, 'r', newline='') as file:
        reader = csv.DictReader(file, fieldnames=fieldnames)
        return list(reader)

def generateMetaData(title, description):
    return f"""---
title: '{title}'
description: '{description}'
pubDate: '{datetime.today().strftime('%Y-%m-%d')}'
---

"""


def saveGeneratedFilesCsv(generatedFiles):
    # start one hour after current time
    startDate = datetime.now() + timedelta(hours=1)
    waitTime = timedelta(hours=6)
    # saving generatedFilesMetaData
    with open(os.path.join(OUTPUT_DIR, "generatedFiles.csv"), 'a', newline='') as file:
        writer = csv.writer(file)
        idx=0
        loopCount = len(generatedFiles)
        while idx < loopCount:
            generatedFile = generatedFiles[idx]
            uploadTime = startDate + waitTime * idx
            writer.writerow([generatedFile.id, generatedFile.outputFileName, uploadTime, 'false', 'false'])
            idx = idx + 1
