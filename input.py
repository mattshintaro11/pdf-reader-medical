import pdfrw
from pdfrw import PdfReader, PdfWriter
from pdfrw.buildxobj import pagexobj
from pdfrw.objects.pdfdict import PdfDict

class PDFFormHandler:
    def __init__(self, pdf_path):
        """
        Initialize the PDF form handler with a PDF file path
        
        Args:
            pdf_path (str): Path to the PDF form
        """
        self.pdf_path = pdf_path
        self.template_pdf = PdfReader(pdf_path)
    
    def get_form_fields(self):
        """
        Extract all form field labels from the PDF
        
        Returns:
            list: List of form field names/labels
        """
        fields = []
        
        # Iterate through pages
        for page in self.template_pdf.pages:
            if page['/Annots']:
                for annotation in page['/Annots']:
                    if annotation.get('/Subtype') == '/Widget':
                        if annotation.get('/T'):
                            # Get the field name
                            field_name = annotation['/T'][1:-1]  # Remove parentheses
                            fields.append(field_name)
        
        return fields
    
    def fill_form(self, data_dict, output_path):
        """
        Fill the PDF form with provided data and save to a new file
        
        Args:
            data_dict (dict): Dictionary mapping field names to values
            output_path (str): Path where to save the filled PDF
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a copy of the template
            template = PdfReader(self.pdf_path)
            
            # Fill in the fields
            for page in template.pages:
                if page['/Annots']:
                    for annotation in page['/Annots']:
                        if annotation.get('/Subtype') == '/Widget':
                            if annotation.get('/T'):
                                key = annotation['/T'][1:-1]  # Remove parentheses
                                if key in data_dict:
                                    # Fill in the value
                                    annotation.update(
                                        PdfDict(V='{}'.format(data_dict[key]))
                                    )
                                    # Set the field as read-only
                                    annotation.update(
                                        PdfDict(Ff=1)
                                    )
            
            # Save the filled form
            PdfWriter().write(output_path, template)
            return True
            
        except Exception as e:
            print(f"Error filling form: {str(e)}")
            return False

def main():
    # Example usage
    pdf_handler = PDFFormHandler("sample_form.pdf")
    
    # Get form fields
    fields = pdf_handler.get_form_fields()
    print("Form fields found:", fields)
    
    # Example data to fill in the form
    data = {
        "Name": "John Doe",
        "Age": "30",
        "Experience": "5 years in software development",
        "Education": "Bachelor's in Computer Science"
    }
    
    # Fill the form and save
    success = pdf_handler.fill_form(data, "filled_form.pdf")
    if success:
        print("Form filled successfully!")
    else:
        print("Error filling form.")

if __name__ == "__main__":
    main()