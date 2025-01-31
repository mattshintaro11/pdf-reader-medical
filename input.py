import pdfplumber
import json
import re
from typing import Dict, List, Any, Optional
import logging

class GenericPDFFormExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def detect_form_field(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Detect form fields in text using various patterns.
        Returns field info if found, None otherwise.
        """
        patterns = [
            # Field with colon (Label: _______)
            r'^([^:]+):\s*(?:_{3,}|\[_{3,}\]|\(\s*\)|□)?(.*)$',
            # Field with equals (Label = ______)
            r'^([^=]+)=\s*(?:_{3,}|\[_{3,}\]|\(\s*\)|□)?(.*)$',
            # Checkbox or radio style ([ ] Label or □ Label)
            r'^(?:\[ \]|□)\s*([^:]+)(?:\s*:\s*(.*))?$',
            # Underlined field (Label _____)
            r'^([^_]+)_{3,}(.*)$',
            # Numbered field (1. Label: _____)
            r'^\d+\.\s*([^:]+):\s*(.*)$',
            # Field with parentheses (Label (____))
            r'^([^(]+)\s*\([^)]*\)\s*:?(.*)$'
        ]

        for pattern in patterns:
            match = re.match(pattern, text.strip())
            if match:
                label = match.group(1).strip()
                value = match.group(2).strip() if len(match.groups()) > 1 else ""
                
                # Clean up the label
                label = re.sub(r'[\[\]\(\)□]', '', label)
                label = re.sub(r'\s+', '_', label.strip().lower())
                
                # Determine field type
                field_type = self.determine_field_type(text, value)
                
                return {
                    "label": label,
                    "type": field_type,
                    "value": value if field_type == "text" else False if field_type == "checkbox" else None
                }
        return None

    def determine_field_type(self, text: str, value: str) -> str:
        """
        Determine the type of form field based on its appearance.
        """
        # Check for checkbox/radio patterns
        if re.search(r'(?:\[ \]|□|\(\s*\))', text):
            return "checkbox"
        # Check for date field patterns
        elif re.search(r'(?:fecha|date|día|mes|año|/|-)', text.lower()):
            return "date"
        # Check for numeric field patterns
        elif re.search(r'(?:cantidad|número|monto|total|\d+)', text.lower()):
            return "number"
        # Default to text
        return "text"

    def process_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Process a table and extract form fields from it.
        """
        fields = []
        headers = []
        
        for row in table:
            if not row or not any(cell for cell in row):
                continue
                
            # Try to detect if this is a header row
            if all(cell and isinstance(cell, str) and cell.strip() for cell in row):
                headers = [self.clean_header(cell) for cell in row]
                continue
                
            # Process regular rows
            for i, cell in enumerate(row):
                if not cell:
                    continue
                    
                field = self.detect_form_field(str(cell))
                if field:
                    # Add header context if available
                    if headers and i < len(headers):
                        field["section"] = headers[i]
                    fields.append(field)
                
        return fields

    def clean_header(self, header: str) -> str:
        """
        Clean and normalize header text.
        """
        header = re.sub(r'[^\w\s]', '', header.lower())
        return re.sub(r'\s+', '_', header.strip())

    def extract_form_fields(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract form fields from a PDF file.
        """
        form_structure = {
            "fields": [],
            "metadata": {
                "total_pages": 0,
                "form_name": ""
            }
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                form_structure["metadata"]["total_pages"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    self.logger.info(f"Processing page {page_num}")
                    
                    # Extract text
                    text = page.extract_text() or ""
                    
                    # Try to detect form name from first page
                    if page_num == 1:
                        first_lines = text.split('\n')[:3]  # Check first 3 lines
                        for line in first_lines:
                            if re.search(r'(?:form|formato|formulario)', line.lower()):
                                form_structure["metadata"]["form_name"] = line.strip()
                                break
                    
                    # Process tables
                    tables = page.extract_tables()
                    for table in tables:
                        fields = self.process_table(table)
                        form_structure["fields"].extend(fields)
                    
                    # Process text lines
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                            
                        field = self.detect_form_field(line)
                        if field:
                            form_structure["fields"].append(field)
            
            # Clean up and organize fields
            form_structure["fields"] = self.organize_fields(form_structure["fields"])
            
            return form_structure
            
        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}")
            raise

    def organize_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Organize and deduplicate fields.
        """
        # Remove duplicates while preserving order
        seen = set()
        unique_fields = []
        
        for field in fields:
            field_key = f"{field['label']}_{field['type']}"
            if field_key not in seen:
                seen.add(field_key)
                unique_fields.append(field)
        
        # Sort fields by label for consistency
        return sorted(unique_fields, key=lambda x: x['label'])

    def save_json_template(self, form_data: Dict[str, Any], output_path: str) -> None:
        """
        Save the form data as a JSON file.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(form_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"JSON template saved successfully to {output_path}")
        except Exception as e:
            self.logger.error(f"Error saving JSON: {str(e)}")
            raise

def main():
    """
    Main function to run the PDF form field extractor.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract form fields from any PDF file')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='form_template.json',
                       help='Output JSON file path (default: form_template.json)')
    
    args = parser.parse_args()
    
    extractor = GenericPDFFormExtractor()
    try:
        form_data = extractor.extract_form_fields(args.pdf_path)
        extractor.save_json_template(form_data, args.output)
    except Exception as e:
        logging.error(f"Failed to process PDF: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()