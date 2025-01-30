from fillpdf import fillpdfs
import json
import os
from datetime import datetime

class MedicalFormSystem:
    def __init__(self, template_path):
        """Initialize with template PDF path"""
        self.template_path = template_path
        self.fields = self._get_form_fields()
        
    def _get_form_fields(self):
        """Get all fillable fields from the template"""
        return fillpdfs.get_form_fields(self.template_path)
    
    def create_patient_form(self, patient_data, output_dir="filled_forms"):
        """Fill form with patient data and save it"""
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate filename using patient name and date
        filename = f"{patient_data['Apellido Paterno']}_{patient_data['Nombre(s)']}"
        filename = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(output_dir, filename)
        
        # Fill and save the form
        fillpdfs.write_fillable_pdf(self.template_path, output_path, patient_data)
        return output_path

def process_patient(form_system):
    """Interactive function to get patient data and create form"""
    print("\nEnter patient information:")
    patient_data = {
        "Apellido Paterno": input("Apellido Paterno: "),
        "Apellido Materno": input("Apellido Materno: "),
        "Nombre(s)": input("Nombre(s): "),
        "Edad": input("Edad: "),
        "Sexo": input("Sexo (M/H): ").upper()
    }
    
    # Additional medical history
    print("\nHistoria clínica:")
    history_options = [
        "Cardiacos", "Hipertensivos", "Diabetes Mellitus", 
        "VIH/SIDA", "Cáncer", "Hepáticos", "Convulsivos"
    ]
    
    for condition in history_options:
        if input(f"¿{condition}? (s/n): ").lower() == 's':
            patient_data[condition] = "Yes"
    
    # Create the filled form
    output_path = form_system.create_patient_form(patient_data)
    print(f"\nForm created successfully: {output_path}")
    return output_path

def main():
    # Initialize system with template form
    template_path = "medical_form.pdf"  # Change this to your template path
    print("Initializing Medical Form System...")
    
    try:
        form_system = MedicalFormSystem(template_path)
        print("System initialized successfully!")
        
        while True:
            print("\n1. Process new patient")
            print("2. Exit")
            choice = input("\nSelect option (1-2): ")
            
            if choice == "1":
                process_patient(form_system)
            elif choice == "2":
                break
            else:
                print("Invalid option. Please try again.")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()