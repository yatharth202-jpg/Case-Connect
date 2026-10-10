import pdfplumber
import os

pdf_map = {
    'docs/reference/Case_Connect_AI_Master_Guide (1).pdf': 'docs/reference/Case_Connect_AI_Master_Guide.md',
    'docs/reference/SIH26189_Complete_Project_Architecture.pdf': 'docs/reference/SIH26189_Complete_Project_Architecture.md',
    'docs/reference/SIH26189_Sample_Demo_Data.pdf': 'docs/reference/SIH26189_Sample_Demo_Data.md',
    'docs/reference/SIH26189_Skills_Required.pdf': 'docs/reference/SIH26189_Skills_Required.md',
    'docs/reference/25de1c7e-2a2c-451c-9d37-53109fe57782.pdf': 'docs/reference/25de1c7e_superseded_master_document.md',
}

for pdf_path, md_path in pdf_map.items():
    if not os.path.exists(pdf_path):
        print(f"Missing: {pdf_path}")
        continue
    with pdfplumber.open(pdf_path) as pdf:
        content = []
        content.append(f"# {os.path.basename(pdf_path)}\n\n")
        if "25de1c7e" in pdf_path:
            content.append("> [!WARNING]\n> **SUPERSEDED DOCUMENT**: This document contains deprecated claims (e.g. '100% admissible under Section 65B', 'Mastermind', 'auto-link'). Marked as SUPERSEDED as per docs/RULES.md and docs/reference/INDEX.md.\n\n")
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            content.append(f"<!-- PAGE {i+1} -->\n## Page {i+1}\n\n{text}\n\n")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        print(f"Converted {pdf_path} -> {md_path} ({len(pdf.pages)} pages)")
