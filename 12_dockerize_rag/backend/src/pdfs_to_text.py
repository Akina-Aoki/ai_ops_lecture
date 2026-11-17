"""
Reads every PDF in your data folder and saves a plain-text copy next to it.
"""

from pypdf import PdfReader
from backend.constants import DATA_PATH


def extract_text_from_pdf(path) -> str:
    """
    Opens one PDF file and pulls out all the readable text from every page,
    joined together into one big string.

    Args:
        path: the location of the PDF file.
    Returns:
        A string containing all the text found in that PDF.
    """
    reader = PdfReader(path)

    all_text = ""
    for page in reader.pages:
        text = page.extract_text()
        # Sometimes a page has no text we can read (e.g. it's a scanned
        # image), so `text` comes back empty or None. We skip those instead
        # of adding "None" as literal text.
        if text:
            all_text += text + "\n"

    return all_text


def export_text_to_txt(text, export_path):
    """Saves a string of text into a .txt file (overwrites if it already exists)."""
    with open(export_path, "w") as file:
        file.write(text)


# This special check means: "only run the code below if someone runs
# `python pdfs_to_text.py` directly." If another file just *imports*
# functions from here, this part is skipped. That's how ingestion.py can
# borrow nothing from here safely without re-running this whole conversion.
if __name__ == "__main__":
    # Go through every PDF file sitting in the data folder, one at a time.
    for pdf_path in DATA_PATH.glob("*.pdf"):
        pdf_text = extract_text_from_pdf(pdf_path)

        # Take the filename without ".pdf" and make it lowercase,
        # then add ".txt" on the end. "casefold" is just a stronger
        # version of lowercase that also handles special characters better.
        filename = f"{pdf_path.stem.casefold()}.txt"

        export_text_to_txt(pdf_text, DATA_PATH / filename)