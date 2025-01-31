import pdfplumber
import json
import re
from typing import Dict, List, Any, Tuple
import logging

class PDFFormExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
    def detect_form_fields(self, text_line: str) -> Tuple[str, str]:
        """
        Detect if a line contains a form field and extract the field name.
        
        Args:
            text_line (str): Line of text from the PDF
            
        Returns:
            Tuple[str, str]: Field name and default value (empty string if not found)
        """
        # Common patterns for form fields
        patterns = [
            # Pattern for fields ending with colon
            r'^([^:]+):(.*)$',
            # Pattern for fields ending with equals
            r'^([^=]+)=(.*)$',
            # Pattern for fields with checkbox or radio indicators
            r'^(?:\[ \]|\( \))\s*(.+?)(?:\s*:)?$',
            # Pattern for numbered fields
            r'^\d+\.\s*([^:]+):?(.*)$',
            # Pattern for fields with underscores or dots indicating fill-in areas
            r'^([^_\.]+)[_\.]+(.*)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text_line.strip())
            if match:
                field_name = match.group(1).strip()
                default_value = match.group(2).strip() if len(match.groups()) > 1 else ""
                # Clean up field name
                field_name = re.sub(r'[\[\]\(\)\{\}]', '', field_name)
                field_name = field_name.strip()
                return field_name, default_value
                
        return None, None

    def clean_field_name(self, field_name: str) -> str:
        """
        Convert field name to a valid JSON key.
        
        Args:
            field_name (str): Original field name
            
        Returns:
            str: Cleaned field name suitable for JSON
        """
        if not field_name:
            return ""
            
        # Replace special characters and spaces with underscores
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_name.lower())
        # Remove multiple consecutive underscores
        clean_name = re.sub(r'_+', '_', clean_name)
        # Remove leading/trailing underscores
        clean_name = clean_name.strip('_')
        return clean_name

    def detect_checkboxes(self, text: str) -> List[str]:
        """
        Detect checkbox options in text.
        
        Args:
            text (str): Text containing checkbox options
            
        Returns:
            List[str]: List of checkbox option labels
        """
        checkbox_patterns = [
            r'(?:\[ \]|\( \))\s*([^\n\[\]\(\)]+)',  # Common checkbox patterns
            r'□\s*([^\n□]+)',                        # Unicode checkbox
            r'○\s*([^\n○]+)',                        # Unicode circle
        ]
        
        checkboxes = []
        for pattern in checkbox_patterns:
            matches = re.finditer(pattern, text)
            checkboxes.extend(match.group(1).strip() for match in matches)
        return checkboxes

    def extract_form_fields(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract form fields from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            Dict[str, Any]: Dictionary containing form fields and their default values
        """
        form_data = {}
        current_section = None
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    self.logger.info(f"Processing page {page_num}")
                    
                    # Extract text and handle potential encoding issues
                    text = page.extract_text() or ""
                    
                    # Process each line
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Check if this is a section header
                        if line.isupper() or (len(line) > 3 and line.endswith(':')):
                            current_section = self.clean_field_name(line)
                            if current_section:
                                form_data[current_section] = {}
                            continue
                            
                        # Detect form fields
                        field_name, default_value = self.detect_form_fields(line)
                        if field_name:
                            clean_name = self.clean_field_name(field_name)
                            if current_section and clean_name:
                                form_data[current_section][clean_name] = default_value
                            elif clean_name:
                                form_data[clean_name] = default_value
                                
                        # Detect checkboxes
                        checkboxes = self.detect_checkboxes(line)
                        if checkboxes:
                            checkbox_group = f"checkbox_group_{len(form_data)}"
                            if current_section:
                                if 'checkboxes' not in form_data[current_section]:
                                    form_data[current_section]['checkboxes'] = {}
                                form_data[current_section]['checkboxes'][checkbox_group] = {
                                    self.clean_field_name(box): False for box in checkboxes
                                }
                            else:
                                form_data[checkbox_group] = {
                                    self.clean_field_name(box): False for box in checkboxes
                                }
                    
                    # Look for tables
                    tables = page.extract_tables()
                    if tables:
                        for table_num, table in enumerate(tables, 1):
                            if table and any(any(cell for cell in row) for row in table):
                                table_data = []
                                for row in table:
                                    if row and any(cell for cell in row):
                                        row_data = [str(cell).strip() if cell else "" for cell in row]
                                        table_data.append(row_data)
                                
                                if current_section:
                                    if 'tables' not in form_data[current_section]:
                                        form_data[current_section]['tables'] = {}
                                    form_data[current_section]['tables'][f'table_{table_num}'] = table_data
                                else:
                                    form_data[f'table_{table_num}'] = table_data
            
            return form_data
            
        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}")
            raise

    def save_json_template(self, form_data: Dict[str, Any], output_path: str) -> None:
        """
        Save the extracted form data as a JSON file.
        
        Args:
            form_data (Dict[str, Any]): The extracted form data
            output_path (str): Path where to save the JSON file
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
    
    parser = argparse.ArgumentParser(description='Extract form fields from a PDF file')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='form_template.json',
                       help='Output JSON file path (default: form_template.json)')
    
    args = parser.parse_args()
    
    extractor = PDFFormExtractor()
    try:
        form_data = extractor.extract_form_fields(args.pdf_path)
        extractor.save_json_template(form_data, args.output)
    except Exception as e:
        logging.error(f"Failed to process PDF: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()