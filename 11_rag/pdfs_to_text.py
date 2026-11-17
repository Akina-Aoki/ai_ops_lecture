"""
it’s step 1 of the whole pipeline — nothing downstream works until these .txt files exist.
"""

from pypdf import PdfReader
from backend.constants import DATA_PATH


def extract_text_from_pdf(path) -> str:
    """
    Opens a PDF and pulls out all the text it can find, page by page.
    """
    reader = PdfReader(path)       # pypdf's tool for reading a PDF's contents

    all_text = ""

    for page in reader.pages:              # go through every page in the PDF
        text = page.extract_text()          # try to pull text out of that page
        if text:                            # some pages (e.g. a scanned image) might have no extractable text at all
            all_text += text + "\n"         # add this page's text, with a newline to separate pages

    return all_text


def export_text_to_txt(text, export_path):
    """
    Saves a string of text out to a .txt file.
    """
    with open(export_path, "w") as file:   # "w" = write mode; creates the file if missing, overwrites it if it exists
        file.write(text)


# Only runs when this script is executed directly, e.g. "python -m backend.pdfs_to_text"
if __name__ == "__main__":
    for pdf_path in DATA_PATH.glob("*.pdf"):          # find every PDF in the data folder
        pdf_text = extract_text_from_pdf(pdf_path)     # get its text

        filename = f"{pdf_path.stem.casefold()}.txt"   # same name as the PDF, lowercased, with .txt instead of .pdf

        export_text_to_txt(pdf_text, DATA_PATH / filename)   # save it next to the original PDF