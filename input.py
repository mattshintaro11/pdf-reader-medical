from PyPDF2 import PdfReader, PdfWriter
from typing import List, Dict

class PDFFormHandler:
    def __init__(self, pdf_path: str):
        """
        Initialize PDF form handler with a PDF file path
        
        Args:
            pdf_path (str): Path to the PDF form file
        """
        self.pdf_path = pdf_path
        self.reader = PdfReader(pdf_path)
        
    def get_form_fields(self) -> List[str]:
        """
        Get all form field names from the PDF
        
        Returns:
            List[str]: List of form field names/labels
        """
        fields = []
        
        # Get form fields page by page
        for page in self.reader.pages:
            if '/Annots' in page:
                for annotation in page['/Annots']:
                    if annotation.get_object()['/Subtype'] == '/Widget':
                        field_name = annotation.get_object().get('/T')
                        if field_name:
                            # Remove any parentheses and decode if needed
                            if isinstance(field_name, bytes):
                                field_name = field_name.decode('utf-8')
                            fields.append(field_name)
        
        return fields
    
    def fill_form(self, data: Dict[str, str], output_path: str) -> bool:
        """
        Fill the PDF form with provided data and save to a new file
        
        Args:
            data (Dict[str, str]): Dictionary mapping field names to values
            output_path (str): Path where to save the filled PDF
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a PDF writer
            writer = PdfWriter()
            
            # Copy all pages from the template
            for page in self.reader.pages:
                writer.add_page(page)
            
            # Update form fields with the provided data
            writer.update_page_form_field_values(
                writer.pages[0],  # Update first page
                data
            )
            
            # Save the filled form
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True
            
        except Exception as e:
            print(f"Error filling form: {str(e)}")
            return False

def main():
    """Example usage of the PDFFormHandler class"""
    
    # Initialize handler with your PDF
    pdf_handler = PDFFormHandler("sample_form.pdf")
    
    # Get all form fields
    fields = pdf_handler.get_form_fields()
    print("Form fields found:", fields)
    
    # Example data to fill in the form
    sample_data = {
        "Name": "John Doe",
        "Age": "30",
        "Experience": "5 years in software development",
        "Education": "Bachelor's in Computer Science"
    }
    
    # Fill the form and save
    success = pdf_handler.fill_form(sample_data, "filled_form.pdf")
    if success:
        print("Form filled successfully!")
    else:
        print("Error filling form.")

if __name__ == "__main__":
    main()