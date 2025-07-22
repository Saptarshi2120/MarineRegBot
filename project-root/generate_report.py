import os
import pdfkit
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

# ⛳️ Updated this line: use the correct function name
from mongo_utils import get_qa_pairs_by_pdf_name  # 🔁 was: get_qa_pairs_by_pdf

def generate_pdf_report(pdf_name: str, output_path: str):
    # Fetch Q&A pairs for the given pdf_name
    qa_pairs = get_qa_pairs_by_pdf_name(pdf_name)

    # Prepare mock metadata (replace with real values if needed)
    context = {
        "submission_id": "SUB12345",
        "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "download_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "file_name": pdf_name,
        "file_size": "456 KB",
        "page_count": "12",
        "word_count": "3456",
        "char_count": "20456",
        "context_similarity": "82%",
        "citation_file": pdf_name,
        "citation_page": 3,
        "citation_paragraph": 2,
        "sentiment": "Positive",
        "tone": "Analytical",
        "entities": [
            {"type": "Person", "value": "John Doe"},
            {"type": "Organization", "value": "OpenAI"},
        ],
        "summary": "This PDF provides a deep insight into modern AI techniques...",
        "qa_pairs": qa_pairs
    }

    # Load the template
    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template("report_template.html")
    html_out = template.render(**context)

    # Generate PDF
    pdfkit.from_string(html_out, output_path)
    print(f"✅ Report generated at: {output_path}")
