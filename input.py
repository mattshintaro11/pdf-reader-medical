import pdfplumber
import json
import re
from typing import Dict, List, Any, Optional
import logging

class GenericPDFFormExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
    def detect_checkbox_groups(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect groups of checkboxes in text.
        """
        checkbox_fields = []
        # Look for checkbox-style inputs (□, [ ], etc.)
        checkbox_pattern = r'(?:□|\[ \]|\(\s*\))\s*([^\n□\[\]\(\)]+)'
        matches = re.finditer(checkbox_pattern, text)
        
        for match in matches:
            label = match.group(1).strip()
            if label:
                checkbox_fields.append({
                    "label": self.clean_field_name(label),
                    "type": "checkbox",
                    "value": False
                })
        
        return checkbox_fields

    def detect_text_fields(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect text input fields in the form.
        """
        text_fields = []
        
        # Patterns for text fields
        patterns = [
            # Label followed by colon and space
            r'([^:\n]+):\s*([^\n]*)',
            # Label with underscores
            r'([^_\n]+)_{3,}',
            # Label in parentheses
            r'\(([^)]+)\)',
            # Label followed by empty brackets
            r'([^[\n]+)\[\s*\]',
            # Specific field indicators
            r'(?:Nombre|Apellido|Dirección|Teléfono|Email|Correo)(?:\s*:)?\s*([^\n]*)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                label = match.group(1).strip()
                if label and not any(c in label for c in '□[]()'):
                    field_type = self.determine_field_type(label)
                    value = match.group(2).strip() if len(match.groups()) > 1 else ""
                    
                    text_fields.append({
                        "label": self.clean_field_name(label),
                        "type": field_type,
                        "value": value if field_type == "text" else None
                    })
        
        return text_fields

    def determine_field_type(self, label: str) -> str:
        """
        Determine the type of form field based on its label.
        """
        label_lower = label.lower()
        
        # Date patterns
        if any(word in label_lower for word in ['fecha', 'date', 'día', 'mes', 'año', 'nacimiento']):
            return "date"
            
        # Number patterns
        if any(word in label_lower for word in [
            'cantidad', 'número', 'monto', 'total', 'edad', 'peso', 'talla',
            'teléfono', 'telefono', 'móvil', 'movil', 'fuma', 'consume'
        ]):
            return "number"
            
        # Checkbox patterns
        if any(word in label_lower for word in ['sí/no', 'si/no', 'yes/no', 'acepta']):
            return "checkbox"
            
        return "text"

    def clean_field_name(self, text: str) -> str:
        """
        Clean and normalize field names.
        """
        # Remove special characters but keep Spanish characters
        text = re.sub(r'[^\w\s\u00C0-\u00FF]', ' ', text)
        # Convert to lowercase and replace spaces with underscores
        text = text.lower().strip()
        # Replace multiple spaces with single underscore
        text = re.sub(r'\s+', '_', text)
        # Remove leading/trailing underscores
        text = text.strip('_')
        return text

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
                current_section = None
                
                for page_num, page in enumerate(pdf.pages, 1):
                    self.logger.info(f"Processing page {page_num}")
                    
                    # Extract text and tables
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    
                    # Detect form name from first page
                    if page_num == 1:
                        first_lines = text.split('\n')[:3]
                        for line in first_lines:
                            if re.search(r'(?:form|formato|formulario)', line.lower()):
                                form_structure["metadata"]["form_name"] = line.strip()
                                break
                    
                    # Process section headers
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Check if this is a section header
                        if line.isupper() or (len(line) > 3 and line.endswith(':')):
                            current_section = self.clean_field_name(line)
                            form_structure["fields"].append({
                                "label": current_section,
                                "type": "section",
                                "value": ""
                            })
                            continue
                        
                        # Add checkbox fields
                        checkbox_fields = self.detect_checkbox_groups(line)
                        for field in checkbox_fields:
                            if current_section:
                                field["section"] = current_section
                            form_structure["fields"].append(field)
                        
                        # Add text fields
                        text_fields = self.detect_text_fields(line)
                        for field in text_fields:
                            if current_section:
                                field["section"] = current_section
                            form_structure["fields"].append(field)
                    
                    # Process tables
                    for table in tables:
                        if not table:
                            continue
                            
                        for row in table:
                            if not row or not any(row):
                                continue
                                
                            row_text = ' '.join(str(cell) for cell in row if cell)
                            # Process checkbox fields in table
                            checkbox_fields = self.detect_checkbox_groups(row_text)
                            for field in checkbox_fields:
                                if current_section:
                                    field["section"] = current_section
                                form_structure["fields"].append(field)
                            
                            # Process text fields in table
                            text_fields = self.detect_text_fields(row_text)
                            for field in text_fields:
                                if current_section:
                                    field["section"] = current_section
                                form_structure["fields"].append(field)
            
            # Clean up and deduplicate fields
            form_structure["fields"] = self.deduplicate_fields(form_structure["fields"])
            
            return form_structure
            
        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}")
            raise

    def deduplicate_fields(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate fields while preserving order.
        """
        seen = set()
        unique_fields = []
        
        for field in fields:
            # Create a unique key for each field
            field_key = f"{field['label']}_{field['type']}"
            if "section" in field:
                field_key += f"_{field['section']}"
                
            if field_key not in seen:
                seen.add(field_key)
                unique_fields.append(field)
        
        return unique_fields

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